from __future__ import annotations

import asyncio
import base64
import mimetypes
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import httpx

from aionforge.core.log import get_logger

_log = get_logger("image")


def _data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


async def _save_image_data(
    client: httpx.AsyncClient, payload: dict[str, Any], output: Path
) -> Path:
    rows = payload.get("data") or []
    if not rows:
        raise RuntimeError("图片接口没有返回 data")
    item = rows[0]
    output.parent.mkdir(parents=True, exist_ok=True)
    if item.get("b64_json"):
        output.write_bytes(base64.b64decode(item["b64_json"]))
        return output
    url = item.get("url")
    if not url:
        raise RuntimeError("图片接口没有 b64_json 或 url")
    download = await client.get(url)
    download.raise_for_status()
    output.write_bytes(download.content)
    return output


class JsonEditsImageAdapter:
    """JSON POST /images/edits（xAI Imagine，以及用 base64 传参考图的兼容网关）。"""

    def __init__(self, client: httpx.AsyncClient, model: str) -> None:
        self._client = client
        self._model = model

    async def edit(self, prompt: str, images: Sequence[Path], output: Path) -> Path:
        refs = [{"url": _data_url(path), "type": "image_url"} for path in images]
        payload = refs[0] if len(refs) == 1 else refs
        _log.info(
            "JSON edits POST %simages/edits model=%s refs=%s",
            self._client.base_url,
            self._model,
            [path.name for path in images],
        )
        try:
            response = await self._client.post(
                "/images/edits",
                json={"model": self._model, "prompt": prompt, "image": payload},
            )
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise RuntimeError(f"无法连接图片接口 {self._client.base_url}") from exc
        except httpx.HTTPStatusError as exc:
            _log.error("图片接口 HTTP %s %s", exc.response.status_code, exc.response.text[:500])
            raise
        return await _save_image_data(self._client, response.json(), output)

    async def generate(self, prompt: str, output: Path) -> Path:
        _log.info(
            "JSON generations POST %simages/generations model=%s",
            self._client.base_url,
            self._model,
        )
        try:
            response = await self._client.post(
                "/images/generations",
                json={"model": self._model, "prompt": prompt, "n": 1},
            )
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise RuntimeError(f"无法连接图片接口 {self._client.base_url}") from exc
        except httpx.HTTPStatusError as exc:
            _log.error("图片接口 HTTP %s %s", exc.response.status_code, exc.response.text[:500])
            raise
        return await _save_image_data(self._client, response.json(), output)

    async def aclose(self) -> None:
        await self._client.aclose()


class MultipartEditsImageAdapter:
    """multipart POST /images/edits（OpenAI Images API 官方格式）。"""

    def __init__(self, client: httpx.AsyncClient, model: str) -> None:
        self._client = client
        self._model = model

    async def edit(self, prompt: str, images: Sequence[Path], output: Path) -> Path:
        files = []
        for path in images:
            mime = mimetypes.guess_type(path.name)[0] or "image/png"
            files.append(("image", (path.name, path.read_bytes(), mime)))
        _log.info(
            "Multipart edits POST %simages/edits model=%s refs=%s",
            self._client.base_url,
            self._model,
            [path.name for path in images],
        )
        try:
            response = await self._client.post(
                "/images/edits",
                data={"model": self._model, "prompt": prompt},
                files=files,
            )
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise RuntimeError(f"无法连接图片接口 {self._client.base_url}") from exc
        except httpx.HTTPStatusError as exc:
            _log.error("图片接口 HTTP %s %s", exc.response.status_code, exc.response.text[:500])
            raise
        return await _save_image_data(self._client, response.json(), output)

    async def generate(self, prompt: str, output: Path) -> Path:
        _log.info(
            "JSON generations POST %simages/generations model=%s",
            self._client.base_url,
            self._model,
        )
        try:
            response = await self._client.post(
                "/images/generations",
                json={"model": self._model, "prompt": prompt, "n": 1},
            )
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise RuntimeError(f"无法连接图片接口 {self._client.base_url}") from exc
        except httpx.HTTPStatusError as exc:
            _log.error("图片接口 HTTP %s %s", exc.response.status_code, exc.response.text[:500])
            raise
        return await _save_image_data(self._client, response.json(), output)

    async def aclose(self) -> None:
        await self._client.aclose()


class DashScopeImageAdapter:
    """通义万相：提交异步任务后轮询任务状态。无参考图时不可用。"""

    def __init__(self, client: httpx.AsyncClient, model: str) -> None:
        self._client = client
        self._model = model

    async def edit(self, prompt: str, images: Sequence[Path], output: Path) -> Path:
        if not images:
            raise RuntimeError("DashScope 出图需要至少一张参考图")
        _log.info(
            "DashScope POST image2image model=%s refs=%s",
            self._model,
            [path.name for path in images],
        )
        try:
            submit = await self._client.post(
                "/services/aigc/image2image/image-synthesis",
                headers={"X-DashScope-Async": "enable"},
                json={
                    "model": self._model,
                    "input": {"prompt": prompt, "base_image_url": _data_url(images[0])},
                    "parameters": {"n": 1},
                },
            )
            submit.raise_for_status()
        except httpx.ConnectError as exc:
            raise RuntimeError(f"无法连接图片接口 {self._client.base_url}") from exc
        except httpx.HTTPStatusError as exc:
            _log.error("图片接口 HTTP %s %s", exc.response.status_code, exc.response.text[:500])
            raise
        task_id = submit.json()["output"]["task_id"]
        while True:
            poll = await self._client.get(f"/tasks/{task_id}")
            poll.raise_for_status()
            result = poll.json()["output"]
            status = result["task_status"]
            if status == "SUCCEEDED":
                url = result["results"][0]["url"]
                break
            if status not in ("RUNNING", "PENDING"):
                raise RuntimeError(f"DashScope 任务失败: {status}")
            await asyncio.sleep(2)
        download = await self._client.get(url)
        download.raise_for_status()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(download.content)
        return output

    async def generate(self, prompt: str, output: Path) -> Path:
        raise RuntimeError("DashScope 当前只支持带参考图的出图，请传入 --ref")

    async def aclose(self) -> None:
        await self._client.aclose()
