"""doctor 自检：图片供应商、Key、连通性、数据目录。"""

from __future__ import annotations

import asyncio
import tempfile
import time
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


def _deep_edit_check(settings: Settings) -> tuple[bool, str]:
    """真实 POST 一次 images/edits；/models 能通不代表出图能通。"""
    from PIL import Image, ImageDraw

    from aionforge.adapters.factory import build_image_adapter

    async def run() -> tuple[bool, str]:
        adapter = build_image_adapter(settings.image)
        try:
            with tempfile.TemporaryDirectory(prefix="forge-doctor-") as tmp:
                probe = Path(tmp) / "probe.png"
                output = Path(tmp) / "out.png"
                image = Image.new("RGB", (512, 512), "white")
                ImageDraw.Draw(image).rectangle((128, 128, 383, 383), fill="red")
                image.save(probe)
                started = time.monotonic()
                await adapter.edit(
                    "保持红色方块的位置和颜色不变，把背景改成纯白 #FFFFFF。",
                    [probe],
                    output,
                )
                elapsed = time.monotonic() - started
                with Image.open(output) as result:
                    result.verify()
                with Image.open(output) as result:
                    size = result.size
                return True, (
                    f"{settings.image.provider}/{settings.image.model} "
                    f"{size[0]}x{size[1]} {elapsed:.1f}s"
                )
        finally:
            await adapter.aclose()

    try:
        return asyncio.run(run())
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)[:240]


def collect_checks(settings: Settings, *, deep: bool = False) -> list[dict[str, Any]]:
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
                f"HTTP {resp.status_code}（浅层 /models）",
                "检查网络、api_base 与 key 是否有效；真实出图请加 --deep",
            )
        except Exception as exc:  # noqa: BLE001
            check(
                "image.reachable",
                False,
                str(exc)[:120],
                "检查网络连通性与 api_base 是否可达",
            )
        if deep:
            passed, detail = _deep_edit_check(settings)
            check(
                "image.deep_edit",
                passed,
                detail,
                ""
                if passed
                else "真实 POST /images/edits 失败；检查模型名、额度、网关是否支持该协议",
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

    log_path = Path(settings.logging.file).expanduser()
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        probe = log_path.parent / ".doctor_log_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        check("logging.file", True, str(log_path))
    except OSError as exc:
        check(
            "logging.file",
            False,
            str(exc)[:120],
            "检查日志目录权限，或改 AIONFORGE_LOG_FILE",
        )

    return checks
