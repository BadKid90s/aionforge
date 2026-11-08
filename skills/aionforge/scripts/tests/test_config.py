from __future__ import annotations

from pathlib import Path

from aionforge.core.config import (
    auth_headers,
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
    assert settings.image.api_base == "https://api.x.ai/v1"


def test_ark_only_does_not_require_text_model() -> None:
    settings = load_settings({"ARK_API_KEY": "ark-key"})
    assert settings.image.provider == "ark"
    assert settings.image.model == "seedream-4.0"


def test_gemini_key_configures_native_image_api() -> None:
    settings = load_settings({"GEMINI_API_KEY": "g-key"})
    assert settings.image.provider == "gemini"
    assert settings.image.model == "gemini-3-pro-image"
    assert settings.image.api == "gemini_generate_content"
    assert settings.image.api_base == "https://generativelanguage.googleapis.com/v1beta"
    assert settings.image.api_key == "g-key"


def test_openai_key_wins_over_gemini_in_auto_pick() -> None:
    settings = load_settings({"OPENAI_API_KEY": "o-key", "GEMINI_API_KEY": "g-key"})
    assert settings.image.provider == "openai"


def test_available_providers_lists_gemini() -> None:
    assert available_providers({"GEMINI_API_KEY": "g-key"}) == ["gemini"]


def test_auth_headers_gemini_uses_goog_api_key() -> None:
    assert auth_headers("gemini", "g-key") == {"x-goog-api-key": "g-key"}
    assert auth_headers("grok", "x-key") == {"Authorization": "Bearer x-key"}


def test_read_dotenv_parses_simple_file(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text("XAI_API_KEY=from-file\n# comment\nEMPTY=\n", encoding="utf-8")
    data = read_dotenv(path)
    assert data["XAI_API_KEY"] == "from-file"
    assert data["EMPTY"] == ""


def test_openai_base_url_overrides_default() -> None:
    settings = load_settings(
        {
            "OPENAI_API_KEY": "o-key",
            "OPENAI_BASE_URL": "https://openai-proxy.example/v1",
        }
    )
    assert settings.image.provider == "openai"
    assert settings.image.api_base == "https://openai-proxy.example/v1"


def test_google_gemini_base_url_overrides_default() -> None:
    settings = load_settings(
        {
            "GEMINI_API_KEY": "g-key",
            "GOOGLE_GEMINI_BASE_URL": "http://gemini-proxy.example/v1beta",
        }
    )
    assert settings.image.provider == "gemini"
    assert settings.image.api_base == "http://gemini-proxy.example/v1beta"


def test_dashscope_base_url_overrides_default() -> None:
    settings = load_settings(
        {
            "DASHSCOPE_API_KEY": "d-key",
            "DASHSCOPE_BASE_URL": "https://dashscope-proxy.example/api/v1",
        }
    )
    assert settings.image.provider == "dashscope"
    assert settings.image.api_base == "https://dashscope-proxy.example/api/v1"


def test_ark_base_url_overrides_default() -> None:
    settings = load_settings(
        {
            "ARK_API_KEY": "a-key",
            "ARK_BASE_URL": "https://ark-proxy.example/api/v3",
        }
    )
    assert settings.image.provider == "ark"
    assert settings.image.api_base == "https://ark-proxy.example/api/v3"


def test_hunyuan_key_configures_multipart() -> None:
    settings = load_settings({"HUNYUAN_API_KEY": "h-key"})
    assert settings.image.provider == "hunyuan"
    assert settings.image.model == "hy-image-v3"
    assert settings.image.api == "edits_multipart"
    assert settings.image.api_base == "https://api.hunyuan.cloud.tencent.com/v1"
    assert settings.image.api_key == "h-key"


def test_qianfan_key_and_base_url() -> None:
    settings = load_settings(
        {
            "QIANFAN_API_KEY": "q-key",
            "QIANFAN_BASE_URL": "https://qianfan-proxy.example/v2",
        }
    )
    assert settings.image.provider == "qianfan"
    assert settings.image.model == "ernie-image"
    assert settings.image.api == "edits_multipart"
    assert settings.image.api_base == "https://qianfan-proxy.example/v2"


def test_first_class_key_wins_over_custom_gateway_vars() -> None:
    settings = load_settings(
        {
            "GEMINI_API_KEY": "g-key",
            "AIONFORGE_API_BASE": "http://should-not-use/v1",
            "AIONFORGE_API_KEY": "custom-key",
        }
    )
    assert settings.image.provider == "gemini"
    assert settings.image.api_base == "https://generativelanguage.googleapis.com/v1beta"


def test_custom_only_when_no_first_class_key() -> None:
    settings = load_settings(
        {
            "AIONFORGE_API_BASE": "https://gw.example.com/v1",
            "AIONFORGE_API_KEY": "custom-key",
            "AIONFORGE_IMAGE_MODEL": "image-model",
        }
    )
    assert settings.image.provider == "custom"
    assert settings.image.model == "image-model"


def test_image_model_overrides_hunyuan_default() -> None:
    settings = load_settings(
        {
            "HUNYUAN_API_KEY": "h-key",
            "AIONFORGE_IMAGE_MODEL": "hy-image-v3.5-preview",
        }
    )
    assert settings.image.provider == "hunyuan"
    assert settings.image.model == "hy-image-v3.5-preview"


def test_dotenv_google_gemini_base_url(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text(
        "GEMINI_API_KEY=g-from-file\n"
        "GOOGLE_GEMINI_BASE_URL=http://from-dotenv/v1beta\n",
        encoding="utf-8",
    )
    settings = load_settings(read_dotenv(path))
    assert settings.image.provider == "gemini"
    assert settings.image.api_key == "g-from-file"
    assert settings.image.api_base == "http://from-dotenv/v1beta"
