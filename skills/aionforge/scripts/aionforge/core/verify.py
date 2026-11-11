"""成品图的确定性校验：尺寸、比例、白底、透明通道。

审美、商品事实和五官一致性由宿主 Agent 看图判断，这里只做脚本能可靠判断的部分。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from aionforge.core.images import (
    MIN_SIDE,
    alpha_border_white_ratio,
    alpha_speck_count,
    aspect_close,
    flatten_to_rgb,
    target_size,
)


def _white_border_ratio(
    image: Image.Image,
    *,
    threshold: int = 250,
    max_channel_delta: int = 6,
) -> float:
    """采样四边 2% 宽度，返回接近纯白的像素占比。"""
    rgb = flatten_to_rgb(image)
    width, height = rgb.size
    band = max(2, min(width, height) // 50)
    strips = (
        rgb.crop((0, 0, width, band)),
        rgb.crop((0, height - band, width, height)),
        rgb.crop((0, 0, band, height)),
        rgb.crop((width - band, 0, width, height)),
    )
    total = 0
    near_white = 0
    for strip in strips:
        pixels = strip.load()
        for y in range(strip.height):
            for x in range(strip.width):
                red, green, blue = pixels[x, y]
                total += 1
                if (
                    red >= threshold
                    and green >= threshold
                    and blue >= threshold
                    and max(red, green, blue) - min(red, green, blue) <= max_channel_delta
                ):
                    near_white += 1
    return near_white / total if total else 0.0


def verify_image(
    path: Path,
    *,
    ratio: str | None = None,
    white_bg: bool = False,
    alpha: bool = False,
    print_quality: bool = False,
    min_side: int = MIN_SIDE,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str = "", suggestion: str = "") -> None:
        checks.append(
            {"name": name, "pass": passed, "detail": detail, "suggestion": suggestion}
        )

    image_path = Path(path).expanduser()
    if not image_path.is_file():
        check("file", False, str(image_path), "检查输出路径或先重新出图")
        return checks
    check("file", True, str(image_path))

    try:
        with Image.open(image_path) as image:
            image.load()
            width, height = image.size
            check(
                "size",
                width >= min_side and height >= min_side,
                f"{width}x{height}",
                f"宽高都要 >= {min_side}px",
            )
            if ratio:
                try:
                    target = target_size(ratio)
                except ValueError as exc:
                    check("ratio", False, str(exc), "比例格式用 W:H，例如 1:1 / 3:4")
                else:
                    passed = aspect_close((width, height), target)
                    check(
                        "ratio",
                        passed,
                        f"{width}x{height} vs {ratio}",
                        "用 --fit expand 扩图铺满，不要留白边",
                    )
            if white_bg:
                coverage = _white_border_ratio(image)
                check(
                    "white_bg",
                    coverage >= 0.98,
                    f"四边近白像素 {coverage:.2%}",
                    "重新出图，要求纯白 #FFFFFF 无缝背景，四边铺满",
                )
            if alpha or print_quality:
                bands = image.getbands()
                if "A" not in bands:
                    check(
                        "alpha",
                        False,
                        f"mode={image.mode}",
                        "印花提取输出 PNG/WebP，并保留透明通道",
                    )
                else:
                    low, high = image.getchannel("A").getextrema()
                    alpha_ok = low < 255 and high > 0
                    check(
                        "alpha",
                        alpha_ok,
                        f"alpha {low}-{high}",
                        "检查 --cutout 是否真的把背景转成了透明",
                    )
                    if print_quality and alpha_ok:
                        border_ratio = alpha_border_white_ratio(image)
                        check(
                            "print.white_edge",
                            border_ratio <= 0.20,
                            f"alpha 边界近白 {border_ratio:.1%}",
                            "用 forge cutout --remove-enclosed-white 或 --ai 重做；"
                            "图案本身是白色字标时可忽略此项",
                        )
                        specks = alpha_speck_count(image, min_pixels=4)
                        check(
                            "print.specks",
                            specks == 0,
                            f"{specks} 个 <4px alpha 孤岛",
                            "用 forge cutout --denoise 4 清理",
                        )
    except Exception as exc:  # noqa: BLE001
        check("open", False, str(exc)[:160], "确认文件是有效图片")
    return checks
