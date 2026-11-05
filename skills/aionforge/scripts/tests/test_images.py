from pathlib import Path

import pytest
from PIL import Image

from aionforge.core.images import (
    MIN_SIDE,
    FitMode,
    cutout_background,
    fit_image,
    needs_expand,
    parse_ratio,
    prepare_expand_canvas,
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
