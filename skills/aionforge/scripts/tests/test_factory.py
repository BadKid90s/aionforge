from __future__ import annotations

from typing import Any

import pytest

from aionforge.adapters.factory import build_image_adapter
from aionforge.adapters.image import (
    DashScopeImageAdapter,
    JsonEditsImageAdapter,
    MultipartEditsImageAdapter,
)
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


def test_image_api_selects_adapter_by_shape() -> None:
    assert isinstance(build_image_adapter(_image(api="edits_json")), JsonEditsImageAdapter)
    assert isinstance(
        build_image_adapter(_image(api="edits_multipart")), MultipartEditsImageAdapter
    )
    assert isinstance(
        build_image_adapter(_image(provider="dashscope", api="dashscope_async")),
        DashScopeImageAdapter,
    )


def test_missing_key_raises() -> None:
    with pytest.raises(RuntimeError, match="API Key"):
        build_image_adapter(_image(api_key=""))
