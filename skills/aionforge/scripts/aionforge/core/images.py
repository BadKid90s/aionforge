from __future__ import annotations

import math
import re
from enum import StrEnum
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

MIN_SIDE = 480
BASE_LONG_SIDE = 1024
_RATIO = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*[:/xX]\s*(\d+(?:\.\d+)?)\s*$")
_ALPHA_SUFFIXES = {".png", ".webp"}


class FitMode(StrEnum):
    crop = "crop"
    pad = "pad"
    expand = "expand"


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
        content = ImageOps.contain(image.convert("RGB"), size, Image.Resampling.LANCZOS)
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
    path: Path, size: tuple[int, int], fit: FitMode | str = FitMode.crop
) -> Path:
    mode = FitMode(fit) if not isinstance(fit, FitMode) else fit
    with Image.open(path) as source:
        if source.size == size:
            return path
        image = source.convert("RGB")
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


def cutout_background(path: Path, *, threshold: int = 238, padding: int = 8) -> Path:
    """把与边缘相连的浅色背景变成透明，并按图案边界裁切。"""
    if path.suffix.lower() not in _ALPHA_SUFFIXES:
        raise ValueError("透明背景需要 .png 或 .webp 输出")
    threshold = min(max(threshold, 0), 255)
    padding = max(padding, 0)
    with Image.open(path) as source:
        image = source.convert("RGBA")
    width, height = image.size
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
