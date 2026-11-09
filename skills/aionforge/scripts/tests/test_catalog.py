import json
from pathlib import Path

from aionforge.catalog import (
    catalog_dir,
    catalog_path,
    load_catalog,
    load_typography,
    match_pack,
    pack_shots,
    validate_catalog,
    validate_typography,
)


def test_catalog_json_validates() -> None:
    data = load_catalog()
    validate_catalog(data)
    assert catalog_path() == catalog_dir() / "looks.json"
    assert "studio" in data["packs"]
    assert len(pack_shots(data, "studio")) == 10
    assert len(pack_shots(data, "walk")) == 6
    assert len(pack_shots(data, "lifestyle")) == 6


def test_detail_pack_skips_print() -> None:
    data = load_catalog()
    with_print = pack_shots(data, "detail", has_print=True)
    assert any(row["id"] == "detail-print" for row in with_print)
    no_print = pack_shots(data, "detail", has_print=False)
    assert all(row["id"] != "detail-print" for row in no_print)
    assert any(row["id"] == "detail-fabric" for row in no_print)


def test_match_pack_keywords() -> None:
    data = load_catalog()
    assert match_pack(data, "这张再裂变几个机位") == "studio"
    assert match_pack(data, "走两步动态 lookbook") == "walk"
    assert match_pack(data, "窗光生活场景") == "lifestyle"
    assert match_pack(data, "只要面料特写") == "detail"


def test_typography_validates() -> None:
    typography = load_typography()
    validate_typography(typography)
    typo_ids = {row["id"] for row in typography["platforms"]}
    assert typo_ids == {"pinduoduo", "taobao", "jd", "douyin_xhs", "amazon", "shopify"}


def test_pinduoduo_typography_is_clean_editorial() -> None:
    typography = load_typography()
    pdd = next(row for row in typography["platforms"] if row["id"] == "pinduoduo")
    assert pdd["palette"]["background"] == "#F7F5F2"
    assert "no black stroke" in pdd["prompt"]


def test_adding_look_shot_only_needs_json(tmp_path: Path) -> None:
    data = load_catalog()
    data["packs"]["studio"]["shots"].append(
        {
            "id": "studio-custom-test",
            "name": "试验",
            "prompt": "【场景】棚。\n【风格】写实。\n【镜头语言】平视全身。\n【主体动作】站立。",
        }
    )
    path = tmp_path / "looks.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    loaded = load_catalog(path)
    validate_catalog(loaded)
    assert pack_shots(loaded, "studio")[-1]["id"] == "studio-custom-test"
