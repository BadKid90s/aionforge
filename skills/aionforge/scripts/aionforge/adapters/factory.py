from __future__ import annotations

import httpx

from aionforge.adapters.image import (
    DashScopeImageAdapter,
    GeminiImageAdapter,
    JsonEditsImageAdapter,
    MultipartEditsImageAdapter,
)
from aionforge.adapters.retry import RetryingImageAdapter
from aionforge.core.config import ImageConfig, auth_headers, key_env_hint

ImageAdapterLike = (
    JsonEditsImageAdapter
    | MultipartEditsImageAdapter
    | DashScopeImageAdapter
    | GeminiImageAdapter
    | RetryingImageAdapter
)


def _client(
    api_base: str, api_key: str, provider: str, timeout: float
) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=api_base.rstrip("/"),
        headers=auth_headers(provider, api_key),
        timeout=timeout,
    )


def build_image_adapter(model: ImageConfig) -> ImageAdapterLike:
    if not model.api_key:
        raise RuntimeError(
            f"未配置 {model.provider} 的 API Key：请设置 {key_env_hint(model.provider)}"
        )
    client = _client(model.api_base, model.api_key, model.provider, model.timeout)
    if model.api == "edits_json":
        adapter: ImageAdapterLike = JsonEditsImageAdapter(client, model=model.model)
    elif model.api == "edits_multipart":
        adapter = MultipartEditsImageAdapter(client, model=model.model)
    elif model.api == "dashscope_async":
        adapter = DashScopeImageAdapter(client, model=model.model)
    elif model.api == "gemini_generate_content":
        adapter = GeminiImageAdapter(client, model=model.model)
    else:
        raise RuntimeError(f"未知图片协议：{model.api}")
    return RetryingImageAdapter(
        adapter,
        label=f"{model.provider}/{model.model}",
        retries=model.retries,
        backoff=model.backoff,
    )

