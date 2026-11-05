from __future__ import annotations

import httpx

from aionforge.adapters.image import (
    DashScopeImageAdapter,
    JsonEditsImageAdapter,
    MultipartEditsImageAdapter,
)
from aionforge.core.config import ImageConfig, key_env_hint

ImageAdapterLike = (
    JsonEditsImageAdapter | MultipartEditsImageAdapter | DashScopeImageAdapter
)


def _client(api_base: str, api_key: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=api_base.rstrip("/"),
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=120.0,
    )


def build_image_adapter(model: ImageConfig) -> ImageAdapterLike:
    if not model.api_key:
        raise RuntimeError(
            f"未配置 {model.provider} 的 API Key：请设置 {key_env_hint(model.provider)}"
        )
    client = _client(model.api_base, model.api_key)
    if model.api == "edits_json":
        return JsonEditsImageAdapter(client, model=model.model)
    if model.api == "edits_multipart":
        return MultipartEditsImageAdapter(client, model=model.model)
    if model.api == "dashscope_async":
        return DashScopeImageAdapter(client, model=model.model)
    raise RuntimeError(f"未知图片协议：{model.api}")
