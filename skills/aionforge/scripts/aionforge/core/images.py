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
    path: Path,
    *,
    threshold: int = 238,
    padding: int = 8,
    tolerance: int = 18,
    remove_enclosed_white: bool = False,
    denoise: int = 0,
) -> Path:
    """把与边缘相连的浅色背景变成透明，并按图案边界裁切。

    先采样四边估计背景色，能估计时按颜色距离抠图，适配米白、浅灰等非纯白稿；
    边缘太杂时退回亮度阈值。默认只有和边缘连通的背景会被去掉，图案内部的白色
    保留；`remove_enclosed_white=True` 时连封闭白区（字母孔洞、镂空）一起去掉。
    `denoise>0` 时删除面积小于该像素数的 alpha 孤岛。
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
    if remove_enclosed_white:
        alpha = background.point(lambda value: 0 if value == 255 else 255)
    else:
        fill = 128
        step = max(1, min(width, height) // 32)
        seeds = {(x, y) for x in range(0, width, step) for y in (0, height - 1)}
        seeds |= {(x, y) for y in range(0, height, step) for x in (0, width - 1)}
        for x, y in seeds:
            if background.getpixel((x, y)) == 255:
                ImageDraw.floodfill(background, (x, y), fill, thresh=0)
        alpha = background.point(lambda value: 0 if value == fill else 255)
    image.putalpha(alpha)
    if denoise > 0:
        image = remove_small_alpha_islands(image, min_pixels=denoise)
    bbox = image.getchannel("A").getbbox()
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


def _alpha_speck_mask(
    alpha: Image.Image, *, min_pixels: int
) -> tuple[Image.Image, int]:
    """找出 alpha 连通域中面积小于 min_pixels 的孤岛。

    返回 (掩码, 孤岛数量)：掩码 255 的位置是需要删除的小孤岛。
    """
    min_pixels = max(1, int(min_pixels))
    mask = alpha.point(lambda value: 255 if value > 0 else 0)
    if mask.getbbox() is None:
        return Image.new("L", mask.size, 0), 0
    width, height = mask.size
    pixels = mask.load()
    small = 128
    large = 127
    specks = 0
    for y in range(height):
        for x in range(width):
            if pixels[x, y] != 255:
                continue
            before = mask.histogram()[large]
            ImageDraw.floodfill(mask, (x, y), large, thresh=0)
            area = mask.histogram()[large] - before
            if area < min_pixels:
                ImageDraw.floodfill(mask, (x, y), small, thresh=0)
                specks += 1
    return mask.point(lambda value: 255 if value == small else 0), specks


def remove_small_alpha_islands(image: Image.Image, *, min_pixels: int) -> Image.Image:
    """删除 alpha 中面积过小的孤立碎点，保留正常图案。"""
    specks, _ = _alpha_speck_mask(image.getchannel("A"), min_pixels=min_pixels)
    if specks.getbbox() is None:
        return image
    cleaned = ImageChops.darker(
        image.getchannel("A"), specks.point(lambda value: 0 if value else 255)
    )
    result = image.copy()
    result.putalpha(cleaned)
    return result


def alpha_speck_count(image: Image.Image, *, min_pixels: int = 4) -> int:
    """统计 alpha 中小于 min_pixels 的孤立碎点数量。"""
    _, count = _alpha_speck_mask(image.getchannel("A"), min_pixels=min_pixels)
    return count


def alpha_border_white_ratio(
    image: Image.Image, *, threshold: int = 238, tolerance: int = 18
) -> float:
    """alpha 包围盒四边中，近白像素占不透明像素的比例。

    印花外围残留白边时这个比例会很高；白色字标也会触发，需要结合图案判断。
    """
    if "A" not in image.getbands():
        return 0.0
    rgba = image.convert("RGBA")
    bbox = rgba.getchannel("A").getbbox()
    if bbox is None:
        return 0.0
    cropped = rgba.crop(bbox)
    width, height = cropped.size
    pixels = cropped.load()
    coords = {(x, 0) for x in range(width)} | {(x, height - 1) for x in range(width)}
    coords |= {(0, y) for y in range(height)} | {(width - 1, y) for y in range(height)}
    total = 0
    near_white = 0
    for x, y in coords:
        red, green, blue, alpha_value = pixels[x, y]
        if alpha_value == 0:
            continue
        total += 1
        if (
            min(red, green, blue) >= threshold
            and max(red, green, blue) - min(red, green, blue) <= tolerance
        ):
            near_white += 1
    return near_white / total if total else 0.0


def _trim_alpha_white(
    image: Image.Image, *, threshold: int, tolerance: int, remove_enclosed_white: bool
) -> Image.Image | None:
    """清掉 alpha 包围盒边缘连通的白底 / 白边，保留图案内部的白色。

    原稿只要带透明通道，旧实现就直接按 alpha 裁切返回；但很多素材的 alpha
    只包住了整块画布，白底仍然留在 alpha 内，于是白边原样被带进商品图。
    这里以 alpha 包围盒四边为种子做 flood fill，只清除与外围连通的白像素；
    被深色描边包住的白色文字、高光和留白不会被误删。

    清完后如果没有任何可见内容（例如图案本身就是白色），返回 None，
    调用方保留原图，避免把白色 logo 整个抹掉。

    `remove_enclosed_white=True` 时不再只清外围，而是把所有近背景色像素
    （含字母孔洞、封闭白区）都清成透明；白色字标不要开。
    """
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        return None
    cropped = image.crop(bbox)
    background = _estimate_background(cropped, tolerance=tolerance)
    if background is not None and min(background) < 200:
        # 透明稿外围的 RGB 可能是任意值，不能把深色描边当成背景。
        background = None
    if background is not None:
        mask = _background_mask(cropped, background, tolerance=tolerance)
    else:
        mask = cropped.convert("L").point(
            lambda value: 255 if value >= threshold else 0
        )
    width, height = cropped.size
    if remove_enclosed_white:
        # 显式要求时，把所有接近背景色的像素都当背景，包括字母孔洞和封闭白区。
        removed = mask.point(lambda value: 0 if value == 255 else 255)
    else:
        seeds = (
            [(x, 0) for x in range(width)]
            + [(x, height - 1) for x in range(width)]
            + [(0, y) for y in range(height)]
            + [(width - 1, y) for y in range(height)]
        )
        fill = 128
        for seed in seeds:
            if mask.getpixel(seed) == 255:
                ImageDraw.floodfill(mask, seed, fill, thresh=0)
        filled = mask.histogram()[fill]
        if filled == 0:
            return None
        # 白底 / 白边通常同时贴住包围盒的多条边；白色字标往往只贴一条边。
        # 少于三条边、或面积过小的白色区域不当成背景，避免误删白色设计。
        edges = (
            any(mask.getpixel((x, 0)) == fill for x in range(width)),
            any(mask.getpixel((x, height - 1)) == fill for x in range(width)),
            any(mask.getpixel((0, y)) == fill for y in range(height)),
            any(mask.getpixel((width - 1, y)) == fill for y in range(height)),
        )
        if sum(edges) < 3 or filled < max(1, int(width * height * 0.002)):
            return None
        removed = mask.point(lambda value: 0 if value == fill else 255)
    cleaned_alpha = ImageChops.darker(cropped.getchannel("A"), removed)
    if cleaned_alpha.getbbox() is None:
        return None
    cropped.putalpha(cleaned_alpha)
    return cropped


def prepare_logo(
    source: Path,
    dest: Path,
    *,
    padding: int = 8,
    threshold: int = 238,
    tolerance: int = 18,
    remove_enclosed_white: bool = False,
    denoise: int = 0,
) -> Path:
    """平面 logo 稿本地预处理：裁到图案主体并输出透明底。

    平面稿不需要经过图片模型重画，直接本地处理能保证文字和形状不被改。
    原稿自带 alpha 时也会清理与透明区域外围连通的白底 / 白边；图案内部的
    白色（白色文字、高光、留白）不受影响。
    `remove_enclosed_white=True` 会把封闭白区（字母孔洞、镂空）也清成透明；
    `denoise>0` 会删除面积小于该像素数的 alpha 孤岛。
    """
    if dest.suffix.lower() not in _ALPHA_SUFFIXES:
        raise ValueError("图案输出需要 .png 或 .webp")
    padding = max(padding, 0)
    threshold = min(max(int(threshold), 0), 255)
    tolerance = min(max(int(tolerance), 0), 255)
    denoise = max(int(denoise), 0)
    with Image.open(source) as img:
        image = img.convert("RGBA")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if image.getchannel("A").getextrema()[0] < 255:
        cleaned = _trim_alpha_white(
            image,
            threshold=threshold,
            tolerance=tolerance,
            remove_enclosed_white=remove_enclosed_white,
        )
        if cleaned is not None:
            image = cleaned
        if denoise > 0:
            image = remove_small_alpha_islands(image, min_pixels=denoise)
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
    return cutout_background(
        dest,
        padding=padding,
        threshold=threshold,
        tolerance=tolerance,
        remove_enclosed_white=remove_enclosed_white,
        denoise=denoise,
    )
