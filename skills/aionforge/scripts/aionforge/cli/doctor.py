"""doctor 自检：图片供应商、Key、连通性、数据目录。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from aionforge.core.config import (
    CUSTOM,
    Settings,
    auth_headers,
    available_providers,
    key_env_hint,
    merge_env,
)

_ALL_KEY_VARS = (
    "一等：XAI_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY / DASHSCOPE_API_KEY / "
    "ARK_API_KEY / HUNYUAN_API_KEY / QIANFAN_API_KEY；"
    "或兼容网关：AIONFORGE_API_BASE + AIONFORGE_API_KEY + AIONFORGE_IMAGE_MODEL"
)


def collect_checks(settings: Settings) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str = "", suggestion: str = "") -> None:
        checks.append(
            {"name": name, "pass": passed, "detail": detail, "suggestion": suggestion}
        )

    image = settings.image
    has_key = bool(image.api_key)
    key_hint = _ALL_KEY_VARS if not has_key else ""

    check("image.selected", has_key, f"{image.provider}/{image.model}", key_hint)

    if image.provider == CUSTOM:
        has_base = bool(image.api_base)
        check(
            "image.base",
            has_base,
            f"{image.api} @ {image.api_base}",
            "" if has_base else "设置 AIONFORGE_API_BASE",
        )
    else:
        check("image.base", True, f"{image.api} @ {image.api_base}")

    check("image.api_key", has_key, key_env_hint(image.provider), key_hint)

    if has_key:
        try:
            resp = httpx.get(
                f"{image.api_base.rstrip('/')}/models",
                headers=auth_headers(image.provider, image.api_key),
                timeout=10.0,
            )
            check(
                "image.reachable",
                resp.status_code < 500,
                f"HTTP {resp.status_code}",
                "检查网络、api_base 与 key 是否有效",
            )
        except Exception as exc:  # noqa: BLE001
            check(
                "image.reachable",
                False,
                str(exc)[:120],
                "检查网络连通性与 api_base 是否可达",
            )

    others = [p for p in available_providers(merge_env()) if p != image.provider]
    extra_suggestion = ""
    if others:
        extra_names = ", ".join(others)
        extra_suggestion = (
            f"当前用 {image.provider}；若要用 {extra_names} 请去掉 {key_env_hint(image.provider)}"
        )
    check(
        "image.also_configured",
        True,
        ", ".join(others) if others else "none",
        extra_suggestion,
    )

    root = Path(settings.storage.root).expanduser()
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".doctor_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        check("storage.writable", True, str(root))
    except OSError as exc:
        check(
            "storage.writable",
            False,
            str(exc)[:120],
            "检查权限或改 AIONFORGE_STORAGE_ROOT",
        )

    return checks
