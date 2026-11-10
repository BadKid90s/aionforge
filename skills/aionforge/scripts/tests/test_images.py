from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from aionforge.core.images import (
    MIN_SIDE,
    FitMode,
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
