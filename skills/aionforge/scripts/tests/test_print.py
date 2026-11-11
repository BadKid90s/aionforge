from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from aionforge.core.print import (
    adapt_print,
    contrast_ratio,
    measure_print,
    parse_palette,
)


def _transparent_print(path: Path) -> Path:
    image = Image.new("RGBA", (100, 50), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 29, 29), fill=(255, 0, 0, 255))
    draw.rectangle((40, 10, 59, 29), fill=(0, 0, 255, 255))
    image.save(path)
    return path


def _garment(path: Path, color: str) -> Path:
    Image.new("RGB", (100, 100), color).save(path)
    return path


def test_measure_print_transparent(tmp_path: Path) -> None:
    metrics = measure_print(_transparent_print(tmp_path / "print.png"))

    assert metrics.has_alpha is True
    assert metrics.background_estimated is False
    assert metrics.size == (100, 50)
    assert metrics.bbox == (10, 10, 60, 30)
    assert metrics.aspect == pytest.approx(2.5)
    assert metrics.coverage == pytest.approx(0.8)
    assert {entry.hex for entry in metrics.palette} == {"#FF0000", "#0000FF"}
    assert metrics.edge_density > 0
    assert metrics.mean_stroke_px > 0
    assert metrics.transparent_holes == 0
    assert metrics.touches_edge is False


def test_measure_print_white_background(tmp_path: Path) -> None:
    image = Image.new("RGB", (100, 100), "white")
    ImageDraw.Draw(image).rectangle((40, 40, 59, 59), fill="black")
    path = tmp_path / "flat.png"
    image.save(path)

    metrics = measure_print(path)

    assert metrics.has_alpha is False
    assert metrics.background_estimated is True
    assert metrics.bbox == (40, 40, 60, 60)
    assert metrics.palette[0].hex == "#000000"
    assert metrics.palette[0].share > 0.9


def test_measure_print_counts_enclosed_holes(tmp_path: Path) -> None:
    image = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 49, 49), fill=(255, 0, 0, 255))
    draw.rectangle((25, 25, 34, 34), fill=(0, 0, 0, 0))
    path = tmp_path / "ring.png"
    image.save(path)

    metrics = measure_print(path)

    assert metrics.transparent_holes == 1


def test_contrast_ratio_extremes() -> None:
    assert contrast_ratio((0, 0, 0), (255, 255, 255)) == pytest.approx(21, rel=1e-3)
    assert contrast_ratio((10, 20, 30), (10, 20, 30)) == pytest.approx(1)


def test_parse_palette() -> None:
    assert parse_palette("#FF0000,#00ff00") == [(255, 0, 0), (0, 255, 0)]
    assert parse_palette(None) == []
    with pytest.raises(ValueError, match="6 位 Hex"):
        parse_palette("red")


def test_adapt_auto_white_on_dark_garment(tmp_path: Path) -> None:
    print_file = tmp_path / "print.png"
    Image.new("RGBA", (20, 20), (0, 0, 0, 255)).save(print_file)
    garment = _garment(tmp_path / "black.png", "black")

    report = adapt_print(print_file, garment, strategy="auto")

    assert report.strategy == "white"
    assert report.image.getpixel((10, 10))[:3] == (255, 255, 255)
    assert report.contrast_after > report.contrast_before


def test_adapt_lighten_preserves_alpha(tmp_path: Path) -> None:
    print_file = tmp_path / "print.png"
    image = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle((5, 5, 14, 14), fill=(20, 20, 20, 128))
    image.save(print_file)
    garment = _garment(tmp_path / "black.png", "black")

    report = adapt_print(print_file, garment, strategy="lighten")

    assert report.image.getchannel("A").tobytes() == image.getchannel("A").tobytes()
    assert report.image.size == image.size


def test_adapt_palette_maps_to_target(tmp_path: Path) -> None:
    print_file = tmp_path / "print.png"
    Image.new("RGBA", (20, 20), (255, 0, 0, 255)).save(print_file)
    garment = _garment(tmp_path / "white.png", "white")

    report = adapt_print(
        print_file,
        garment,
        strategy="palette",
        palette=[(0, 128, 0)],
    )

    assert report.image.getpixel((10, 10)) == (0, 128, 0, 255)
    assert report.image.getchannel("A").getextrema() == (255, 255)


def test_adapt_outline_adds_padding(tmp_path: Path) -> None:
    print_file = tmp_path / "print.png"
    Image.new("RGBA", (20, 20), (255, 0, 0, 255)).save(print_file)
    garment = _garment(tmp_path / "white.png", "white")

    report = adapt_print(
        print_file, garment, strategy="outline", outline_px=2
    )

    assert report.image.size == (24, 24)
    assert report.image.getpixel((0, 0))[:3] == (0, 0, 0)
    assert report.image.getpixel((12, 12))[:3] == (255, 0, 0)


def test_adapt_outline_raises_contrast_on_dark_garment(tmp_path: Path) -> None:
    print_file = tmp_path / "print.png"
    Image.new("RGBA", (20, 20), (20, 20, 20, 255)).save(print_file)
    garment = _garment(tmp_path / "black.png", "black")

    report = adapt_print(print_file, garment, strategy="outline", outline_px=2)

    assert report.contrast_after >= 3
    assert report.warnings == ["outline 会在印花外加一圈描边，画布已自动留出边距"]


def test_adapt_requires_alpha(tmp_path: Path) -> None:
    print_file = tmp_path / "print.png"
    Image.new("RGB", (20, 20), "red").save(print_file)
    garment = _garment(tmp_path / "white.png", "white")

    with pytest.raises(ValueError, match="透明印花"):
        adapt_print(print_file, garment)
