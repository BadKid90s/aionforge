"""定义目录：女装展示套餐 / 字体美学。数据在 references/catalog/，增删只改 JSON。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

CATALOG_DIR = Path(__file__).resolve().parents[2] / "references" / "catalog"
_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
_LOOK_SECTIONS = ("【场景】", "【风格】", "【镜头语言】", "【主体动作】")


def catalog_dir() -> Path:
    return CATALOG_DIR


def catalog_path() -> Path:
    return CATALOG_DIR / "looks.json"


def _load(name: str) -> dict[str, Any]:
    return json.loads((CATALOG_DIR / name).read_text(encoding="utf-8"))


def _index(rows: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row["id"]
        if key in seen:
            raise ValueError(f"{label}.id 重复：{key}")
        seen[key] = row
    return seen


def load_looks(path: Path | None = None) -> dict[str, Any]:
    if path is not None:
        return json.loads(path.read_text(encoding="utf-8"))
    return _load("looks.json")


def load_catalog(path: Path | None = None) -> dict[str, Any]:
    return load_looks(path)


def load_typography() -> dict[str, Any]:
    return _load("typography.json")


def validate_catalog(data: dict[str, Any]) -> None:
    packs = data.get("packs")
    if not packs:
        raise ValueError("looks.json 缺少 packs")
    seen_shots: set[str] = set()
    for pack_id, pack in packs.items():
        shots = pack.get("shots") or []
        if not shots:
            raise ValueError(f"套餐 {pack_id} 缺少 shots")
        for shot in shots:
            shot_id = shot.get("id") or "<unknown>"
            if shot_id in seen_shots:
                raise ValueError(f"shot.id 重复：{shot_id}")
            seen_shots.add(shot_id)
            prompt = (shot.get("prompt") or "").strip()
            if not prompt:
                raise ValueError(f"{shot_id} 缺少 prompt")
            missing = [name for name in _LOOK_SECTIONS if name not in prompt]
            if missing:
                raise ValueError(f"{shot_id} prompt 须含 {' '.join(missing)}")


def pack_shots(
    data: dict[str, Any],
    pack_id: str,
    *,
    has_print: bool = True,
) -> list[dict[str, Any]]:
    pack = (data.get("packs") or {}).get(pack_id)
    if pack is None:
        raise KeyError(pack_id)
    out: list[dict[str, Any]] = []
    for shot in pack.get("shots") or []:
        requires = set(shot.get("requires") or [])
        if "print" in requires and not has_print:
            continue
        out.append(shot)
    return out


def match_pack(data: dict[str, Any], text: str) -> str:
    blob = text or ""
    packs = data.get("packs") or {}
    default = data.get("default_pack") or "studio"
    for pack_id, pack in packs.items():
        if pack_id == default:
            continue
        for word in pack.get("keywords") or []:
            if word and word in blob:
                return pack_id
    return default if default in packs else next(iter(packs))


def validate_typography(data: dict[str, Any]) -> None:
    if "platforms" not in data:
        raise ValueError("typography.json 缺少 platforms")
    _index(data["platforms"], "platforms")
    required_fields = (
        "id",
        "name",
        "platforms",
        "aesthetic",
        "headline_font",
        "body_font",
        "badge_style",
        "palette",
        "prompt",
        "avoid",
    )
    for row in data["platforms"]:
        pid = row.get("id", "<unknown>")
        for field in required_fields:
            if field not in row:
                raise ValueError(f"typography {pid} 缺少字段：{field}")
        if not (row.get("prompt") or "").strip():
            raise ValueError(f"typography {pid} prompt 不能为空")
        palette = row.get("palette") or {}
        for color_key in ("background", "background_alt", "text", "subtext"):
            val = palette.get(color_key)
            if not val or not _HEX_RE.match(str(val)):
                raise ValueError(
                    f"typography {pid} palette.{color_key} 必须为 6 位 Hex：{val}"
                )
        accent = palette.get("accent")
        if not accent or (
            accent != "product-matched" and not _HEX_RE.match(str(accent))
        ):
            raise ValueError(
                f"typography {pid} palette.accent 必须为 6 位 Hex 或 product-matched：{accent}"
            )
