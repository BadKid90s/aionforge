"""定义目录：姿势 / 场景 / 风格。数据在 Skill 的 references/catalog/，增删只改 JSON。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# scripts/aionforge/catalog.py → Skill 根目录
CATALOG_DIR = Path(__file__).resolve().parents[2] / "references" / "catalog"


def catalog_dir() -> Path:
    return CATALOG_DIR


def catalog_path() -> Path:
    """姿势目录文件（兼容旧调用）。"""
    return CATALOG_DIR / "poses.json"


def _load(name: str) -> dict[str, Any]:
    path = CATALOG_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def _index(rows: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row["id"]
        if key in seen:
            raise ValueError(f"{label}.id 重复：{key}")
        seen[key] = row
    return seen


def load_poses(path: Path | None = None) -> dict[str, Any]:
    if path is not None:
        return json.loads(path.read_text(encoding="utf-8"))
    return _load("poses.json")


def load_scenes() -> dict[str, Any]:
    return _load("scenes.json")


def load_styles() -> dict[str, Any]:
    return _load("styles.json")


def load_catalog(path: Path | None = None) -> dict[str, Any]:
    return load_poses(path)


def validate_catalog(data: dict[str, Any]) -> None:
    for key in ("version", "cameras", "poses", "recipes", "packs"):
        if key not in data:
            raise ValueError(f"poses.json 缺少字段：{key}")
    cameras = _index(data["cameras"], "cameras")
    poses = _index(data["poses"], "poses")
    recipes = _index(data["recipes"], "recipes")
    for recipe in data["recipes"]:
        if recipe["camera"] not in cameras:
            raise ValueError(f"{recipe['id']} 引用了不存在的 camera {recipe['camera']}")
        if recipe["pose"] not in poses:
            raise ValueError(f"{recipe['id']} 引用了不存在的 pose {recipe['pose']}")
        if not (recipe.get("prompt") or "").strip():
            raise ValueError(f"{recipe['id']} 缺少 prompt")
    for pack_id, pack in data["packs"].items():
        for recipe_id in pack.get("recipes") or []:
            if recipe_id not in recipes:
                raise ValueError(f"套餐 {pack_id} 引用了不存在的配方 {recipe_id}")


def validate_scenes(data: dict[str, Any]) -> None:
    if "scenes" not in data:
        raise ValueError("scenes.json 缺少 scenes")
    _index(data["scenes"], "scenes")
    for row in data["scenes"]:
        if not (row.get("prompt") or "").strip():
            raise ValueError(f"{row.get('id')} 缺少 prompt")


def validate_styles(data: dict[str, Any]) -> None:
    if "styles" not in data:
        raise ValueError("styles.json 缺少 styles")
    _index(data["styles"], "styles")
    for row in data["styles"]:
        if not (row.get("style_lock") or "").strip():
            raise ValueError(f"{row.get('id')} 缺少 style_lock")
        palette = row.get("palette") or {}
        if not palette.get("background") or not palette.get("text"):
            raise ValueError(f"{row.get('id')} palette 需要 background 与 text")


def get_recipe(data: dict[str, Any], recipe_id: str) -> dict[str, Any]:
    for row in data["recipes"]:
        if row["id"] == recipe_id:
            return row
    raise KeyError(recipe_id)


def pack_recipes(
    data: dict[str, Any],
    pack_id: str,
    *,
    has_print: bool = True,
    has_pockets: bool = True,
    has_hoodie: bool = True,
    pants: bool = False,
) -> list[dict[str, Any]]:
    pack = data["packs"].get(pack_id)
    if pack is None:
        raise KeyError(pack_id)
    subs = data.get("substitutions") or {}
    mapping: dict[str, str] = {}
    if not has_print:
        mapping.update(subs.get("no_print") or {})
    if pants:
        mapping.update(subs.get("pants") or {})
    recipes = _index(data["recipes"], "recipes")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for recipe_id in pack["recipes"]:
        recipe_id = mapping.get(recipe_id, recipe_id)
        recipe = recipes[recipe_id]
        requires = set(recipe.get("requires") or [])
        if "print" in requires and not has_print:
            continue
        if "pockets" in requires and not has_pockets:
            continue
        if "hoodie" in requires and not has_hoodie:
            continue
        if recipe_id in seen:
            continue
        seen.add(recipe_id)
        out.append(recipe)
    return out
