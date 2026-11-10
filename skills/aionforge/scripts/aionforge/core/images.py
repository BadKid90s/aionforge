from __future__ import annotations

import math
import re
from enum import StrEnum
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageOps

MIN_SIDE = 480
BASE_LONG_SIDE = 1024
_RATIO = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*[:/xX]\s*(\d+(?:\.\d+)?)\s*$")
_ALPHA_SUFFIXES = {".png", ".webp"}


class FitMode(StrEnum):
    crop = "crop"
    pad = "pad"
    expand = "expand"


def flatten_to_rgb(image: Image.Image, background: str = "white") -> Image.Image:
    """把带透明通道的图铺到背景色上再转 RGB。

    直接 convert("RGB") 会丢掉 alpha，透明区域保留为黑色，白底商品图会变成黑底。
    """
    if "A" not in image.getbands():
        return image.convert("RGB")
    rgba = image.convert("RGBA")
    canvas = Image.new("RGBA", rgba.size, background)
    return Image.alpha_composite(canvas, rgba).convert("RGB")


def parse_ratio(value: str) -> tuple[float, float]:
    match = _RATIO.match(value)
    if match is None:
        raise ValueError("比例格式应为 W:H，例如 3:4")
    width = float(match.group(1))
    height = float(match.group(2))
    if width <= 0 or height <= 0:
        raise ValueError("比例必须大于 0")
    return width, height


def _even_ceil(value: float) -> int:
    return math.ceil(value / 2) * 2


def target_size(ratio: str) -> tuple[int, int]:
    width, height = parse_ratio(ratio)
    long_ratio = max(width, height)
    short_ratio = min(width, height)
    long_side = _even_ceil(max(BASE_LONG_SIDE, MIN_SIDE * long_ratio / short_ratio + 1))
    short_side = _even_ceil(long_side * short_ratio / long_ratio)
    if width >= height:
        return long_side, short_side
    return short_side, long_side


def aspect_close(
    size: tuple[int, int], target: tuple[int, int], *, tolerance: float = 0.02
) -> bool:
    width, height = size
    tw, th = target
    if width <= 0 or height <= 0 or tw <= 0 or th <= 0:
        return False
    return abs(width / height - tw / th) <= tolerance


def needs_expand(path: Path, ratio: str, *, tolerance: float = 0.02) -> bool:
    """参考图或成片比例对不上目标时需要扩图，不能留白边。"""
    with Image.open(path) as source:
        return not aspect_close(source.size, target_size(ratio), tolerance=tolerance)


def prepare_expand_canvas(source: Path, dest: Path, size: tuple[int, int]) -> Path:
    """把原图完整放入目标画布，缺口用边缘像素拉满，不留空白。"""
    with Image.open(source) as image:
        content = ImageOps.contain(flatten_to_rgb(image), size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size)
    offset_x = (size[0] - content.width) // 2
    offset_y = (size[1] - content.height) // 2
    if offset_x > 0:
        left = content.crop((0, 0, 1, content.height)).resize((offset_x, content.height))
        right_w = size[0] - offset_x - content.width
        right = content.crop((content.width - 1, 0, content.width, content.height)).resize(
            (max(right_w, 1), content.height)
        )
        canvas.paste(left, (0, offset_y))
        canvas.paste(right, (offset_x + content.width, offset_y))
    if offset_y > 0:
        top = content.crop((0, 0, content.width, 1)).resize((content.width, offset_y))
        bottom_h = size[1] - offset_y - content.height
        bottom = content.crop((0, content.height - 1, content.width, content.height)).resize(
            (content.width, max(bottom_h, 1))
        )
        canvas.paste(top, (offset_x, 0))
        canvas.paste(bottom, (offset_x, offset_y + content.height))
    canvas.paste(content, (offset_x, offset_y))
    dest.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dest, format="PNG")
    return dest


def fit_image(
    path: Path,
    size: tuple[int, int],
    fit: FitMode | str = FitMode.crop,
    *,
    background: str = "white",
) -> Path:
    mode = FitMode(fit) if not isinstance(fit, FitMode) else fit
    with Image.open(path) as source:
        if source.size == size:
            return path
        image = flatten_to_rgb(source, background)
    if mode is FitMode.expand:
        prepare_expand_canvas(path, path, size)
        return path
    if mode is FitMode.pad:
        result = ImageOps.pad(image, size, method=Image.Resampling.LANCZOS, color="white")
    else:
        result = ImageOps.fit(image, size, method=Image.Resampling.LANCZOS)
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        result.save(path, format="JPEG", quality=95)
    else:
        result.save(path, format="PNG")
    return path


def _estimate_background(
    image: Image.Image, *, tolerance: int = 18
) -> tuple[int, int, int] | None:
    """从四边采样背景色；边缘不够均匀时返回 None，退回亮度阈值。"""
    rgb = image.convert("RGB")
    width, height = rgb.size
    step = max(1, min(width, height) // 64)
    samples: list[tuple[int, int, int]] = []
    for x in range(0, width, step):
        samples.append(rgb.getpixel((x, 0)))
        samples.append(rgb.getpixel((x, height - 1)))
    for y in range(0, height, step):
        samples.append(rgb.getpixel((0, y)))
        samples.append(rgb.getpixel((width - 1, y)))
    if not samples:
        return None
    channels = list(zip(*samples))
    background = tuple(sorted(channel)[len(channel) // 2] for channel in channels)
    distances = sorted(
        max(abs(pixel[index] - background[index]) for index in range(3))
        for pixel in samples
    )
    if distances[int(len(distances) * 0.9)] > tolerance * 2:
        return None
    return background


def _background_mask(
    image: Image.Image, background: tuple[int, int, int], *, tolerance: int
) -> Image.Image:
    """按与背景色的通道最大差生成候选背景掩码；真正的边缘 flood fill 在后面做。"""
    rgb = image.convert("RGB")
    diff = ImageChops.difference(rgb, Image.new("RGB", rgb.size, background))
    red, green, blue = diff.split()
    max_diff = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    return max_diff.point(lambda value: 255 if value <= tolerance else 0)


def cutout_background(
    path: Path, *, threshold: int = 238, padding: int = 8, tolerance: int = 18
) -> Path:
    """把与边缘相连的浅色背景变成透明，并按图案边界裁切。

    先采样四边估计背景色，能估计时按颜色距离抠图，适配米白、浅灰等非纯白稿；
    边缘太杂时退回亮度阈值。只有和边缘连通的背景会被去掉，图案内部的白色保留。
    """
    if path.suffix.lower() not in _ALPHA_SUFFIXES:
        raise ValueError("透明背景需要 .png 或 .webp 输出")
    threshold = min(max(threshold, 0), 255)
    padding = max(padding, 0)
    tolerance = min(max(tolerance, 0), 255)
    with Image.open(path) as source:
        image = source.convert("RGBA")
    width, height = image.size
    background_color = _estimate_background(image, tolerance=tolerance)
    if background_color is not None:
        background = _background_mask(image, background_color, tolerance=tolerance)
    else:
        background = image.convert("L").point(lambda value: 255 if value >= threshold else 0)
    fill = 128
    step = max(1, min(width, height) // 32)
    seeds = {(x, y) for x in range(0, width, step) for y in (0, height - 1)}
    seeds |= {(x, y) for y in range(0, height, step) for x in (0, width - 1)}
    for x, y in seeds:
        if background.getpixel((x, y)) == 255:
            ImageDraw.floodfill(background, (x, y), fill, thresh=0)
    alpha = background.point(lambda value: 0 if value == fill else 255)
    image.putalpha(alpha)
    bbox = alpha.getbbox()
    if bbox is None:
        raise ValueError("提取结果没有可见图案")
    cropped = image.crop(bbox)
    result = Image.new(
        "RGBA",
        (cropped.width + padding * 2, cropped.height + padding * 2),
        (0, 0, 0, 0),
    )
    result.paste(cropped, (padding, padding))
    if path.suffix.lower() == ".webp":
        result.save(path, format="WEBP", lossless=True)
    else:
        result.save(path, format="PNG")
    return path


def prepare_logo(source: Path, dest: Path, *, padding: int = 8) -> Path:
    """平面 logo 稿本地预处理：已有 alpha 就裁到图案边界，否则按背景色抠图。

    平面稿不需要经过图片模型重画，直接本地处理能保证文字和形状不被改。
    """
    if dest.suffix.lower() not in _ALPHA_SUFFIXES:
        raise ValueError("图案输出需要 .png 或 .webp")
    padding = max(padding, 0)
    with Image.open(source) as img:
        image = img.convert("RGBA")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if image.getchannel("A").getextrema()[0] < 255:
        bbox = image.getchannel("A").getbbox()
        if bbox is None:
            raise ValueError("图案没有可见内容")
        cropped = image.crop(bbox)
        result = Image.new(
            "RGBA",
            (cropped.width + padding * 2, cropped.height + padding * 2),
            (0, 0, 0, 0),
        )
        result.paste(cropped, (padding, padding))
        if dest.suffix.lower() == ".webp":
            result.save(dest, format="WEBP", lossless=True)
        else:
            result.save(dest, format="PNG")
        return dest
    if dest.suffix.lower() == ".webp":
        image.save(dest, format="WEBP", lossless=True)
    else:
        image.save(dest, format="PNG")
    return cutout_background(dest, padding=padding)
