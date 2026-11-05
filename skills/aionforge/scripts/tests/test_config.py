from __future__ import annotations

from pathlib import Path

import pytest

from aionforge.core.config import (
    ConfigError,
    available_providers,
    load_settings,
    read_dotenv,
)

GROK = {"XAI_API_KEY": "x-key"}


def test_single_key_configures_image() -> None:
    settings = load_settings(GROK)
    assert settings.image.provider == "grok"
    assert settings.image.model == "grok-imagine-image-2.0"
    assert settings.image.api == "edits_json"
    assert settings.image.api_key == "x-key"


def test_no_key_falls_back_to_grok_empty() -> None:
    settings = load_settings({})
    assert settings.image.provider == "grok"
    assert settings.image.api_key == ""


def test_available_providers_only_lists_configured_keys() -> None:
    assert available_providers(GROK) == ["grok"]
    assert available_providers({"OPENAI_API_KEY": "o", "ARK_API_KEY": "a"}) == [
        "openai",
        "ark",
    ]
    assert available_providers({}) == []


def test_custom_auto_picked_when_base_and_key_set() -> None:
    settings = load_settings(
        {
            "XAI_API_KEY": "x-key",
            "AIONFORGE_API_BASE": "https://gw.example.com/v1",
            "AIONFORGE_API_KEY": "custom-key",
            "AIONFORGE_IMAGE_MODEL": "image-model",
        }
    )
    assert settings.image.provider == "custom"
    assert settings.image.api == "edits_multipart"
    assert settings.image.model == "image-model"


def test_api_base_overrides_provider_default() -> None:
    settings = load_settings({**GROK, "AIONFORGE_API_BASE": "https://proxy.example/v1"})
    assert settings.image.api_base == "https://proxy.example/v1"


def test_unknown_provider_raises() -> None:
    with pytest.raises(ConfigError, match="不是可用供应商"):
        load_settings({**GROK, "AIONFORGE_PROVIDER": "foo"})


def test_ark_only_does_not_require_text_model() -> None:
    settings = load_settings({"ARK_API_KEY": "ark-key"})
    assert settings.image.provider == "ark"
    assert settings.image.model == "seedream-4.0"


def test_read_dotenv_parses_simple_file(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text("XAI_API_KEY=from-file\n# comment\nEMPTY=\n", encoding="utf-8")
    data = read_dotenv(path)
    assert data["XAI_API_KEY"] == "from-file"
    assert data["EMPTY"] == ""
