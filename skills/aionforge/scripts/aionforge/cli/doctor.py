"""doctor 自检：图片供应商、Key、连通性、数据目录。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from aionforge.core.config import Settings, key_env_hint

_ALL_KEY_VARS = (
    "XAI_API_KEY / OPENAI_API_KEY / DASHSCOPE_API_KEY / ARK_API_KEY，"
    "或 custom 网关的 AIONFORGE_API_BASE + AIONFORGE_API_KEY"
)


def collect_checks(settings: Settings) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str = "", suggestion: str = "") -> None:
        checks.append(
            {"name": name, "pass": passed, "detail": detail, "suggestion": suggestion}
        )

    image = settings.image
    check("image.provider", True, f"{image.provider}/{image.model}")
    check("image.api", True, f"{image.api} @ {image.api_base}")
    check(
        "image.api_key",
        bool(image.api_key),
        image.provider,
        f"设置 {key_env_hint(image.provider)}（{_ALL_KEY_VARS}）",
    )
    if image.api_key:
        try:
            resp = httpx.get(
                f"{image.api_base.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {image.api_key}"},
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
