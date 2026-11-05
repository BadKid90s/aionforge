from pathlib import Path

from aionforge.catalog import (
    catalog_dir,
    catalog_path,
    load_catalog,
    load_scenes,
    load_styles,
    pack_recipes,
    validate_catalog,
    validate_scenes,
    validate_styles,
)


def test_catalog_json_validates() -> None:
    data = load_catalog()
    validate_catalog(data)
    assert catalog_path() == catalog_dir() / "poses.json"
    assert "default-8" in data["packs"]
    assert len(pack_recipes(data, "default-8")) == 8


def test_tee_hoodie_pack_loads() -> None:
    data = load_catalog()
    rows = pack_recipes(data, "tee-hoodie-12", has_hoodie=True, has_print=True)
    ids = [row["id"] for row in rows]
    assert "vary-tee-front-print" in ids
    assert "vary-hoodie-pocket" in ids
    no_hoodie = pack_recipes(data, "tee-hoodie-12", has_hoodie=False, has_print=True)
    assert all("hoodie" not in (row.get("requires") or []) for row in no_hoodie)


def test_scenes_and_styles_validate() -> None:
    scenes = load_scenes()
    styles = load_styles()
    validate_scenes(scenes)
    validate_styles(styles)
    assert any(row["id"] == "studio-offwhite" for row in scenes["scenes"])
    assert any(row["id"] == "pdd-clean" for row in styles["styles"])
    assert any(row["id"] == "campus-quad" for row in scenes["scenes"])
    assert any(row["id"] == "campus-youth" for row in styles["styles"])


def test_pack_skips_print_and_pockets() -> None:
    data = load_catalog()
    lookbook = pack_recipes(data, "lookbook-16", has_print=False, has_pockets=False)
    ids = [row["id"] for row in lookbook]
    assert "vary-print-macro" not in ids
    assert "vary-fabric-macro" in ids
    assert "vary-pockets" not in ids


def test_adding_recipe_only_needs_json(tmp_path: Path) -> None:
    data = load_catalog()
    data["recipes"].append(
        {
            "id": "vary-custom-test",
            "camera": "cam-eye-full",
            "pose": "pose-stand-relax",
            "sells": "试验",
            "keywords": ["试验"],
            "prompt": "正面全身试验镜头。",
        }
    )
    data["packs"]["default-8"]["recipes"].append("vary-custom-test")
    path = tmp_path / "poses.json"
    import json

    path.write_text(json.dumps(data), encoding="utf-8")
    loaded = load_catalog(path)
    validate_catalog(loaded)
    assert pack_recipes(loaded, "default-8")[-1]["id"] == "vary-custom-test"
