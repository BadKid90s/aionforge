"""落点与亮度计算：composite 与 print adapt 共用的纯几何/色彩工具。"""

from __future__ import annotations

from PIL import Image


def placement_box(
    canvas_size: tuple[int, int],
    subject_size: tuple[int, int],
    *,
    x: float = 0.5,
    y: float = 0.38,
    width: float = 0.35,
) -> tuple[int, int, int, int]:
    """把 0-1 的画布比例换算成 (left, top, width, height) 像素框。"""
    canvas_width, canvas_height = canvas_size
    subject_width, subject_height = subject_size
    target_width = max(1, round(canvas_width * width))
    target_height = max(
        1, round(target_width * subject_height / max(1, subject_width))
    )
    left = round(canvas_width * x - target_width / 2)
    top = round(canvas_height * y - target_height / 2)
    return left, top, target_width, target_height


def validate_box(box: tuple[int, int, int, int], canvas_size: tuple[int, int]) -> None:
    """确认落点完全在画布内；超出时抛 ValueError。"""
    left, top, width, height = box
    canvas_width, canvas_height = canvas_size
    if (
        left < 0
        or top < 0
        or left + width > canvas_width
        or top + height > canvas_height
    ):
        raise ValueError("印花超出画布：调小 --width 或调整 --x / --y")


def mean_luminance(image: Image.Image) -> float:
    """返回 0-255 的平均亮度。"""
    gray = image.convert("L")
    histogram = gray.histogram()
    total = sum(histogram)
    if not total:
        return 0.0
    return sum(value * count for value, count in enumerate(histogram)) / total
