from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import httpx
import pytest

from aionforge.adapters.retry import RetryingImageAdapter


class Flaky:
    def __init__(self, failures: int, factory: Callable[[], Exception]) -> None:
        self.failures = failures
        self.factory = factory
        self.attempts = 0
        self.closed = False

    async def edit(self, prompt: str, images: Sequence[Path], output: Path) -> Path:
        return await self._call(output)

    async def generate(self, prompt: str, output: Path) -> Path:
        return await self._call(output)

    async def _call(self, output: Path) -> Path:
        self.attempts += 1
        if self.attempts <= self.failures:
            raise self.factory()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"ok")
        return output

    async def aclose(self) -> None:
        self.closed = True


def _status_error(status: int, text: str = "") -> Exception:
    request = httpx.Request("POST", "https://example.test/images/edits")
    response = httpx.Response(status, text=text, request=request)
    return httpx.HTTPStatusError("bad", request=request, response=response)


async def test_retry_recovers_after_read_errors(tmp_path: Path) -> None:
    inner = Flaky(2, lambda: httpx.ReadError("server disconnected"))
    adapter = RetryingImageAdapter(
        inner, label="custom/gpt-image", retries=2, backoff=0
    )

    saved = await adapter.edit("x", [], tmp_path / "out.png")

    assert saved.is_file()
    assert inner.attempts == 3


async def test_retry_recovers_after_remote_protocol_error(tmp_path: Path) -> None:
    inner = Flaky(1, lambda: httpx.RemoteProtocolError("server disconnected"))
    adapter = RetryingImageAdapter(
        inner, label="custom/gpt-image", retries=2, backoff=0
    )

    saved = await adapter.generate("x", tmp_path / "out.png")

    assert saved.is_file()
    assert inner.attempts == 2


async def test_retry_gives_up_with_model_refs_and_elapsed(tmp_path: Path) -> None:
    inner = Flaky(99, lambda: httpx.RemoteProtocolError("server disconnected"))
    adapter = RetryingImageAdapter(
        inner, label="custom/gpt-image", retries=2, backoff=0
    )
    ref = tmp_path / "ref.png"
    ref.write_bytes(b"12345")

    with pytest.raises(RuntimeError) as info:
        await adapter.edit("x", [ref], tmp_path / "out.png")

    message = str(info.value)
    assert "custom/gpt-image" in message
    assert "第 3/3 次" in message
    assert "参考图 1 张 / 5 字节" in message
    assert "RemoteProtocolError" in message
    assert inner.attempts == 3


async def test_non_retryable_4xx_fails_on_first_attempt(tmp_path: Path) -> None:
    inner = Flaky(99, lambda: _status_error(400, "bad input"))
    adapter = RetryingImageAdapter(
        inner, label="custom/gpt-image", retries=5, backoff=0
    )

    with pytest.raises(RuntimeError, match="HTTP 400 bad input"):
        await adapter.edit("x", [], tmp_path / "out.png")

    assert inner.attempts == 1


async def test_retryable_503_is_retried(tmp_path: Path) -> None:
    inner = Flaky(1, lambda: _status_error(503, "overloaded"))
    adapter = RetryingImageAdapter(
        inner, label="custom/gpt-image", retries=2, backoff=0
    )

    saved = await adapter.edit("x", [], tmp_path / "out.png")

    assert saved.is_file()
    assert inner.attempts == 2
