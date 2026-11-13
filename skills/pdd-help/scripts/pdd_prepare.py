# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pillow>=10.0.0",
# ]
# ///
"""拼多多（PDD）商品素材合规检测与上架尺寸适配工具。"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from PIL import Image, ImageOps

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
MAX_FILE_BYTES = 3 * 1024 * 1024  # 拼多多单张图片上限 3MB
RECOMMENDED_FILE_BYTES = 1 * 1024 * 1024  # 建议 ≤ 1MB

PROHIBITED_WORDS = [
    "第一",
    "唯一",
    "顶级",
    "极致",
    "绝对",
    "100%",
    "全网最低",
    "全网首发",
    "销量冠军",
    "国家级",
    "王牌",
    "永久",
    "万能",
    "假一赔十",
    "零差评",
    "无效退款",
    "秒杀全网",
    "最好",
    "最低价",
    "最高级",
]


@dataclass
class CheckResult:
    category: str
    file: str
    width: int
    height: int
    size_bytes: int
    status: Literal["PASS", "WARN", "FAIL"]
    issues: list[str]
    corner_rgb_avg: float | None = None


def _is_image(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTS and not path.name.startswith(".")


def _list_images(directory: Path) -> list[Path]:
    if not directory.exists() or not directory.is_dir():
        return []
    return sorted(p for p in directory.iterdir() if _is_image(p))


def _measure_white_bg_corners(img: Image.Image) -> float:
    """采样四角及四边中点 8x8 区域，返回平均亮度 (0-255)。"""
    rgb = img.convert("RGB")
    w, h = rgb.size
    patch = min(8, max(1, w // 20), max(1, h // 20))
    coords = [
        (0, 0),
        (w - patch, 0),
        (0, h - patch),
        (w - patch, h - patch),
        (w // 2 - patch // 2, 0),
        (w // 2 - patch // 2, h - patch),
        (0, h // 2 - patch // 2),
        (w - patch, h // 2 - patch // 2),
    ]
    total = 0.0
    count = 0
    for x0, y0 in coords:
        crop = rgb.crop((x0, y0, x0 + patch, y0 + patch))
        raw_bytes = crop.tobytes()
        for i in range(0, len(raw_bytes), 3):
            total += (raw_bytes[i] + raw_bytes[i + 1] + raw_bytes[i + 2]) / 3.0
            count += 1
    return round(total / max(1, count), 1)


def _check_single_image(path: Path, category: str) -> CheckResult:
    size_bytes = path.stat().st_size
    issues: list[str] = []
    status: Literal["PASS", "WARN", "FAIL"] = "PASS"
    corner_avg: float | None = None

    with Image.open(path) as raw:
        img = ImageOps.exif_transpose(raw)
        w, h = img.size

        if size_bytes > MAX_FILE_BYTES:
            issues.append(f"体积超限 ({size_bytes / 1024 / 1024:.2f}MB > 3MB)")
            status = "FAIL"
        elif size_bytes > RECOMMENDED_FILE_BYTES:
            issues.append(f"体积偏大 ({size_bytes / 1024 / 1024:.2f}MB，建议 ≤ 1MB)")
            if status == "PASS":
                status = "WARN"

        if category in {"main", "bg_white", "sku"}:
            if w < 480 or h < 480:
                issues.append(f"分辨率过低 ({w}x{h} < 480x480)")
                status = "FAIL"
            elif w != h:
                issues.append(f"非 1:1 正方形 ({w}x{h})，建议适配为 800x800")
                if status == "PASS":
                    status = "WARN"
            elif w != 800:
                issues.append(f"当前为 {w}x{h}，拼多多标准推荐 800x800")
                if status == "PASS":
                    status = "WARN"

        if category == "bg_white":
            if img.mode == "RGBA":
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3])
                corner_avg = _measure_white_bg_corners(bg)
            else:
                corner_avg = _measure_white_bg_corners(img)

            if corner_avg < 235:
                issues.append(f"白底不纯 (边缘平均亮度 {corner_avg} < 235，需纯白 #FFFFFF)")
                status = "FAIL"
            elif corner_avg < 245:
                issues.append(f"白底略偏灰 (边缘平均亮度 {corner_avg} < 245)")
                if status == "PASS":
                    status = "WARN"

        if category == "detail":
            if w < 480 or w > 1200:
                issues.append(f"详情图宽度 {w}px 不在 480-1200px 范围，建议统一 750px")
                if status == "PASS":
                    status = "WARN"
            if h > 1500:
                issues.append(f"单张高度 {h}px > 1500px，建议自动切分")
                if status == "PASS":
                    status = "WARN"

    return CheckResult(
        category=category,
        file=str(path),
        width=w,
        height=h,
        size_bytes=size_bytes,
        status=status,
        issues=issues,
        corner_rgb_avg=corner_avg,
    )


def _discover_categories(target: Path) -> dict[str, list[Path]]:
    """自动识别工作区子目录或单目录素材。"""
    sub_map = {
        "main": _list_images(target / "main"),
        "bg_white": _list_images(target / "bg_white"),
        "detail": _list_images(target / "detail"),
        "sku": _list_images(target / "sku"),
        "auxiliary": _list_images(target / "auxiliary"),
    }
    if any(sub_map.values()):
        return {k: v for k, v in sub_map.items() if v}

    flat_imgs = _list_images(target)
    if flat_imgs:
        return {"main": flat_imgs}
    return {}


def _to_rgb_white_bg(img: Image.Image) -> Image.Image:
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[3])
        return bg
    return img.convert("RGB")


def _fit_square(img: Image.Image, size: int, mode: Literal["cover", "contain"]) -> Image.Image:
    rgb = _to_rgb_white_bg(img)
    if mode == "cover":
        return ImageOps.fit(rgb, (size, size), method=Image.Resampling.LANCZOS)
    contained = ImageOps.contain(rgb, (size, size), method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (size, size), (255, 255, 255))
    offset = ((size - contained.width) // 2, (size - contained.height) // 2)
    canvas.paste(contained, offset)
    return canvas


COLOR_ZH_MAP = {
    "black": "黑色",
    "white": "白色",
    "offwhite": "米白色",
    "navy": "藏青色",
    "darkgrey": "深灰色",
    "lightgrey": "浅灰色",
    "grey": "灰色",
    "gray": "灰色",
    "red": "红色",
    "pink": "粉色",
    "blue": "蓝色",
    "green": "绿色",
    "yellow": "黄色",
    "brown": "棕色",
    "khaki": "卡其色",
    "beige": "杏色",
    "purple": "紫色",
}


def _load_workspace_facts(target: Path) -> dict[str, object]:
    """尝试从 .forge/products/*/facts.json 读取商品事实。"""
    forge_products = target / ".forge" / "products"
    if not forge_products.exists():
        return {}
    for facts_file in sorted(forge_products.glob("*/facts.json")):
        try:
            data = json.loads(facts_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError):
            continue
    return {}


def _infer_color_label(stem: str) -> str:
    lower = stem.lower()
    for key, zh in COLOR_ZH_MAP.items():
        if f"-{key}" in lower or lower.endswith(key):
            return zh
    return stem


DEFAULT_CONFIG_FILE = (
    Path(__file__).resolve().parent.parent / "references" / "default-config.json"
)
DEFAULT_ATTRIBUTES_FILE = DEFAULT_CONFIG_FILE
DEFAULT_TEMPLATES_FILE = DEFAULT_CONFIG_FILE
DEFAULT_PRICING_FILE = DEFAULT_CONFIG_FILE


def _load_pricing_file(path: Path, profile: str) -> dict[str, object]:
    """按长袖/短袖模板读取拼单价、单买价与库存配置。"""
    empty: dict[str, object] = {"group_price": None, "single_price": None, "stock": 100}
    if not path.is_file():
        return empty
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty
    if not isinstance(raw, dict):
        return empty

    block: dict[str, object] = {}
    profiles = raw.get("profiles")
    if isinstance(profiles, dict) and isinstance(profiles.get(profile), dict):
        block = profiles[profile]
    elif "group_price" in raw or "single_price" in raw:
        block = raw

    return {
        "group_price": block.get("group_price"),
        "single_price": block.get("single_price"),
        "stock": block.get("stock") if block.get("stock") is not None else 100,
    }


def _load_templates_file(path: Path, profile: str | None = None) -> dict[str, str]:
    """读取尺码模板与运费模板配置，支持按长袖/短袖 profiles 分开配置及旧版平铺格式。"""
    if not path.is_file():
        return {"size_template": "", "shipping_template": ""}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"size_template": "", "shipping_template": ""}
    if not isinstance(raw, dict):
        return {"size_template": "", "shipping_template": ""}

    block: dict[str, object] = {}
    if "profiles" in raw and isinstance(raw["profiles"], dict):
        if isinstance(raw.get("default"), dict):
            block.update(raw["default"])
        if profile and isinstance(raw["profiles"].get(profile), dict):
            block.update(raw["profiles"][profile])
    else:
        block = raw

    return {
        "size_template": str(block.get("size_template") or "").strip(),
        "shipping_template": str(block.get("shipping_template") or "").strip(),
    }


def _normalize_profile_name(profile: str | None, product_name: str, facts: dict[str, object]) -> str:
    if profile:
        low = profile.strip().lower()
        if low in {"short", "short_sleeve", "短袖"}:
            return "短袖"
        if low in {"long", "long_sleeve", "长袖"}:
            return "长袖"
        return profile.strip()
    vf = facts.get("visual_features")
    sleeve = str(vf.get("sleeve") or "").strip() if isinstance(vf, dict) else ""
    if "短袖" in sleeve or "短袖" in product_name or "short" in product_name.lower():
        return "短袖"
    return "长袖"


def _load_attributes_file(
    path: Path, category: str, profile: str | None = None
) -> dict[str, str]:
    """从 JSON 属性文件读取默认属性、袖型模板（短袖/长袖）及对应类目属性。"""
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}

    merged: dict[str, str] = {}
    non_attr_keys = {
        "size_template",
        "shipping_template",
        "group_price",
        "single_price",
        "stock",
        "attributes",
    }
    if "default" in raw or "by_category" in raw or "profiles" in raw or "attributes" in raw:
        if isinstance(raw.get("attributes"), dict):
            merged.update({str(k): str(v) for k, v in raw["attributes"].items()})
        default_block = raw.get("default")
        if isinstance(default_block, dict):
            attrs_sub = default_block.get("attributes")
            src_def = attrs_sub if isinstance(attrs_sub, dict) else default_block
            merged.update(
                {str(k): str(v) for k, v in src_def.items() if k not in non_attr_keys and not isinstance(v, dict)}
            )
        profiles = raw.get("profiles")
        if profile and isinstance(profiles, dict):
            prof_block = profiles.get(profile)
            if isinstance(prof_block, dict):
                attrs_sub = prof_block.get("attributes")
                src_prof = attrs_sub if isinstance(attrs_sub, dict) else prof_block
                merged.update(
                    {str(k): str(v) for k, v in src_prof.items() if k not in non_attr_keys and not isinstance(v, dict)}
                )
        by_cat = raw.get("by_category")
        if isinstance(by_cat, dict):
            leaf = category.split(">")[-1].strip()
            for cat_key, cat_vals in by_cat.items():
                if isinstance(cat_vals, dict) and (cat_key in category or cat_key == leaf):
                    merged.update({str(k): str(v) for k, v in cat_vals.items()})
        return merged

    return {
        str(k): str(v)
        for k, v in raw.items()
        if k not in non_attr_keys and not isinstance(v, dict)
    }


def _infer_attributes(
    facts: dict[str, object],
    product_name: str,
    category: str,
    custom_attrs_file: Path | None = None,
    profile: str | None = None,
) -> dict[str, str]:
    """合并默认属性文件（短袖/长袖两套素禾母版）、facts.json 视觉特征与自定义属性文件。"""
    resolved_profile = _normalize_profile_name(profile, product_name, facts)
    attrs = _load_attributes_file(DEFAULT_ATTRIBUTES_FILE, category, resolved_profile)

    vf = facts.get("visual_features")
    vf_dict = vf if isinstance(vf, dict) else {}
    materials = facts.get("materials_visible")
    if isinstance(materials, list) and materials:
        attrs["重要面料俗称"] = str(materials[0]).strip()
    sleeve = str(vf_dict.get("sleeve") or "").strip()
    if sleeve:
        attrs["重要袖长"] = sleeve
    if str(vf_dict.get("neckline") or "").strip():
        attrs["领型"] = str(vf_dict["neckline"]).strip()
    if str(vf_dict.get("silhouette") or "").strip():
        attrs["重要服装版型"] = str(vf_dict["silhouette"]).strip()
    if str(vf_dict.get("length") or "").strip():
        attrs["重要衣长"] = str(vf_dict["length"]).strip()

    if custom_attrs_file is not None:
        attrs.update(_load_attributes_file(custom_attrs_file, category, resolved_profile))

    return attrs


def _build_listing_payload(
    target: Path,
    manifest: dict[str, list[dict[str, object]]],
    facts: dict[str, object],
    custom_attrs_file: Path | None = None,
    profile: str | None = None,
    custom_templates_file: Path | None = None,
    custom_pricing_file: Path | None = None,
) -> dict[str, object]:
    product_name = str(facts.get("product_name") or target.name).strip()
    category = str(facts.get("category") or "女装/女士精品 > T恤 > T恤").strip()
    if category == "T恤":
        category = "女装/女士精品 > T恤 > T恤"

    aux_list = [str(item["output"]) for item in manifest.get("auxiliary", [])]
    aux_long = next((p for p in aux_list if Path(p).stem.endswith("-long")), "")
    aux_white = next(
        (p for p in aux_list if Path(p).stem.endswith("-white") and p != aux_long), ""
    )

    white_bg_list = [str(item["output"]) for item in manifest["white_bg"]]
    preferred_white_bg = aux_white or next(
        (p for p in white_bg_list if "-back" not in Path(p).stem),
        white_bg_list[0] if white_bg_list else "",
    )

    sku_items = [
        {
            "color": _infer_color_label(Path(str(item["output"])).stem),
            "image": str(item["output"]),
        }
        for item in manifest["sku"]
    ]

    resolved_profile = _normalize_profile_name(profile, product_name, facts)

    templates = _load_templates_file(DEFAULT_TEMPLATES_FILE, resolved_profile)
    if custom_templates_file is not None:
        custom_tpl = _load_templates_file(custom_templates_file, resolved_profile)
        for key in ("size_template", "shipping_template"):
            if custom_tpl.get(key):
                templates[key] = custom_tpl[key]

    pricing = _load_pricing_file(DEFAULT_PRICING_FILE, resolved_profile)
    if custom_pricing_file is not None:
        custom_price = _load_pricing_file(custom_pricing_file, resolved_profile)
        for key in ("group_price", "single_price", "stock"):
            if custom_price.get(key) is not None:
                pricing[key] = custom_price[key]

    attrs = _infer_attributes(facts, product_name, category, custom_attrs_file, profile)
    title_candidates = _generate_tshirt_titles(
        facts,
        attrs,
        resolved_profile,
        formula="all",
        config_file=custom_templates_file or custom_attrs_file or DEFAULT_CONFIG_FILE,
    )

    return {
        "mode": "draft",
        "profile": resolved_profile,
        "title": str(title_candidates[0]["title"]),
        "title_candidates": title_candidates,
        "category": category,
        "size_template": templates["size_template"],
        "shipping_template": templates["shipping_template"],
        "attributes": attrs,
        "main_images": [str(item["output"]) for item in manifest["main"]][:10],
        "white_bg_image": preferred_white_bg,
        "long_image": aux_long,
        "detail_images": [str(item["output"]) for item in manifest["detail"]],
        "sku_colors": sku_items,
        "sizes": ["S", "M", "L", "XL"],
        "group_price": pricing["group_price"],
        "single_price": pricing["single_price"],
        "stock": pricing["stock"],
    }


def _save_image(img: Image.Image, dest: Path, fmt: Literal["jpg", "png"]) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "png":
        img.save(dest, format="PNG", optimize=True)
        return dest.stat().st_size

    quality = 92
    while quality >= 70:
        img.save(dest, format="JPEG", quality=quality, optimize=True)
        size = dest.stat().st_size
        if size <= MAX_FILE_BYTES:
            return size
        quality -= 6
    return dest.stat().st_size


def cmd_check(args: argparse.Namespace) -> int:
    target = Path(args.target).resolve()
    if not target.exists():
        print(f"错误: 目录不存在: {target}", file=sys.stderr)
        return 1

    categories = _discover_categories(target)
    if not categories:
        print(f"未在 {target} 中发现图片文件。", file=sys.stderr)
        return 1

    results: list[CheckResult] = []
    for cat, files in categories.items():
        for f in files:
            results.append(_check_single_image(f, cat))

    if args.json:
        print(json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2))
    else:
        counts = {"PASS": 0, "WARN": 0, "FAIL": 0}
        for r in results:
            counts[r.status] += 1
            rel = Path(r.file).name
            issue_str = "；".join(r.issues) if r.issues else "符合拼多多规范"
            print(
                f"[{r.status}] ({r.category}) {rel} | "
                f"{r.width}x{r.height} | {r.size_bytes / 1024:.0f}KB | {issue_str}"
            )
        print(
            f"\n汇总: 共 {len(results)} 张 — "
            f"PASS {counts['PASS']} / WARN {counts['WARN']} / FAIL {counts['FAIL']}"
        )

    return 1 if any(r.status == "FAIL" for r in results) else 0


def cmd_prepare(args: argparse.Namespace) -> int:
    target = Path(args.target).resolve()
    if not target.exists():
        print(f"错误: 目录不存在: {target}", file=sys.stderr)
        return 1

    categories = _discover_categories(target)
    if not categories:
        print(f"未在 {target} 中发现图片文件。", file=sys.stderr)
        return 1

    out_dir = Path(args.out).resolve() if args.out else target / "pdd_ready"
    fmt: Literal["jpg", "png"] = args.format
    ext = ".jpg" if fmt == "jpg" else ".png"

    manifest: dict[str, list[dict[str, object]]] = {
        "main": [],
        "white_bg": [],
        "detail": [],
        "sku": [],
        "auxiliary": [],
    }

    # 1. 主图 -> 01_main/ (800x800, cover)
    for idx, src in enumerate(categories.get("main", []), start=1):
        with Image.open(src) as raw:
            out_img = _fit_square(raw, args.main_size, args.fit)
        dest = out_dir / "01_main" / f"{idx:02d}_{src.stem}{ext}"
        size_bytes = _save_image(out_img, dest, fmt)
        manifest["main"].append(
            {
                "source": str(src),
                "output": str(dest),
                "width": out_img.width,
                "height": out_img.height,
                "size_kb": round(size_bytes / 1024, 1),
            }
        )

    # 2. 白底图 -> 02_white_bg/ (800x800, contain on pure white)
    for src in categories.get("bg_white", []):
        with Image.open(src) as raw:
            out_img = _fit_square(raw, args.main_size, "contain")
        dest = out_dir / "02_white_bg" / f"{src.stem}{ext}"
        size_bytes = _save_image(out_img, dest, fmt)
        manifest["white_bg"].append(
            {
                "source": str(src),
                "output": str(dest),
                "width": out_img.width,
                "height": out_img.height,
                "size_kb": round(size_bytes / 1024, 1),
            }
        )

    # 3. 详情图 -> 03_detail/ (width=750, slice if height > max_detail_height)
    for idx, src in enumerate(categories.get("detail", []), start=1):
        with Image.open(src) as raw:
            rgb = _to_rgb_white_bg(raw)
            new_h = max(1, round(rgb.height * (args.detail_width / rgb.width)))
            resized = rgb.resize((args.detail_width, new_h), Image.Resampling.LANCZOS)

        max_h = args.max_detail_height
        if resized.height <= max_h:
            dest = out_dir / "03_detail" / f"{idx:02d}_{src.stem}{ext}"
            size_bytes = _save_image(resized, dest, fmt)
            manifest["detail"].append(
                {
                    "source": str(src),
                    "output": str(dest),
                    "width": resized.width,
                    "height": resized.height,
                    "size_kb": round(size_bytes / 1024, 1),
                }
            )
        else:
            part = 1
            for y0 in range(0, resized.height, max_h):
                y1 = min(resized.height, y0 + max_h)
                slice_img = resized.crop((0, y0, resized.width, y1))
                dest = out_dir / "03_detail" / f"{idx:02d}_{src.stem}_part{part}{ext}"
                size_bytes = _save_image(slice_img, dest, fmt)
                manifest["detail"].append(
                    {
                        "source": str(src),
                        "output": str(dest),
                        "width": slice_img.width,
                        "height": slice_img.height,
                        "size_kb": round(size_bytes / 1024, 1),
                    }
                )
                part += 1

    # 4. SKU 图 -> 04_sku/ (优先使用 sku/，否则取 bg_white/ 正面图)
    sku_sources = categories.get("sku", [])
    if not sku_sources:
        sku_sources = [p for p in categories.get("bg_white", []) if "-back" not in p.stem]

    for src in sku_sources:
        with Image.open(src) as raw:
            out_img = _fit_square(raw, args.main_size, "contain")
        dest = out_dir / "04_sku" / f"{src.stem}{ext}"
        size_bytes = _save_image(out_img, dest, fmt)
        manifest["sku"].append(
            {
                "source": str(src),
                "output": str(dest),
                "width": out_img.width,
                "height": out_img.height,
                "size_kb": round(size_bytes / 1024, 1),
            }
        )

    # 5. 商品辅助图 -> 05_auxiliary/ (白底图 1:1 800x800, 长图 2:3 800x1200)
    for src in categories.get("auxiliary", []):
        with Image.open(src) as raw:
            rgb = _to_rgb_white_bg(raw)
            if "-long" in src.stem:
                out_img = ImageOps.fit(
                    rgb, (args.main_size, int(args.main_size * 1.5)), method=Image.Resampling.LANCZOS
                )
            else:
                out_img = _fit_square(rgb, args.main_size, "contain")
        dest = out_dir / "05_auxiliary" / f"{src.stem}{ext}"
        size_bytes = _save_image(out_img, dest, fmt)
        manifest["auxiliary"].append(
            {
                "source": str(src),
                "output": str(dest),
                "width": out_img.width,
                "height": out_img.height,
                "size_kb": round(size_bytes / 1024, 1),
            }
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "pdd_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    facts = _load_workspace_facts(target)
    custom_cfg = Path(args.config_file).resolve() if args.config_file else None
    custom_attrs = Path(args.attributes_file).resolve() if args.attributes_file else custom_cfg
    custom_tpls = Path(args.templates_file).resolve() if args.templates_file else custom_cfg
    custom_pricing = Path(args.pricing_file).resolve() if args.pricing_file else custom_cfg
    listing_payload = _build_listing_payload(
        target, manifest, facts, custom_attrs, args.profile, custom_tpls, custom_pricing
    )
    attrs_path = out_dir / "pdd_attributes.json"
    attrs_path.write_text(
        json.dumps(listing_payload["attributes"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    listing_path = out_dir / "pdd_listing.json"
    listing_path.write_text(
        json.dumps(listing_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(
        f"已导出拼多多上架素材至: {out_dir}\n"
        f"  - 主图 (01_main): {len(manifest['main'])} 张\n"
        f"  - 白底图 (02_white_bg): {len(manifest['white_bg'])} 张\n"
        f"  - 详情图 (03_detail): {len(manifest['detail'])} 张\n"
        f"  - SKU 图 (04_sku): {len(manifest['sku'])} 张\n"
        f"  - 清单文件: {manifest_path}\n"
        f"  - 属性文件: {attrs_path}\n"
        f"  - 上架数据: {listing_path}"
    )
    return 0


def _pdd_char_len(text: str) -> int:
    """拼多多标题长度计算：全角/中文=2，半角=1（上限 60）。"""
    total = 0
    for ch in text:
        if unicodedata.east_asian_width(ch) in {"F", "W", "A"} or ord(ch) > 127:
            total += 2
        else:
            total += 1
    return total


MAX_TITLE_UNITS = 60

MUTUALLY_EXCLUSIVE_TOKEN_GROUPS: list[set[str]] = [
    {"宽松", "修身", "紧身", "显瘦收腰"},
    {"短袖", "长袖", "五分袖", "七分袖"},
    {"圆领", "V领", "半高领", "高领", "POLO领"},
]

CORE_ROOT_TOKENS: tuple[str, ...] = (
    "T恤",
    "纯棉",
    "印花",
    "宽松",
    "修身",
    "紧身",
    "圆领",
    "V领",
    "韩版",
    "韩系",
    "美式",
    "复古",
    "法式",
    "甜酷",
    "设计感",
    "小众",
    "显瘦",
    "遮肉",
    "叠穿",
    "打底",
    "百搭",
    "上衣",
    "体恤",
    "半袖",
    "短袖",
    "长袖",
    "夏季",
    "秋季",
    "新款",
)


def _sanitize_title_token(token: str) -> str:
    """移除违禁词、多余空白与标点，保证标题词干净合规。"""
    cleaned = token.strip()
    for word in PROHIBITED_WORDS:
        if word in cleaned:
            cleaned = cleaned.replace(word, "")
    cleaned = re.sub(r"[\s/|·,，。!！?？]+", "", cleaned)
    return cleaned


def _has_mutually_exclusive_conflict(token: str, current_title: str) -> bool:
    """检查待追加词与已选词是否存在互斥冲突（如宽松与修身）。"""
    for group in MUTUALLY_EXCLUSIVE_TOKEN_GROUPS:
        token_hits = {item for item in group if item in token}
        if not token_hits:
            continue
        existing_hits = {item for item in group if item in current_title}
        if existing_hits and not token_hits.issubset(existing_hits):
            return True
    return False


def _has_root_overlap(token: str, current_title: str) -> bool:
    """检查词根是否已出现在当前标题中，避免重复堆砌关键词。"""
    if not token:
        return True
    lowered_title = current_title.lower()
    if token.lower() in lowered_title:
        return True
    for root in CORE_ROOT_TOKENS:
        if root in token and root.lower() in lowered_title:
            return True
    return False


LOGO_MOTIF_MAP: tuple[tuple[str, str], ...] = (
    ("daisy", "小雏菊印花"),
    ("flower", "花卉印花"),
    ("butterfly", "蝴蝶印花"),
    ("dog", "卡通小狗印花"),
    ("cat", "猫咪印花"),
    ("bear", "小熊印花"),
    ("boba", "趣味卡通印花"),
    ("romantic", "浪漫标语印花"),
    ("los-angeles", "美式字母印花"),
    ("happy", "英文标语印花"),
    ("positive", "字母标语印花"),
    ("liberty", "复古标语印花"),
)


def _load_title_hot_keywords(config_file: Path | None = None) -> dict[str, object]:
    """从统一配置文件（如 default-config.json）加载拼多多女装 T 恤热搜词库。"""
    for path in (config_file, DEFAULT_CONFIG_FILE):
        if path and path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            hot_kw = data.get("title_hot_keywords")
            if isinstance(hot_kw, dict):
                return hot_kw
    return {}


def _infer_title_theme(
    facts: dict[str, object], extra_keywords: list[str] | None = None
) -> str:
    """根据印花元素、logo 标识与用户关键词识别热搜风格分组。"""
    joined = " ".join(
        [
            str(facts.get("logo") or ""),
            str(facts.get("product_name") or ""),
            *(extra_keywords or []),
        ]
    ).lower()
    if any(k in joined for k in ("daisy", "flower", "butterfly", "romantic", "花", "蝴蝶", "法式", "温柔")):
        return "floral"
    if any(k in joined for k in ("los-angeles", "happy", "positive", "liberty", "retro", "23", "美式", "复古", "字母", "标语", "街头")):
        return "retro_street"
    if any(k in joined for k in ("dog", "cat", "bear", "boba", "卡通", "小狗", "可爱", "学院")):
        return "cartoon"
    return "general"


def _has_back_print(facts: dict[str, object]) -> bool:
    """判断商品是否包含后背主印花，用于精准匹配「后背印花」热搜词。"""
    print_info = facts.get("print")
    if isinstance(print_info, dict):
        placements = print_info.get("placements")
        if isinstance(placements, list):
            for p in placements:
                if isinstance(p, dict) and str(p.get("side") or "").lower() == "back":
                    return True
    colors = facts.get("colors")
    if isinstance(colors, list):
        for c in colors:
            if isinstance(c, dict) and str(c.get("bg_white_back") or "").strip():
                return True
    return False


def _rotate_list(items: list[str], seed: int, offset: int = 0) -> list[str]:
    """按确定性偏移轮换热搜词顺序，避免同店多款标题高度雷同。"""
    if not items:
        return []
    idx = (seed + offset) % len(items)
    return items[idx:] + items[:idx]


def _extract_print_descriptor(
    facts: dict[str, object], extra_keywords: list[str] | None = None, fallback: str = "创意印花"
) -> str:
    """从工作区 facts 或用户关键词中提取具体印花/设计词。"""
    back_prefix = "后背" if _has_back_print(facts) else ""

    for kw in extra_keywords or []:
        cleaned = _sanitize_title_token(kw)
        if cleaned and _pdd_char_len(cleaned) <= 12:
            if "印花" in cleaned or "图案" in cleaned or "刺绣" in cleaned:
                return cleaned
            return f"{cleaned}印花" if _pdd_char_len(cleaned) <= 8 else cleaned

    print_info = facts.get("print")
    if isinstance(print_info, dict):
        if print_info.get("has_print") is False:
            return "简约纯色"
        text_exact = _sanitize_title_token(str(print_info.get("text_exact") or ""))
        if text_exact and _pdd_char_len(text_exact) <= 8:
            return f"{back_prefix}{text_exact}印花"
        for key in ("theme", "motif", "style"):
            val = _sanitize_title_token(str(print_info.get(key) or ""))
            if val and _pdd_char_len(val) <= 10:
                base = val if "印花" in val else f"{val}印花"
                return f"{back_prefix}{base}" if back_prefix and _pdd_char_len(base) <= 8 else base
        visual_kws = print_info.get("visual_keywords")
        if isinstance(visual_kws, list) and visual_kws:
            first_kw = _sanitize_title_token(str(visual_kws[0]))
            if first_kw and _pdd_char_len(first_kw) <= 8:
                base = first_kw if "印花" in first_kw else f"{first_kw}印花"
                return f"{back_prefix}{base}" if back_prefix and _pdd_char_len(base) <= 8 else base

    logo_slug = str(facts.get("logo") or "").lower()
    for motif, label in LOGO_MOTIF_MAP:
        if motif in logo_slug:
            if back_prefix and _pdd_char_len(back_prefix + label) <= 12:
                return f"{back_prefix}{label}"
            return label

    return f"{back_prefix}{fallback}" if back_prefix else fallback


def _extract_title_slots(
    facts: dict[str, object],
    attributes: dict[str, str],
    profile: str,
    extra_keywords: list[str] | None = None,
) -> dict[str, str]:
    """从属性与工作区事实提取女装 T 恤标题各槽位。"""
    resolved_profile = "长袖" if profile in {"长袖", "long"} else "短袖"
    sleeve_word = "长袖" if resolved_profile == "长袖" else "短袖"

    raw_material = _sanitize_title_token(attributes.get("重要面料俗称", ""))
    if "棉" in raw_material and "纯棉" not in raw_material:
        material_word = "纯棉"
    elif raw_material and _pdd_char_len(raw_material) <= 8:
        material_word = raw_material
    else:
        material_word = "纯棉"

    raw_weight = attributes.get("重要平方克重", "")
    weight_match = re.search(r"(\d+)\s*g", raw_weight, flags=re.IGNORECASE)
    weight_word = f"{weight_match.group(1)}g" if weight_match else ""

    raw_season = _sanitize_title_token(attributes.get("重要上市时节", ""))
    season_short = raw_season.replace("年", "")
    if not season_short:
        season_short = "2026秋季" if resolved_profile == "长袖" else "2026夏季"
    year_season_new = season_short if "新款" in season_short else f"{season_short}新款"

    raw_fit = _sanitize_title_token(attributes.get("重要服装版型", "宽松"))
    if "宽松" in raw_fit:
        fit_word = "宽松"
    elif "修身" in raw_fit:
        fit_word = "修身"
    elif "紧身" in raw_fit:
        fit_word = "紧身"
    else:
        fit_word = raw_fit[:4] or "宽松"

    raw_collar = _sanitize_title_token(attributes.get("领型", "圆领")) or "圆领"
    collar_word = "圆领" if "圆领" in raw_collar and _pdd_char_len(raw_collar) > 6 else raw_collar

    raw_style = _sanitize_title_token(
        attributes.get("重要主风格") or attributes.get("风格") or "韩版"
    )
    if "韩" in raw_style:
        style_word = "韩版"
    elif raw_style and _pdd_char_len(raw_style) <= 6:
        style_word = raw_style
    else:
        style_word = "韩版"

    return {
        "profile": resolved_profile,
        "sleeve": sleeve_word,
        "material": material_word,
        "weight": weight_word,
        "season_short": season_short,
        "year_season_new": year_season_new,
        "fit": fit_word,
        "collar": collar_word,
        "style": style_word,
        "print_a": _extract_print_descriptor(facts, extra_keywords, fallback="创意印花"),
        "print_b": _extract_print_descriptor(facts, extra_keywords, fallback="趣味印花"),
    }


def _assemble_title_tokens(core_tokens: list[str], tail_tokens: list[str]) -> str:
    """按词组装标题：严格控制在 60 字符（30 汉字）内，不截断半个词，自动去重与防冲突。"""
    title = ""
    for raw in core_tokens:
        token = _sanitize_title_token(raw)
        if not token or _has_mutually_exclusive_conflict(token, title):
            continue
        if _pdd_char_len(title + token) <= MAX_TITLE_UNITS:
            title += token

    for raw in tail_tokens:
        token = _sanitize_title_token(raw)
        if not token:
            continue
        if _has_mutually_exclusive_conflict(token, title) or _has_root_overlap(token, title):
            continue
        if _pdd_char_len(title + token) <= MAX_TITLE_UNITS:
            title += token

    return title


def _generate_tshirt_titles(
    facts: dict[str, object],
    attributes: dict[str, str],
    profile: str,
    formula: Literal["a", "b", "all"] = "all",
    extra_keywords: list[str] | None = None,
    config_file: Path | None = None,
) -> list[dict[str, object]]:
    """按拼多多女装 T 恤高权重公式 + 主题热搜词库生成差异化合规标题（<= 30 汉字 / 60 字符）。"""
    slots = _extract_title_slots(facts, attributes, profile, extra_keywords)

    hot_cfg = _load_title_hot_keywords(config_file)
    theme = _infer_title_theme(facts, extra_keywords)
    themes_map = hot_cfg.get("themes") if isinstance(hot_cfg.get("themes"), dict) else {}
    theme_entry = themes_map.get(theme) or themes_map.get("general") or {}
    profile_entry = hot_cfg.get(slots["profile"]) if isinstance(hot_cfg.get(slots["profile"]), dict) else {}

    style_pool = [str(x) for x in (theme_entry.get("style") or [slots["style"]])]
    sell_pool = [str(x) for x in (theme_entry.get("selling_points") or [])]
    tail_pool = [str(x) for x in (profile_entry.get("tail") or [])]

    logo_seed_str = str(facts.get("logo") or facts.get("product_name") or slots["print_a"])
    seed = zlib.crc32(logo_seed_str.encode("utf-8"))

    style_a = _rotate_list(style_pool, seed, offset=0)
    sell_a = _rotate_list(sell_pool, seed, offset=0)
    tail_a_hot = _rotate_list(tail_pool, seed, offset=0)

    style_b = _rotate_list(style_pool, seed, offset=1)
    sell_b = _rotate_list(sell_pool, seed, offset=1)
    tail_b_hot = _rotate_list(tail_pool, seed, offset=1)

    extra_clean = [_sanitize_title_token(k) for k in (extra_keywords or []) if _sanitize_title_token(k)]

    # 公式 A：高权重核心前置公式
    # [核心材质] + [袖长+核心品类+人群] + [年份季节] + [版型+领型] + [设计/印花元素] + [热搜风格+热搜卖点+长尾衍生词]
    core_a = [
        slots["material"],
        f"{slots['sleeve']}T恤女",
        slots["year_season_new"],
        f"{slots['fit']}{slots['collar']}",
        slots["print_a"],
    ]
    tail_a = [*extra_clean, *style_a[:1], *sell_a[:1], *tail_a_hot, *style_a[1:], *sell_a[1:]]
    title_a = _assemble_title_tokens(core_a, tail_a)

    # 公式 B：新品热搜长尾引流公式（风格热词前置抢占细分搜索流量）
    # [热搜风格+版型] + [袖长+核心品类+人群] + [季节] + [材质/克重卖点] + [领型+印花] + [热搜卖点+场景长尾词]
    material_weight = f"{slots['material']}{slots['weight']}" if slots["weight"] else slots["material"]
    lead_style_b = style_b[0] if style_b else slots["style"]
    core_b = [
        f"{lead_style_b}{slots['fit']}",
        f"{slots['sleeve']}T恤女",
        slots["season_short"],
        material_weight,
        f"{slots['collar']}{slots['print_b']}",
    ]
    tail_b = [*extra_clean, *sell_b[:1], *tail_b_hot, *style_b[1:], *sell_b[1:]]
    title_b = _assemble_title_tokens(core_b, tail_b)

    specs: list[tuple[str, str, str]] = []
    if formula in {"a", "all"}:
        specs.append(("A", "高权重核心前置公式", title_a))
    if formula in {"b", "all"}:
        specs.append(("B", "热搜风格长尾引流公式", title_b))

    results: list[dict[str, object]] = []
    for code, name, title in specs:
        char_len = _pdd_char_len(title)
        hits = [w for w in PROHIBITED_WORDS if w in title]
        results.append(
            {
                "formula": code,
                "formula_name": name,
                "theme": theme,
                "title": title,
                "char_len": char_len,
                "hanzi_approx": round(char_len / 2, 1),
                "valid": bool(title) and char_len <= MAX_TITLE_UNITS and not hits,
            }
        )
    return results


def cmd_generate_title(args: argparse.Namespace) -> int:
    facts: dict[str, object] = {}
    product_name = ""
    if args.target:
        target = Path(args.target).resolve()
        if target.exists():
            facts = _load_workspace_facts(target)
            product_name = str(facts.get("product_name") or target.name)

    custom_cfg = Path(args.config_file).resolve() if args.config_file else None
    custom_attrs = Path(args.attributes_file).resolve() if args.attributes_file else custom_cfg
    resolved_profile = _normalize_profile_name(args.profile, product_name, facts)
    attrs = _infer_attributes(facts, product_name, "女装/T恤", custom_attrs, resolved_profile)

    candidates = _generate_tshirt_titles(
        facts,
        attrs,
        resolved_profile,
        formula=args.formula,
        extra_keywords=args.keywords,
        config_file=custom_cfg,
    )
    if args.json:
        print(
            json.dumps(
                {"profile": resolved_profile, "candidates": candidates},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    print(f"类目模板: 女装/T恤 ({resolved_profile})")
    for item in candidates:
        status = "PASS" if item["valid"] else "FAIL"
        print(
            f"[公式 {item['formula']} · {item['formula_name']}] {item['title']}\n"
            f"  长度: {item['char_len']}/60（约 {item['hanzi_approx']} 汉字） | 状态: {status}"
        )
    return 0


def cmd_check_title(args: argparse.Namespace) -> int:
    title = args.title.strip()
    char_len = _pdd_char_len(title)
    hits = [w for w in PROHIBITED_WORDS if w in title]

    ok = char_len <= 60 and not hits and len(title) > 0
    print(f"标题: {title}")
    print(f"字符长度: {char_len}/60（约 {char_len / 2:.1f} 个汉字，上限 30 汉字）")
    if char_len > 60:
        print("问题: 标题超出拼多多 60 字符（30 汉字）上限！")
    if hits:
        print(f"问题: 命中常见违禁/极限词: {', '.join(hits)}")
    if ok:
        print("结论: PASS — 长度与违禁词检查通过")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdd_prepare",
        description="拼多多（PDD）商品素材合规检测、尺寸适配与标题检查工具",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="检查目录或工作区图片是否符合拼多多规范")
    p_check.add_argument("target", help="AionForge 商品目录（如 output/<logo>）或图片文件夹")
    p_check.add_argument("--json", action="store_true", help="以 JSON 格式输出检测结果")
    p_check.set_defaults(func=cmd_check)

    p_prep = sub.add_parser("prepare", help="将图片批量适配并导出为拼多多上架目录")
    p_prep.add_argument("target", help="AionForge 商品目录（如 output/<logo>）或图片文件夹")
    p_prep.add_argument("--out", help="输出目录（默认为 <target>/pdd_ready）")
    p_prep.add_argument("--main-size", type=int, default=800, help="主图/白底/SKU 边长（默认 800）")
    p_prep.add_argument("--detail-width", type=int, default=750, help="详情图统一宽度（默认 750）")
    p_prep.add_argument(
        "--max-detail-height", type=int, default=1500, help="详情图单张最大高度（默认 1500）"
    )
    p_prep.add_argument(
        "--fit",
        choices=["cover", "contain"],
        default="cover",
        help="主图 1:1 适配方式：cover 居中裁切铺满（默认），contain 白底留白",
    )
    p_prep.add_argument(
        "--format",
        choices=["jpg", "png"],
        default="jpg",
        help="导出图片格式（默认 jpg，加载快且体积小）",
    )
    p_prep.add_argument(
        "--config-file",
        help="统一自定义配置 JSON 文件路径（同时覆盖属性、尺码/运费模板与价格，默认 references/default-config.json）",
    )
    p_prep.add_argument(
        "--attributes-file",
        help="自定义商品属性 JSON 文件路径（覆盖 default-config.json 中的属性）",
    )
    p_prep.add_argument(
        "--templates-file",
        help="自定义尺码模板/运费模板 JSON 文件路径（覆盖 default-config.json 中的模板）",
    )
    p_prep.add_argument(
        "--pricing-file",
        help="自定义拼单价/单买价/库存 JSON 文件路径（覆盖 default-config.json 中的价格）",
    )
    p_prep.add_argument(
        "--profile",
        choices=["短袖", "长袖", "short", "long"],
        help="选择默认属性模板（短袖 / 长袖）；未指定时自动从商品名与 facts.json 识别",
    )
    p_prep.set_defaults(func=cmd_prepare)

    p_title = sub.add_parser("check-title", help="检查拼多多商品标题字数与违禁词")
    p_title.add_argument("title", help="待检测的商品标题")
    p_title.set_defaults(func=cmd_check_title)

    p_gen_title = sub.add_parser("generate-title", help="按拼多多女装 T 恤高权重公式生成合规标题")
    p_gen_title.add_argument(
        "target", nargs="?", help="可选：AionForge 商品目录（如 output/<logo>），用于提取印花与版型事实"
    )
    p_gen_title.add_argument(
        "--profile",
        choices=["短袖", "长袖", "short", "long"],
        help="选择袖长模板（短袖 / 长袖）；未指定时自动从商品名与 facts.json 识别",
    )
    p_gen_title.add_argument(
        "--formula",
        choices=["a", "b", "all"],
        default="all",
        help="标题公式：a=高权重核心前置，b=新品长尾引流，all=同时输出（默认）",
    )
    p_gen_title.add_argument(
        "--keywords",
        nargs="*",
        default=[],
        help="补充具体印花主题或卖点词（如：小雏菊 复古）",
    )
    p_gen_title.add_argument("--config-file", help="自定义配置 JSON 路径")
    p_gen_title.add_argument("--attributes-file", help="自定义属性 JSON 路径")
    p_gen_title.add_argument("--json", action="store_true", help="以 JSON 格式输出候选标题")
    p_gen_title.set_defaults(func=cmd_generate_title)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
