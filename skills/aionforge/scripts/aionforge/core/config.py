"""配置只来自环境变量：配了 Key 的图片供应商才可用。

分析、写计划、质检由宿主 Agent 完成，本应用只调图片模型。
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

# scripts/aionforge/core/config.py → Skill 根目录
SKILL_DIR = Path(__file__).resolve().parents[3]

CUSTOM = "custom"
BUILTIN_PROVIDERS = (
    "grok",
    "openai",
    "gemini",
    "dashscope",
    "ark",
    "hunyuan",
    "qianfan",
)
PROVIDERS = (*BUILTIN_PROVIDERS, CUSTOM)

_PROVIDER_API_BASE = {
    "grok": "https://api.x.ai/v1",
    "openai": "https://api.openai.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
    "dashscope": "https://dashscope.aliyuncs.com/api/v1",
    "ark": "https://ark.cn-beijing.volces.com/api/v3",
    "hunyuan": "https://api.hunyuan.cloud.tencent.com/v1",
    "qianfan": "https://qianfan.baidubce.com/v2",
}
PROVIDER_KEY_ENV = {
    "grok": "XAI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "dashscope": "DASHSCOPE_API_KEY",
    "ark": "ARK_API_KEY",
    "hunyuan": "HUNYUAN_API_KEY",
    "qianfan": "QIANFAN_API_KEY",
    CUSTOM: "AIONFORGE_API_KEY",
}
_DEFAULT_MODEL = {
    "grok": "grok-imagine-image-2.0",
    "openai": "gpt-image-2.5-sunburst",
    "gemini": "gemini-3-pro-image",
    "dashscope": "wanx2.1-imageedit",
    "ark": "seedream-4.0",
    "hunyuan": "hy-image-v3",
    "qianfan": "ernie-image",
}
_DEFAULT_API = {
    "grok": "edits_json",
    "openai": "edits_multipart",
    "gemini": "gemini_generate_content",
    "dashscope": "dashscope_async",
    "ark": "edits_multipart",
    "hunyuan": "edits_multipart",
    "qianfan": "edits_multipart",
    CUSTOM: "edits_multipart",
}
PROVIDER_BASE_ENV = {
    "grok": "XAI_BASE_URL",
    "openai": "OPENAI_BASE_URL",
    "gemini": "GOOGLE_GEMINI_BASE_URL",
    "dashscope": "DASHSCOPE_BASE_URL",
    "ark": "ARK_BASE_URL",
    "hunyuan": "HUNYUAN_BASE_URL",
    "qianfan": "QIANFAN_BASE_URL",
}

_TRUE = ("1", "true", "yes", "on")
_FALSE = ("0", "false", "no", "off")


class ConfigError(RuntimeError):
    """环境变量配置不完整或不合法，消息里点名要设哪个变量。"""


@dataclass(frozen=True)
class ImageConfig:
    provider: str
    model: str
    api_base: str
    api_key: str
    api: str = "edits_multipart"


@dataclass(frozen=True)
class StorageSettings:
    root: str = "~/.aionforge"


@dataclass(frozen=True)
class LoggingSettings:
    level: str = "INFO"
    console: bool = False
    file: str = "logs/forge.log"


@dataclass(frozen=True)
class Settings:
    image: ImageConfig
    storage: StorageSettings = field(default_factory=StorageSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)


def _get(env: Mapping[str, str], name: str) -> str:
    return (env.get(name) or "").strip()


def _bool(env: Mapping[str, str], name: str, default: bool) -> bool:
    value = _get(env, name).lower()
    if not value:
        return default
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise ConfigError(f"{name}={value} 不是布尔值；可用 {', '.join((*_TRUE, *_FALSE))}")


def _available_key(env: Mapping[str, str], provider: str) -> str:
    if provider == CUSTOM:
        return _get(env, PROVIDER_KEY_ENV[CUSTOM])
    return _get(env, PROVIDER_KEY_ENV[provider])


def key_env_hint(provider: str) -> str:
    return PROVIDER_KEY_ENV[provider]


def auth_headers(provider: str, api_key: str) -> dict[str, str]:
    if provider == "gemini":
        return {"x-goog-api-key": api_key}
    return {"Authorization": f"Bearer {api_key}"}


def available_providers(env: Mapping[str, str] | None = None) -> list[str]:
    environ = os.environ if env is None else env
    found = [p for p in BUILTIN_PROVIDERS if _available_key(environ, p)]
    if _available_key(environ, CUSTOM) and _get(environ, "AIONFORGE_API_BASE"):
        found.append(CUSTOM)
    return found


def read_dotenv(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            result[key] = value
    return result


def merge_env(
    environ: Mapping[str, str] | None = None, dotenv_path: Path | None = None
) -> dict[str, str]:
    merged = dict(os.environ if environ is None else environ)
    # 当前目录 .env 优先，其次 Skill 根目录 .env（Skill 单独分发时把 Key 放这里）
    paths = [dotenv_path] if dotenv_path else [Path.cwd() / ".env", SKILL_DIR / ".env"]
    for path in paths:
        for key, value in read_dotenv(path).items():
            merged.setdefault(key, value)
    return merged


def _pick_provider(env: Mapping[str, str]) -> str:
    for provider in BUILTIN_PROVIDERS:
        if _available_key(env, provider):
            return provider
    if _available_key(env, CUSTOM) and _get(env, "AIONFORGE_API_BASE"):
        return CUSTOM
    return BUILTIN_PROVIDERS[0]


def _api_base(env: Mapping[str, str], provider: str) -> str:
    if provider == CUSTOM:
        override = _get(env, "AIONFORGE_API_BASE")
        if not override:
            raise ConfigError("custom 供应商需要 AIONFORGE_API_BASE")
        return override
    specific_name = PROVIDER_BASE_ENV.get(provider, "")
    if specific_name:
        specific = _get(env, specific_name)
        if specific:
            return specific
    return _PROVIDER_API_BASE[provider]


def _model(env: Mapping[str, str], provider: str) -> str:
    explicit = _get(env, "AIONFORGE_IMAGE_MODEL")
    if explicit:
        return explicit
    known = _DEFAULT_MODEL.get(provider, "")
    if known:
        return known
    raise ConfigError(f"供应商 {provider} 没有内置默认模型，请设置 AIONFORGE_IMAGE_MODEL")


def _resolve_image(env: Mapping[str, str]) -> ImageConfig:
    provider = _pick_provider(env)
    return ImageConfig(
        provider=provider,
        model=_model(env, provider),
        api_base=_api_base(env, provider),
        api_key=_available_key(env, provider),
        api=_DEFAULT_API[provider],
    )


def load_settings(
    env: Mapping[str, str] | None = None, dotenv_path: Path | None = None
) -> Settings:
    environ = merge_env(None, dotenv_path) if env is None else dict(env)
    return Settings(
        image=_resolve_image(environ),
        storage=StorageSettings(root=_get(environ, "AIONFORGE_STORAGE_ROOT") or "~/.aionforge"),
        logging=LoggingSettings(
            level=_get(environ, "AIONFORGE_LOG_LEVEL") or "INFO",
            console=_bool(environ, "AIONFORGE_LOG_CONSOLE", False),
            file=_get(environ, "AIONFORGE_LOG_FILE") or "logs/forge.log",
        ),
    )
