from __future__ import annotations

from typing import Any

import pytest

from aionforge.adapters.factory import build_image_adapter
from aionforge.adapters.image import (
    DashScopeImageAdapter,
    GeminiImageAdapter,
    JsonEditsImageAdapter,
    MultipartEditsImageAdapter,
)
from aionforge.adapters.retry import RetryingImageAdapter
from aionforge.core.config import ImageConfig


def _image(**over: Any) -> ImageConfig:
    base: dict[str, Any] = {
        "provider": "grok",
        "model": "grok-imagine-image-2.0",
        "api_base": "https://api.x.ai/v1",
        "api_key": "x-key",
        "api": "edits_json",
    }
    base.update(over)
    return ImageConfig(**base)


def _inner(adapter: object) -> object:
    assert isinstance(adapter, RetryingImageAdapter)
    return adapter.inner


def test_image_api_selects_adapter_by_shape() -> None:
    assert isinstance(
        _inner(build_image_adapter(_image(api="edits_json"))), JsonEditsImageAdapter
    )
    assert isinstance(
        _inner(build_image_adapter(_image(api="edits_multipart"))),
        MultipartEditsImageAdapter,
    )
    assert isinstance(
        _inner(
            build_image_adapter(_image(provider="dashscope", api="dashscope_async"))
        ),
        DashScopeImageAdapter,
    )
    assert isinstance(
        _inner(
            build_image_adapter(
                _image(
                    provider="gemini",
                    model="gemini-3-pro-image",
                    api_base="https://generativelanguage.googleapis.com/v1beta",
                    api="gemini_generate_content",
                )
            )
        ),
        GeminiImageAdapter,
    )
    assert isinstance(
        _inner(
            build_image_adapter(
                _image(
                    provider="hunyuan",
                    model="hy-image-v3",
                    api_base="https://api.hunyuan.cloud.tencent.com/v1",
                    api="edits_multipart",
                )
            )
        ),
        MultipartEditsImageAdapter,
    )
    assert isinstance(
        _inner(
            build_image_adapter(
                _image(
                    provider="qianfan",
                    model="ernie-image",
                    api_base="https://qianfan.baidubce.com/v2",
                    api="edits_multipart",
                )
            )
        ),
        MultipartEditsImageAdapter,
    )


def test_missing_key_raises() -> None:
    with pytest.raises(RuntimeError, match="API Key"):
        build_image_adapter(_image(api_key=""))
