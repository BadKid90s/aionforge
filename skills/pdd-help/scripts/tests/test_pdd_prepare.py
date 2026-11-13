"""Unit tests for pdd_prepare.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pdd_prepare


def _make_img(path: Path, size: tuple[int, int], color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)


def test_prepare_and_check_workspace(tmp_path: Path) -> None:
    ws = tmp_path / "demo_tee"
    _make_img(ws / "main" / "tee-white-hero.png", (1024, 1024), (200, 180, 170))
    _make_img(ws / "bg_white" / "tee-white.png", (1024, 1024), (255, 255, 255))
    _make_img(ws / "bg_white" / "tee-white-back.png", (1024, 1024), (255, 255, 255))
    _make_img(ws / "detail" / "long_detail.png", (1000, 2600), (240, 240, 240))

    # Run prepare
    out_dir = tmp_path / "pdd_out"
    parser = pdd_prepare.build_parser()
    args = parser.parse_args(["prepare", str(ws), "--out", str(out_dir)])
    assert args.func(args) == 0

    manifest = json.loads((out_dir / "pdd_manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["main"]) == 1
    assert manifest["main"][0]["width"] == 800
    assert manifest["main"][0]["height"] == 800

    assert len(manifest["white_bg"]) == 2
    # SKU falls back to front images only (excludes -back)
    assert len(manifest["sku"]) == 1
    assert "tee-white.jpg" in manifest["sku"][0]["output"]

    # Detail width 1000->750 scales height 2600->1950, sliced into 2 parts (1500 + 450)
    assert len(manifest["detail"]) == 2
    assert manifest["detail"][0]["width"] == 750
    assert manifest["detail"][0]["height"] == 1500
    assert manifest["detail"][1]["height"] == 450

    listing = json.loads((out_dir / "pdd_listing.json").read_text(encoding="utf-8"))
    assert listing["mode"] == "draft"
    assert len(listing["main_images"]) == 1
    assert "tee-white.jpg" in listing["white_bg_image"]
    assert len(listing["detail_images"]) == 2
    assert listing["sku_colors"][0]["color"] == "白色"
    assert listing["attributes"]["重要面料俗称"] == "棉"
    assert listing["attributes"]["领型"] == "圆领"
    assert listing["attributes"]["品牌"] == "十介美"
    attrs_file = json.loads((out_dir / "pdd_attributes.json").read_text(encoding="utf-8"))
    assert attrs_file["重要服装版型"] == "宽松"


def test_custom_attributes_file_override(tmp_path: Path) -> None:
    ws = tmp_path / "custom_ws"
    _make_img(ws / "main" / "hero.png", (800, 800), (200, 200, 200))
    custom_attrs = tmp_path / "my_attrs.json"
    custom_attrs.write_text(
        json.dumps({"重要面料俗称": "100%新疆长绒棉", "重要平方克重": "230g"}, ensure_ascii=False),
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"
    parser = pdd_prepare.build_parser()
    args = parser.parse_args(
        ["prepare", str(ws), "--out", str(out_dir), "--attributes-file", str(custom_attrs)]
    )
    assert args.func(args) == 0
    exported = json.loads((out_dir / "pdd_attributes.json").read_text(encoding="utf-8"))
    assert exported["重要面料俗称"] == "100%新疆长绒棉"
    assert exported["重要平方克重"] == "230g"


def test_custom_templates_file_override(tmp_path: Path) -> None:
    ws = tmp_path / "tpl_ws"
    _make_img(ws / "main" / "hero.png", (800, 800), (200, 200, 200))
    tpl_file = tmp_path / "my_templates.json"
    tpl_file.write_text(
        json.dumps(
            {"size_template": "短袖T恤", "shipping_template": "短袖T恤包邮"},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out_dir = tmp_path / "out_tpl"
    parser = pdd_prepare.build_parser()
    args = parser.parse_args(
        ["prepare", str(ws), "--out", str(out_dir), "--templates-file", str(tpl_file)]
    )
    assert args.func(args) == 0
    listing = json.loads((out_dir / "pdd_listing.json").read_text(encoding="utf-8"))
    assert listing["size_template"] == "短袖T恤"
    assert listing["shipping_template"] == "短袖T恤包邮"


def test_custom_templates_by_sleeve_profile(tmp_path: Path) -> None:
    ws = tmp_path / "tpl_prof_ws"
    _make_img(ws / "main" / "hero.png", (800, 800), (200, 200, 200))
    tpl_file = tmp_path / "prof_templates.json"
    tpl_file.write_text(
        json.dumps(
            {
                "profiles": {
                    "长袖": {"size_template": "长袖T恤", "shipping_template": "长袖T恤包邮"},
                    "短袖": {"size_template": "短袖T恤", "shipping_template": "短袖T恤包邮"},
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    parser = pdd_prepare.build_parser()

    out_short = tmp_path / "out_short_tpl"
    args_s = parser.parse_args(
        ["prepare", str(ws), "--out", str(out_short), "--profile", "短袖", "--templates-file", str(tpl_file)]
    )
    assert args_s.func(args_s) == 0
    l_short = json.loads((out_short / "pdd_listing.json").read_text(encoding="utf-8"))
    assert l_short["size_template"] == "短袖T恤"
    assert l_short["shipping_template"] == "短袖T恤包邮"

    out_long = tmp_path / "out_long_tpl"
    args_l = parser.parse_args(
        ["prepare", str(ws), "--out", str(out_long), "--profile", "长袖", "--templates-file", str(tpl_file)]
    )
    assert args_l.func(args_l) == 0
    l_long = json.loads((out_long / "pdd_listing.json").read_text(encoding="utf-8"))
    assert l_long["size_template"] == "长袖T恤"
    assert l_long["shipping_template"] == "长袖T恤包邮"


def test_unified_config_file_by_profile(tmp_path: Path) -> None:
    ws = tmp_path / "unified_ws"
    _make_img(ws / "main" / "hero.png", (800, 800), (200, 200, 200))
    cfg_file = tmp_path / "unified_config.json"
    cfg_file.write_text(
        json.dumps(
            {
                "profiles": {
                    "长袖": {
                        "size_template": "长袖T恤",
                        "shipping_template": "长袖包邮",
                        "group_price": 49.9,
                        "single_price": 59.9,
                        "stock": 88,
                        "attributes": {"品牌": "十介美", "重要袖长": "长袖"},
                    },
                    "短袖": {
                        "size_template": "短袖T恤",
                        "shipping_template": "短袖包邮",
                        "group_price": 39.9,
                        "single_price": 49.9,
                        "stock": 66,
                        "attributes": {"品牌": "十介美", "重要袖长": "短袖"},
                    },
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    parser = pdd_prepare.build_parser()
    out_dir = tmp_path / "out_unified"
    args = parser.parse_args(
        ["prepare", str(ws), "--out", str(out_dir), "--profile", "短袖", "--config-file", str(cfg_file)]
    )
    assert args.func(args) == 0
    listing = json.loads((out_dir / "pdd_listing.json").read_text(encoding="utf-8"))
    assert listing["size_template"] == "短袖T恤"
    assert listing["shipping_template"] == "短袖包邮"
    assert listing["group_price"] == 39.9
    assert listing["single_price"] == 49.9
    assert listing["stock"] == 66
    assert listing["attributes"]["品牌"] == "十介美"
    assert listing["attributes"]["重要袖长"] == "短袖"


def test_custom_pricing_by_sleeve_profile(tmp_path: Path) -> None:
    ws = tmp_path / "price_ws"
    _make_img(ws / "main" / "hero.png", (800, 800), (200, 200, 200))
    pricing_file = tmp_path / "my_pricing.json"
    pricing_file.write_text(
        json.dumps(
            {
                "profiles": {
                    "长袖": {"group_price": 49.9, "single_price": 59.9, "stock": 200},
                    "短袖": {"group_price": 39.9, "single_price": 49.9, "stock": 150},
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    parser = pdd_prepare.build_parser()

    out_short = tmp_path / "out_short_p"
    args_s = parser.parse_args(
        [
            "prepare",
            str(ws),
            "--out",
            str(out_short),
            "--profile",
            "短袖",
            "--pricing-file",
            str(pricing_file),
        ]
    )
    assert args_s.func(args_s) == 0
    l_short = json.loads((out_short / "pdd_listing.json").read_text(encoding="utf-8"))
    assert l_short["group_price"] == 39.9
    assert l_short["single_price"] == 49.9
    assert l_short["stock"] == 150

    out_long = tmp_path / "out_long_p"
    args_l = parser.parse_args(
        [
            "prepare",
            str(ws),
            "--out",
            str(out_long),
            "--profile",
            "长袖",
            "--pricing-file",
            str(pricing_file),
        ]
    )
    assert args_l.func(args_l) == 0
    l_long = json.loads((out_long / "pdd_listing.json").read_text(encoding="utf-8"))
    assert l_long["group_price"] == 49.9
    assert l_long["single_price"] == 59.9
    assert l_long["stock"] == 200


def test_short_and_long_sleeve_profiles(tmp_path: Path) -> None:
    ws = tmp_path / "tee_ws"
    _make_img(ws / "main" / "hero.png", (800, 800), (200, 200, 200))

    parser = pdd_prepare.build_parser()

    out_short = tmp_path / "out_short"
    args_short = parser.parse_args(
        ["prepare", str(ws), "--out", str(out_short), "--profile", "短袖"]
    )
    assert args_short.func(args_short) == 0
    attrs_short = json.loads((out_short / "pdd_attributes.json").read_text(encoding="utf-8"))
    assert attrs_short["重要袖长"] == "短袖"
    assert attrs_short["重要上市时节"] == "2026年夏季"
    assert attrs_short["重要衣长"] == "常规款"

    out_long = tmp_path / "out_long"
    args_long = parser.parse_args(
        ["prepare", str(ws), "--out", str(out_long), "--profile", "长袖"]
    )
    assert args_long.func(args_long) == 0
    attrs_long = json.loads((out_long / "pdd_attributes.json").read_text(encoding="utf-8"))
    assert attrs_long["重要袖长"] == "长袖"
    assert attrs_long["重要上市时节"] == "2026年秋季"
    assert attrs_long["重要衣长"] == "中长款"


def test_check_white_bg_fail(tmp_path: Path) -> None:
    ws = tmp_path / "bad_ws"
    _make_img(ws / "bg_white" / "grey.png", (800, 800), (180, 180, 180))
    res = pdd_prepare._check_single_image(ws / "bg_white" / "grey.png", "bg_white")
    assert res.status == "FAIL"
    assert any("白底不纯" in msg for msg in res.issues)


def test_check_title() -> None:
    parser = pdd_prepare.build_parser()

    ok_args = parser.parse_args(["check-title", "2026夏季新款纯棉短袖T恤女宽松百搭印花半袖"])
    assert ok_args.func(ok_args) == 0

    bad_word_args = parser.parse_args(["check-title", "全网最低纯棉短袖T恤女"])
    assert bad_word_args.func(bad_word_args) == 1

    long_title = "纯棉短袖T恤女宽松百搭印花半袖体恤夏装潮流设计感小众上衣女装新款"
    long_args = parser.parse_args(["check-title", long_title])
    assert long_args.func(long_args) == 1
