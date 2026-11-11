"""把透明底印花拆成独立元素，并标记触边情况。

元素按 alpha 的 8 邻接连通域拆分：文字、图形、装饰各自成为独立 PNG。
连通域贴到源图边缘时，说明元素可能被裁断，需要在 catalog 里标出来。
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops


@dataclass(frozen=True)
class AlphaElement:
    index: int
    bbox: tuple[int, int, int, int]
    area: int
    touches_edge: bool
    image: Image.Image


def _components(
    alpha: Image.Image, *, min_pixels: int
) -> list[list[tuple[int, int]]]:
    width, height = alpha.size
    pixels = alpha.load()
    visited = bytearray(width * height)
    result: list[list[tuple[int, int]]] = []
    for start_y in range(height):
        for start_x in range(width):
            start_index = start_y * width + start_x
            if visited[start_index] or pixels[start_x, start_y] == 0:
                continue
            visited[start_index] = 1
            queue: deque[tuple[int, int]] = deque([(start_x, start_y)])
            component: list[tuple[int, int]] = []
            while queue:
                x, y = queue.popleft()
                component.append((x, y))
                for next_y in range(max(0, y - 1), min(height, y + 2)):
                    row = next_y * width
                    for next_x in range(max(0, x - 1), min(width, x + 2)):
                        index = row + next_x
                        if visited[index] or pixels[next_x, next_y] == 0:
                            continue
                        visited[index] = 1
                        queue.append((next_x, next_y))
            if len(component) >= min_pixels:
                result.append(component)
    return result


def _element_image(
    image: Image.Image,
    component: list[tuple[int, int]],
    *,
    padding: int,
) -> tuple[Image.Image, tuple[int, int, int, int]]:
    xs = [point[0] for point in component]
    ys = [point[1] for point in component]
    left, top = min(xs), min(ys)
    right, bottom = max(xs) + 1, max(ys) + 1
    mask = Image.new("L", (right - left, bottom - top), 0)
    mask_pixels = mask.load()
    for x, y in component:
        mask_pixels[x - left, y - top] = 255
    cropped = image.crop((left, top, right, bottom))
    cropped.putalpha(ImageChops.darker(cropped.getchannel("A"), mask))
    padded = Image.new(
        "RGBA",
        (cropped.width + padding * 2, cropped.height + padding * 2),
        (0, 0, 0, 0),
    )
    padded.paste(cropped, (padding, padding))
    return padded, (left, top, right, bottom)


def extract_alpha_elements(
    image: Image.Image,
    *,
    min_pixels: int = 16,
    padding: int = 4,
) -> list[AlphaElement]:
    """按 alpha 连通域拆分元素；面积小于 min_pixels 的噪点忽略。"""
    if "A" not in image.getbands():
        raise ValueError("元素提取需要透明底印花，先用 forge cutout 去底")
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    width, height = rgba.size
    min_pixels = max(1, int(min_pixels))
    padding = max(0, int(padding))
    elements: list[AlphaElement] = []
    for component in _components(alpha, min_pixels=min_pixels):
        padded, bbox = _element_image(rgba, component, padding=padding)
        left, top, right, bottom = bbox
        touches_edge = left == 0 or top == 0 or right == width or bottom == height
        elements.append(
            AlphaElement(
                index=len(elements) + 1,
                bbox=bbox,
                area=len(component),
                touches_edge=touches_edge,
                image=padded,
            )
        )
    return elements


def element_catalog(
    source: Path, elements: list[AlphaElement], *, paths: list[Path]
) -> dict[str, Any]:
    return {
        "source": str(source),
        "elements": [
            {
                "index": element.index,
                "path": str(path),
                "bbox": list(element.bbox),
                "area": element.area,
                "touches_edge": element.touches_edge,
            }
            for element, path in zip(elements, paths, strict=True)
        ],
    }
