"""图片接口的重试与观测包装。

四个 provider adapter 共用这一层：网络断连、读超时、5xx / 429 自动退避重试，
最终失败时把 model、参考图数量与字节数、耗时、尝试次数一并带进错误信息。
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path
from typing import TypeVar

import httpx

from aionforge.core.log import get_logger

_log = get_logger("image.retry")

_T = TypeVar("_T")

_RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 529}
_MAX_WAIT = 30.0


def _retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _RETRY_STATUS
    if isinstance(exc, httpx.TransportError):
        # ConnectError / ReadError / RemoteProtocolError / ReadTimeout 都在这里。
        return True
    return isinstance(exc, (ConnectionError, TimeoutError))


def _retry_after(exc: BaseException) -> float | None:
    if not isinstance(exc, httpx.HTTPStatusError):
        return None
    raw = exc.response.headers.get("Retry-After")
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        return None


class RetryingImageAdapter:
    """给任意 ImageEditor 包一层重试；不改变 provider 适配器的协议细节。"""

    def __init__(
        self,
        inner: object,
        *,
        label: str,
        retries: int = 2,
        backoff: float = 2.0,
    ) -> None:
        self._inner = inner
        self._label = label
        self._retries = max(0, int(retries))
        self._backoff = max(0.0, float(backoff))

    @property
    def inner(self) -> object:
        return self._inner

    async def edit(
        self, prompt: str, images: Sequence[Path], output: Path
    ) -> Path:
        return await self._run(
            "edit",
            lambda: self._inner.edit(prompt, images, output),  # type: ignore[attr-defined]
            images=images,
        )

    async def generate(self, prompt: str, output: Path) -> Path:
        return await self._run(
            "generate",
            lambda: self._inner.generate(prompt, output),  # type: ignore[attr-defined]
        )

    async def aclose(self) -> None:
        await self._inner.aclose()  # type: ignore[attr-defined]

    async def _run(
        self,
        operation: str,
        call: Callable[[], Awaitable[_T]],
        *,
        images: Sequence[Path] = (),
    ) -> _T:
        refs = tuple(images)
        total_bytes = sum(path.stat().st_size for path in refs if path.is_file())
        attempts = self._retries + 1
        _log.info(
            "%s start model=%s refs=%s bytes=%d attempts=%d",
            operation,
            self._label,
            [path.name for path in refs],
            total_bytes,
            attempts,
        )
        last_error: BaseException | None = None
        for attempt in range(1, attempts + 1):
            started = time.monotonic()
            try:
                result = await call()
            except Exception as exc:  # noqa: BLE001
                elapsed = time.monotonic() - started
                last_error = exc
                retryable = _retryable(exc)
                if not retryable or attempt >= attempts:
                    detail = self._detail(exc)
                    _log.error(
                        "%s failed model=%s attempt=%d/%d elapsed=%.1fs refs=%s "
                        "bytes=%d error=%s",
                        operation,
                        self._label,
                        attempt,
                        attempts,
                        elapsed,
                        [path.name for path in refs],
                        total_bytes,
                        detail,
                    )
                    raise RuntimeError(
                        f"图片接口 {operation} 失败：{self._label}，"
                        f"第 {attempt}/{attempts} 次，耗时 {elapsed:.1f}s，"
                        f"参考图 {len(refs)} 张 / {total_bytes} 字节；{detail}"
                    ) from exc
                wait = self._wait(attempt, exc)
                _log.warning(
                    "%s retry model=%s attempt=%d/%d elapsed=%.1fs error=%s wait=%.1fs",
                    operation,
                    self._label,
                    attempt,
                    attempts,
                    elapsed,
                    self._detail(exc),
                    wait,
                )
                if wait:
                    await asyncio.sleep(wait)
                continue
            elapsed = time.monotonic() - started
            _log.info(
                "%s ok model=%s attempt=%d elapsed=%.1fs output=%s",
                operation,
                self._label,
                attempt,
                elapsed,
                result,
            )
            return result
        raise AssertionError("unreachable") from last_error

    def _wait(self, attempt: int, exc: BaseException) -> float:
        requested = _retry_after(exc)
        if requested is not None:
            return min(requested, _MAX_WAIT)
        return min(self._backoff * (2 ** (attempt - 1)), _MAX_WAIT)

    @staticmethod
    def _detail(exc: BaseException) -> str:
        if isinstance(exc, httpx.HTTPStatusError):
            body = exc.response.text[:300].replace("\n", " ")
            return f"HTTP {exc.response.status_code} {body}".strip()
        return f"{type(exc).__name__}: {exc}"
