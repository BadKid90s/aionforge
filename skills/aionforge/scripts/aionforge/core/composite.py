"""本地印花合成：把透明印花贴到成衣图上，不经过图片模型重绘。

支持三种墨色策略：
- multiply：正片叠底，适合浅色衣，保留布料明暗；
- normal：直接 alpha 合成，适合白墨或彩色印花；
- white：白墨打底 + 深色笔画转白，适合深色衣。
`auto` 按印花区域的成衣亮度自动选择。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops

from aionforge.core.placement import mean_luminance, placement_box, validate_box

_INK_MODES = {"auto", "multiply", "normal", "white"}


@dataclass(frozen=True)
class CompositeResult:
    image: Image.Image
    ink: str


def _dark_ink_to_white(print_rgba: Image.Image) -> Image.Image:
    """深色衣上把中性深色笔画转成白色，彩色元素保持原色。"""
    rgb = print_rgba.convert("RGB")
    pixels = rgb.load()
    for y in range(rgb.height):
        for x in range(rgb.width):
            red, green, blue = pixels[x, y]
            if max(red, green, blue) < 100 and max(red, green, blue) - min(red, green, blue) < 40:
                pixels[x, y] = (255, 255, 255)
    result = rgb.convert("RGBA")
    result.putalpha(print_rgba.getchannel("A"))
    return result


def composite_print(
    garment_path: Path,
    print_path: Path,
    *,
    x: float = 0.5,
    y: float = 0.38,
    width: float = 0.35,
    ink: str = "auto",
    shading: float = 0.25,
) -> CompositeResult:
    """把印花合成到成衣图上，返回合成结果与实际使用的墨色策略。"""
    if ink not in _INK_MODES:
        raise ValueError(f"--ink 必须是 {', '.join(sorted(_INK_MODES))}，收到：{ink}")
    for name, value in (("x", x), ("y", y), ("width", width)):
        if not 0 < value <= 1:
            raise ValueError(f"--{name} 必须在 (0, 1] 之间，收到：{value}")
    if not 0 <= shading <= 1:
        raise ValueError(f"--shading 必须在 0-1 之间，收到：{shading}")

    with Image.open(garment_path) as source:
        garment = source.convert("RGB")
    with Image.open(print_path) as source:
        print_rgba = source.convert("RGBA")

    left, top, target_width, target_height = placement_box(
        garment.size, print_rgba.size, x=x, y=y, width=width
    )
    validate_box((left, top, target_width, target_height), garment.size)
    resized = print_rgba.resize(
        (target_width, target_height), Image.Resampling.LANCZOS
    )

    alpha = resized.getchannel("A")
    region = garment.crop((left, top, left + target_width, top + target_height))
    mean = mean_luminance(region)
    mode = ink if ink != "auto" else ("white" if mean < 100 else "multiply")

    if mode == "multiply":
        white = Image.new("RGBA", resized.size, (255, 255, 255, 255))
        white.alpha_composite(resized)
        multiplied = ImageChops.multiply(region, white.convert("RGB"))
        blended = Image.composite(multiplied, region, alpha)
    elif mode == "white":
        underbase = Image.new("RGB", resized.size, (255, 255, 255))
        under = Image.composite(underbase, region, alpha)
        blended = Image.composite(_dark_ink_to_white(resized).convert("RGB"), under, alpha)
    else:
        blended = Image.composite(resized.convert("RGB"), region, alpha)

    if shading > 0 and mode != "multiply":
        luminance = region.convert("L")
        factor = luminance.point(
            lambda value: round(255 * (1 - shading) + value * shading)
        )
        shaded = ImageChops.multiply(blended, factor.convert("RGB"))
        blended = Image.composite(shaded, blended, alpha)

    garment.paste(blended, (left, top))
    return CompositeResult(image=garment, ink=mode)
