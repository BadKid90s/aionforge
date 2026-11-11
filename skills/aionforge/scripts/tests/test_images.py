from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from aionforge.core.images import (
    MIN_SIDE,
    FitMode,
    alpha_border_white_ratio,
    alpha_speck_count,
    cutout_background,
    fit_image,
    flatten_to_rgb,
    needs_expand,
    parse_ratio,
    prepare_expand_canvas,
    prepare_logo,
    target_size,
)


def test_parse_ratio_accepts_common_formats() -> None:
    assert parse_ratio("3:4") == (3.0, 4.0)
    assert parse_ratio(" 3 / 4 ") == (3.0, 4.0)
    assert parse_ratio("3x4") == (3.0, 4.0)


def test_parse_ratio_rejects_invalid_values() -> None:
    for value in ("3", "3:", "0:4", "-1:4", "a:b"):
        with pytest.raises(ValueError):
            parse_ratio(value)


def test_target_size_handles_common_ratios() -> None:
    assert target_size("1:1") == (1024, 1024)
    assert target_size("3:4") == (768, 1024)
    width, height = target_size("3:4")
    assert width > MIN_SIDE
    assert height > MIN_SIDE


def _make_image(path: Path, size: tuple[int, int] = (400, 300)) -> Path:
    Image.new("RGB", size, "red").save(path)
    return path


def test_fit_image_crop_outputs_exact_size(tmp_path: Path) -> None:
    path = _make_image(tmp_path / "in.png")
    fit_image(path, (200, 400), FitMode.crop)
    with Image.open(path) as image:
        assert image.size == (200, 400)


def test_needs_expand_when_aspect_differs(tmp_path: Path) -> None:
    wide = _make_image(tmp_path / "wide.png", (800, 400))
    square = _make_image(tmp_path / "sq.png", (500, 500))
    assert needs_expand(wide, "2:3")
    assert not needs_expand(square, "1:1")


def test_prepare_expand_canvas_fills_target_without_white_bars(tmp_path: Path) -> None:
    source = _make_image(tmp_path / "wide.png", (800, 400))
    dest = tmp_path / "out.png"
    prepare_expand_canvas(source, dest, (400, 800))
    with Image.open(dest) as image:
        assert image.size == (400, 800)
        corners = [image.getpixel((0, 0)), image.getpixel((399, 799))]
        assert all(pixel != (255, 255, 255) for pixel in corners)


def test_cutout_rejects_jpeg(tmp_path: Path) -> None:
    path = tmp_path / "in.jpg"
    Image.new("RGB", (20, 20), "white").save(path)
    with pytest.raises(ValueError, match="透明背景"):
        cutout_background(path)


def test_cutout_removes_off_white_background_and_crops(tmp_path: Path) -> None:
    path = tmp_path / "logo.png"
    image = Image.new("RGB", (100, 100), "#EFEFEF")
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 30, 70, 70), fill="red")
    image.save(path)

    cutout_background(path, padding=2)
    with Image.open(path) as result:
        assert result.mode == "RGBA"
        assert result.getpixel((0, 0))[3] == 0
        assert result.getpixel((result.width // 2, result.height // 2))[3] == 255
        assert result.width <= 46
        assert result.height <= 46


def test_cutout_keeps_white_inside_design(tmp_path: Path) -> None:
    path = tmp_path / "logo.png"
    image = Image.new("RGB", (80, 80), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 60, 60), fill="blue")
    draw.rectangle((35, 35, 45, 45), fill="white")
    image.save(path)

    cutout_background(path, padding=2)
    with Image.open(path) as result:
        assert result.getpixel((0, 0))[3] == 0
        assert result.getpixel((result.width // 2, result.height // 2))[3] == 255


def test_fit_image_keeps_transparent_area_white(tmp_path: Path) -> None:
    path = tmp_path / "rgba.png"
    image = Image.new("RGBA", (600, 600), (0, 0, 0, 0))
    image.paste((255, 0, 0, 255), (200, 200, 400, 400))
    image.save(path)

    fit_image(path, (300, 300), FitMode.crop)
    with Image.open(path) as result:
        assert result.mode == "RGB"
        assert result.getpixel((0, 0)) == (255, 255, 255)
        assert result.getpixel((150, 150)) == (255, 0, 0)


def test_fit_image_uses_custom_background(tmp_path: Path) -> None:
    path = tmp_path / "rgba.png"
    image = Image.new("RGBA", (600, 600), (0, 0, 0, 0))
    image.paste((255, 0, 0, 255), (200, 200, 400, 400))
    image.save(path)

    fit_image(path, (300, 300), FitMode.crop, background="#F7F5F2")
    with Image.open(path) as result:
        assert result.getpixel((0, 0)) == (247, 245, 242)


def test_flatten_to_rgb_composites_alpha_on_white() -> None:
    image = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    image.paste((0, 128, 0, 255), (4, 4, 6, 6))
    result = flatten_to_rgb(image)
    assert result.mode == "RGB"
    assert result.getpixel((0, 0)) == (255, 255, 255)
    assert result.getpixel((5, 5)) == (0, 128, 0)


def test_prepare_logo_from_white_jpg(tmp_path: Path) -> None:
    source = tmp_path / "logo.jpg"
    image = Image.new("RGB", (100, 100), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 30, 70, 70), fill="red")
    image.save(source)

    dest = tmp_path / "logo.png"
    prepare_logo(source, dest, padding=2)
    with Image.open(dest) as result:
        assert result.mode == "RGBA"
        assert result.getpixel((0, 0))[3] == 0
        assert result.getpixel((result.width // 2, result.height // 2))[3] == 255


def test_prepare_logo_keeps_existing_alpha(tmp_path: Path) -> None:
    source = tmp_path / "logo.png"
    image = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 30, 70, 70), fill=(255, 0, 0, 255))
    image.save(source)

    dest = tmp_path / "out.png"
    prepare_logo(source, dest, padding=2)
    with Image.open(dest) as result:
        assert result.getpixel((0, 0))[3] == 0
        assert result.getpixel((result.width // 2, result.height // 2))[3] == 255
        assert result.width <= 46


def test_prepare_logo_cleans_white_plate_inside_alpha(tmp_path: Path) -> None:
    """alpha 只包住画布时，alpha 内的白底也必须清掉，而不是直接裁边返回。"""
    source = tmp_path / "logo.png"
    image = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 89, 89), fill=(255, 255, 255, 255))
    draw.rectangle((35, 35, 64, 64), fill=(255, 0, 0, 255))
    image.save(source)

    dest = tmp_path / "out.png"
    prepare_logo(source, dest, padding=2)
    with Image.open(dest) as result:
        assert result.size == (34, 34)
        assert result.getpixel((0, 0))[3] == 0
        assert result.getpixel((17, 17))[:3] == (255, 0, 0)
        assert result.getpixel((17, 17))[3] == 255


def test_prepare_logo_keeps_white_inside_alpha_design(tmp_path: Path) -> None:
    """被图案包住的白色文字 / 高光不能当成白底删掉。"""
    source = tmp_path / "logo.png"
    image = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 79, 79), fill=(0, 0, 255, 255))
    draw.rectangle((40, 40, 59, 59), fill=(255, 255, 255, 255))
    image.save(source)

    dest = tmp_path / "out.png"
    prepare_logo(source, dest, padding=2)
    with Image.open(dest) as result:
        assert result.size == (64, 64)
        assert result.getpixel((32, 32)) == (255, 255, 255, 255)


def test_prepare_logo_keeps_white_logo_when_cleaning_would_erase_everything(
    tmp_path: Path,
) -> None:
    """纯白图案没有可删的白底，清理后为空时必须回退到原图。"""
    source = tmp_path / "logo.png"
    image = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 79, 79), fill=(255, 255, 255, 255))
    image.save(source)

    dest = tmp_path / "out.png"
    prepare_logo(source, dest, padding=2)
    with Image.open(dest) as result:
        assert result.size == (64, 64)
        assert result.getpixel((32, 32)) == (255, 255, 255, 255)


def test_prepare_logo_keeps_white_wordmark_touching_one_edge(tmp_path: Path) -> None:
    """白色字标只贴住一条边时，不能按白底处理。"""
    source = tmp_path / "logo.png"
    image = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 35, 70), fill=(255, 0, 0, 255))
    draw.rectangle((40, 35, 95, 45), fill=(255, 255, 255, 255))
    image.save(source)

    dest = tmp_path / "out.png"
    prepare_logo(source, dest, padding=2)
    with Image.open(dest) as result:
        assert result.size == (90, 65)
        assert result.getpixel((52, 32)) == (255, 255, 255, 255)


def test_prepare_logo_can_skip_alpha_cleaning(tmp_path: Path) -> None:
    source = tmp_path / "logo.png"
    image = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 89, 89), fill=(255, 255, 255, 255))
    draw.rectangle((35, 35, 64, 64), fill=(255, 0, 0, 255))
    image.save(source)

    dest = tmp_path / "out.png"
    prepare_logo(source, dest, padding=2, clean_white=False)
    with Image.open(dest) as result:
        assert result.size == (84, 84)
        assert result.getpixel((2, 2))[3] == 255


def test_prepare_logo_removes_enclosed_white_when_requested(tmp_path: Path) -> None:
    """字母孔洞里的封闭白区，显式开启后要清成透明。"""
    source = tmp_path / "logo.png"
    image = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 79, 79), fill=(0, 0, 255, 255))
    draw.rectangle((40, 40, 59, 59), fill=(255, 255, 255, 255))
    image.save(source)

    dest = tmp_path / "out.png"
    prepare_logo(source, dest, padding=2, remove_enclosed_white=True)
    with Image.open(dest) as result:
        assert result.size == (64, 64)
        assert result.getpixel((32, 32))[3] == 0
        assert result.getpixel((2, 2))[3] == 255


def test_cutout_removes_enclosed_white_when_requested(tmp_path: Path) -> None:
    path = tmp_path / "logo.png"
    image = Image.new("RGB", (100, 100), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 79, 79), fill="blue")
    draw.rectangle((40, 40, 59, 59), fill="white")
    image.save(path)

    cutout_background(path, padding=2, remove_enclosed_white=True)
    with Image.open(path) as result:
        assert result.getpixel((0, 0))[3] == 0
        assert result.getpixel((result.width // 2, result.height // 2))[3] == 0


def test_prepare_logo_denoise_removes_isolated_specks(tmp_path: Path) -> None:
    source = tmp_path / "logo.png"
    image = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 40, 59, 59), fill=(255, 0, 0, 255))
    draw.point((10, 10), fill=(0, 0, 0, 255))
    image.save(source)

    dest = tmp_path / "out.png"
    prepare_logo(source, dest, padding=2, denoise=4)
    with Image.open(dest) as result:
        assert result.size == (24, 24)
        assert result.getpixel((12, 12))[3] == 255


def test_alpha_quality_helpers_detect_white_edge_and_specks() -> None:
    image = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 89, 89), fill=(255, 255, 255, 255))
    draw.rectangle((30, 30, 69, 69), fill=(255, 0, 0, 255))
    draw.point((95, 95), fill=(0, 0, 0, 255))

    assert alpha_border_white_ratio(image) > 0.5
    assert alpha_speck_count(image, min_pixels=4) == 1
