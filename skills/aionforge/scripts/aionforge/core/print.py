"""印花体检与配色适配：纯 Pillow，不调用图片模型。

- ``measure_print``：给出一张印花的客观指标（比例、色数、细节密度、笔画宽度）。
- ``adapt_print``：按成衣底色重映射印花颜色，保持 alpha、几何和文字形状不变。
"""

from __future__ import annotations

import colorsys
import re
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from aionforge.core.composite import _dark_ink_to_white
from aionforge.core.images import _background_mask, _estimate_background
from aionforge.core.placement import mean_luminance, placement_box

_HEX_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")
_STRATEGIES = {
    "auto",
    "multiply",
    "normal",
    "white",
    "lighten",
    "darken",
    "palette",
    "outline",
}


@dataclass(frozen=True)
class PaletteEntry:
    hex: str
    share: float
    rgb: tuple[int, int, int]


@dataclass(frozen=True)
class PrintMetrics:
    source: str
    has_alpha: bool
    background_estimated: bool
    size: tuple[int, int]
    bbox: tuple[int, int, int, int]
    aspect: float
    coverage: float
    palette: list[PaletteEntry]
    edge_density: float
    mean_stroke_px: float
    mean_stroke_ratio: float
    transparent_holes: int
    touches_edge: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "has_alpha": self.has_alpha,
            "background_estimated": self.background_estimated,
            "size": list(self.size),
            "bbox": list(self.bbox),
            "aspect": round(self.aspect, 4),
            "coverage": round(self.coverage, 4),
            "palette": [
                {"hex": item.hex, "share": item.share} for item in self.palette
            ],
            "edge_density": round(self.edge_density, 4),
            "mean_stroke_px": round(self.mean_stroke_px, 2),
            "mean_stroke_ratio": round(self.mean_stroke_ratio, 4),
            "transparent_holes": self.transparent_holes,
            "touches_edge": self.touches_edge,
        }


@dataclass(frozen=True)
class AdaptReport:
    image: Image.Image
    strategy: str
    contrast_before: float
    contrast_after: float
    color_map: list[dict[str, str]]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "contrast_before": round(self.contrast_before, 3),
            "contrast_after": round(self.contrast_after, 3),
            "map": self.color_map,
            "warnings": self.warnings,
            "size": list(self.image.size),
        }


def _to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _from_hex(value: str) -> tuple[int, int, int]:
    text = value.strip().lstrip("#")
    return tuple(int(text[index : index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]


def parse_palette(value: str | None) -> list[tuple[int, int, int]]:
    """把 `#RRGGBB,#RRGGBB` 解析成 RGB 列表。"""
    if not value:
        return []
    colors: list[tuple[int, int, int]] = []
    for part in value.split(","):
        item = part.strip()
        if not _HEX_RE.fullmatch(item):
            raise ValueError(f"--palette 需要逗号分隔的 6 位 Hex，收到：{item}")
        colors.append(_from_hex(item))
    return colors


def _foreground_alpha(
    image: Image.Image, *, threshold: int, tolerance: int
) -> tuple[Image.Image, bool]:
    """优先用自带 alpha；没有时在内存里估背景并做边缘 flood fill。"""
    rgba = image.convert("RGBA")
    if "A" in image.getbands():
        alpha = rgba.getchannel("A")
        low, _high = alpha.getextrema()
        if low < 255:
            return alpha, False

    background_color = _estimate_background(rgba, tolerance=tolerance)
    if background_color is not None:
        background = _background_mask(rgba, background_color, tolerance=tolerance)
        estimated = True
    else:
        background = rgba.convert("L").point(
            lambda value: 255 if value >= threshold else 0
        )
        estimated = False

    width, height = rgba.size
    fill = 128
    step = max(1, min(width, height) // 32)
    seeds = {(x, y) for x in range(0, width, step) for y in (0, height - 1)}
    seeds |= {(x, y) for y in range(0, height, step) for x in (0, width - 1)}
    for x, y in seeds:
        if background.getpixel((x, y)) == 255:
            ImageDraw.floodfill(background, (x, y), fill, thresh=0)
    return background.point(lambda value: 0 if value == fill else 255), estimated


def _palette_entries(
    rgba: Image.Image,
    *,
    max_colors: int,
    alpha_threshold: int = 8,
    sample: int = 256,
) -> list[PaletteEntry]:
    work = rgba.copy()
    work.thumbnail((sample, sample), Image.Resampling.LANCZOS)
    alpha = work.getchannel("A")
    rgb = work.convert("RGB")
    opaque = [
        pixel
        for pixel, value in zip(
            rgb.get_flattened_data(), alpha.get_flattened_data(), strict=True
        )
        if value > alpha_threshold
    ]
    if not opaque:
        return []
    # 只把不透明像素排成一行做量化，避免透明区填充色被算进调色板。
    strip = Image.new("RGB", (len(opaque), 1))
    strip.putdata(opaque)
    quantized = strip.quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT)
    counts = Counter(quantized.get_flattened_data())
    total = sum(counts.values())
    if not total:
        return []
    palette = quantized.getpalette() or []
    entries: list[PaletteEntry] = []
    for index, count in counts.most_common(max_colors):
        base = index * 3
        rgb_tuple = tuple(palette[base : base + 3])
        entries.append(
            PaletteEntry(
                hex=_to_hex(rgb_tuple),  # type: ignore[arg-type]
                share=round(count / total, 4),
                rgb=rgb_tuple,  # type: ignore[arg-type]
            )
        )
    return entries


def _transparent_holes(alpha: Image.Image, *, sample: int = 256) -> int:
    work = alpha.copy()
    work.thumbnail((sample, sample), Image.Resampling.NEAREST)
    width, height = work.size
    pixels = work.load()
    visited = bytearray(width * height)
    holes = 0
    for start_y in range(height):
        for start_x in range(width):
            start_index = start_y * width + start_x
            if visited[start_index] or pixels[start_x, start_y] > 8:
                continue
            visited[start_index] = 1
            queue: deque[tuple[int, int]] = deque([(start_x, start_y)])
            area = 0
            touches_border = False
            while queue:
                x, y = queue.popleft()
                area += 1
                if x == 0 or y == 0 or x == width - 1 or y == height - 1:
                    touches_border = True
                for next_y in range(max(0, y - 1), min(height, y + 2)):
                    for next_x in range(max(0, x - 1), min(width, x + 2)):
                        index = next_y * width + next_x
                        if visited[index] or pixels[next_x, next_y] > 8:
                            continue
                        visited[index] = 1
                        queue.append((next_x, next_y))
            if not touches_border and area >= 4:
                holes += 1
    return holes


def measure_print(
    path: Path,
    *,
    max_colors: int = 8,
    threshold: int = 238,
    tolerance: int = 18,
    alpha_threshold: int = 8,
) -> PrintMetrics:
    """读取一张原稿或透明印花，返回客观指标；不写文件。"""
    source = Path(path)
    if not source.is_file():
        raise ValueError(f"印花不存在：{source}")
    with Image.open(source) as opened:
        has_alpha = "A" in opened.getbands()
        rgba = opened.convert("RGBA")
    alpha, background_estimated = _foreground_alpha(
        rgba, threshold=threshold, tolerance=tolerance
    )
    bbox = alpha.getbbox()
    if bbox is None:
        raise ValueError(f"没有可见图案：{source}")

    left, top, right, bottom = bbox
    bbox_width = right - left
    bbox_height = bottom - top
    mask = alpha.point(lambda value: 255 if value > alpha_threshold else 0)
    alpha_pixels = mask.histogram()[255]
    if not alpha_pixels:
        raise ValueError(f"没有可见图案：{source}")

    eroded = mask.filter(ImageFilter.MinFilter(3))
    boundary_pixels = ImageChops.difference(mask, eroded).histogram()[255]
    edge_density = boundary_pixels / alpha_pixels
    mean_stroke_px = alpha_pixels / max(1, boundary_pixels)

    cropped = rgba.crop(bbox)
    palette = _palette_entries(
        cropped,
        max_colors=max_colors,
        alpha_threshold=alpha_threshold,
    )
    width, height = rgba.size
    return PrintMetrics(
        source=str(source),
        has_alpha=has_alpha,
        background_estimated=background_estimated,
        size=(width, height),
        bbox=(left, top, right, bottom),
        aspect=bbox_width / max(1, bbox_height),
        coverage=alpha_pixels / max(1, bbox_width * bbox_height),
        palette=palette,
        edge_density=edge_density,
        mean_stroke_px=mean_stroke_px,
        mean_stroke_ratio=mean_stroke_px / max(1, bbox_width),
        transparent_holes=_transparent_holes(cropped.getchannel("A")),
        touches_edge=left == 0 or top == 0 or right == width or bottom == height,
    )


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    def channel(value: int) -> float:
        normalized = value / 255
        if normalized <= 0.03928:
            return normalized / 12.92
        return ((normalized + 0.055) / 1.055) ** 2.4

    red, green, blue = (channel(value) for value in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(
    first: tuple[int, int, int], second: tuple[int, int, int]
) -> float:
    high, low = sorted(
        (_relative_luminance(first), _relative_luminance(second)), reverse=True
    )
    return (high + 0.05) / (low + 0.05)


def _min_contrast(
    palette: list[PaletteEntry], garment_rgb: tuple[int, int, int]
) -> float:
    relevant = [item for item in palette if item.share >= 0.1] or palette
    if not relevant:
        return 1.0
    return min(contrast_ratio(item.rgb, garment_rgb) for item in relevant)


def _garment_region(
    garment: Image.Image,
    print_size: tuple[int, int],
    *,
    x: float,
    y: float,
    width: float,
) -> Image.Image:
    left, top, box_width, box_height = placement_box(
        garment.size, print_size, x=x, y=y, width=width
    )
    left = min(max(0, left), max(0, garment.width - 1))
    top = min(max(0, top), max(0, garment.height - 1))
    right = min(garment.width, left + max(1, box_width))
    bottom = min(garment.height, top + max(1, box_height))
    return garment.crop((left, top, right, bottom))


def _mean_rgb(image: Image.Image) -> tuple[int, int, int]:
    rgb = image.convert("RGB")
    rgb.thumbnail((64, 64), Image.Resampling.BILINEAR)
    pixels = list(rgb.get_flattened_data())
    total = len(pixels)
    if not total:
        return (255, 255, 255)
    return tuple(
        round(sum(pixel[index] for pixel in pixels) / total) for index in range(3)
    )  # type: ignore[return-value]


def _transform_luminance(
    rgba: Image.Image, *, lighten: bool, strength: float
) -> Image.Image:
    hsv = rgba.convert("RGB").convert("HSV")
    hue, saturation, value = hsv.split()
    exponent = 1 / (1 + strength) if lighten else 1 + strength
    mapped = value.point(lambda item: round(255 * (item / 255) ** exponent))
    result = Image.merge("HSV", (hue, saturation, mapped)).convert("RGB").convert("RGBA")
    result.putalpha(rgba.getchannel("A"))
    return result


def _map_palette(
    rgba: Image.Image, colors: list[tuple[int, int, int]]
) -> Image.Image:
    flat = [channel for color in colors for channel in color]
    if not flat:
        raise ValueError("palette 策略需要至少一个目标色")
    palette_image = Image.new("P", (1, 1))
    repeats = (768 + len(flat) - 1) // len(flat)
    palette_image.putpalette((flat * repeats)[:768])
    quantized = rgba.convert("RGB").quantize(
        palette=palette_image, dither=Image.Dither.NONE
    )
    result = quantized.convert("RGB").convert("RGBA")
    result.putalpha(rgba.getchannel("A"))
    return result


def _add_outline(
    rgba: Image.Image, color: tuple[int, int, int], *, outline_px: int
) -> Image.Image:
    pad = max(1, int(outline_px))
    size = (rgba.width + pad * 2, rgba.height + pad * 2)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.paste(rgba, (pad, pad))
    dilated = canvas.getchannel("A").filter(ImageFilter.MaxFilter(pad * 2 + 1))
    outline = Image.new("RGBA", size, (*color, 255))
    outline.putalpha(dilated)
    return Image.alpha_composite(outline, canvas)


def _map_color(
    rgb: tuple[int, int, int],
    *,
    strategy: str,
    palette_target: list[tuple[int, int, int]],
    strength: float,
) -> tuple[int, int, int]:
    if strategy == "white":
        maximum = max(rgb)
        spread = maximum - min(rgb)
        return (255, 255, 255) if maximum < 100 and spread < 40 else rgb
    if strategy in {"lighten", "darken"}:
        hue, saturation, value = colorsys.rgb_to_hsv(*(item / 255 for item in rgb))
        exponent = 1 / (1 + strength) if strategy == "lighten" else 1 + strength
        mapped = value**exponent
        result = colorsys.hsv_to_rgb(hue, saturation, mapped)
        return tuple(round(item * 255) for item in result)  # type: ignore[return-value]
    if strategy == "palette" and palette_target:
        return min(
            palette_target,
            key=lambda item: sum(
                (item[index] - rgb[index]) ** 2 for index in range(3)
            ),
        )
    return rgb


def _choose_strategy(
    garment_luminance: float,
    palette: list[PaletteEntry],
    contrast: float,
) -> str:
    normalized = garment_luminance / 255
    dark_neutral_share = sum(
        item.share
        for item in palette
        if max(item.rgb) < 100 and max(item.rgb) - min(item.rgb) < 40
    )
    if normalized < 0.3:
        if dark_neutral_share >= 0.15:
            return "white"
        return "lighten" if contrast < 3 else "normal"
    if normalized > 0.7:
        return "darken" if contrast < 3 else "multiply"
    if contrast < 3:
        return "lighten" if normalized < 0.5 else "darken"
    return "multiply"


def adapt_print(
    print_path: Path,
    garment_path: Path,
    *,
    strategy: str = "auto",
    palette: list[tuple[int, int, int]] | None = None,
    x: float = 0.5,
    y: float = 0.38,
    width: float = 0.35,
    outline_px: int = 4,
    max_colors: int = 8,
) -> AdaptReport:
    """按成衣底色重映射印花颜色；除 outline 外加描边外，不改 alpha 与几何。"""
    if strategy not in _STRATEGIES:
        raise ValueError(f"strategy 必须是 {', '.join(sorted(_STRATEGIES))}")
    if strategy == "palette" and not palette:
        raise ValueError("palette 策略需要 --palette 目标色")
    for name, value in (("x", x), ("y", y), ("width", width)):
        if not 0 < value <= 1:
            raise ValueError(f"--{name} 必须在 (0, 1] 之间，收到：{value}")

    source = Path(print_path)
    garment_file = Path(garment_path)
    if not source.is_file():
        raise ValueError(f"印花不存在：{source}")
    if not garment_file.is_file():
        raise ValueError(f"成衣图不存在：{garment_file}")
    with Image.open(source) as opened:
        if "A" not in opened.getbands():
            raise ValueError("print adapt 需要透明印花，先运行 cutout")
        original = opened.convert("RGBA")
    with Image.open(garment_file) as opened:
        garment = opened.convert("RGB")

    region = _garment_region(garment, original.size, x=x, y=y, width=width)
    garment_rgb = _mean_rgb(region)
    garment_luminance = mean_luminance(region)
    palette_entries = _palette_entries(original, max_colors=max_colors)
    contrast_before = _min_contrast(palette_entries, garment_rgb)

    selected = strategy
    if selected == "auto":
        selected = _choose_strategy(garment_luminance, palette_entries, contrast_before)

    warnings: list[str] = []
    outline_color: tuple[int, int, int] | None = None
    if selected == "white":
        adapted = _dark_ink_to_white(original)
    elif selected == "lighten":
        adapted = _transform_luminance(original, lighten=True, strength=0.6)
    elif selected == "darken":
        adapted = _transform_luminance(original, lighten=False, strength=0.5)
    elif selected == "palette":
        adapted = _map_palette(original, palette or [])
    elif selected == "outline":
        outline_color = (255, 255, 255) if garment_luminance < 128 else (0, 0, 0)
        adapted = _add_outline(original, outline_color, outline_px=outline_px)
        warnings.append("outline 会在印花外加一圈描边，画布已自动留出边距")
    else:
        adapted = original.copy()

    adapted_entries = _palette_entries(adapted, max_colors=max_colors)
    if selected == "outline" and outline_color is not None:
        contrast_after = max(
            contrast_before, contrast_ratio(outline_color, garment_rgb)
        )
    else:
        contrast_after = _min_contrast(adapted_entries, garment_rgb)
    if contrast_after < 3:
        warnings.append("适配后对比度仍低于 3:1；考虑 outline 或换位置")

    color_map = [
        {
            "from": item.hex,
            "to": _to_hex(
                _map_color(
                    item.rgb,
                    strategy=selected,
                    palette_target=palette or [],
                    strength=0.6 if selected == "lighten" else 0.5,
                )
            ),
        }
        for item in palette_entries
        if item.share >= 0.05
    ]
    return AdaptReport(
        image=adapted,
        strategy=selected,
        contrast_before=contrast_before,
        contrast_after=contrast_after,
        color_map=color_map,
        warnings=warnings,
    )
