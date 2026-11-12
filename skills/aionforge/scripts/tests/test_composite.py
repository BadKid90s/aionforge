from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from aionforge.core.composite import composite_print
from aionforge.core.placement import mean_luminance, placement_box, validate_box


def _garment(path: Path, color: str, size: tuple[int, int] = (200, 200)) -> Path:
    Image.new("RGB", size, color).save(path)
    return path


def _print(path: Path, color: tuple[int, int, int, int]) -> Path:
    image = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle((0, 0, 19, 19), fill=color)
    image.save(path)
    return path


def test_composite_normal_on_light_garment(tmp_path: Path) -> None:
    garment = _garment(tmp_path / "garment.png", "white")
    print_file = _print(tmp_path / "print.png", (255, 0, 0, 255))

    result = composite_print(
        garment,
        print_file,
        x=0.5,
        y=0.5,
        width=0.1,
        ink="normal",
        shading=0,
    )

    assert result.ink == "normal"
    assert result.image.size == (200, 200)
    assert result.image.getpixel((100, 100)) == (255, 0, 0)
    assert result.image.getpixel((0, 0)) == (255, 255, 255)


def test_composite_multiply_white_print_stays_invisible(tmp_path: Path) -> None:
    garment = _garment(tmp_path / "garment.png", "white")
    print_file = _print(tmp_path / "print.png", (255, 255, 255, 255))

    result = composite_print(
        garment, print_file, x=0.5, y=0.5, width=0.1, ink="multiply", shading=0
    )

    assert result.image.getpixel((100, 100)) == (255, 255, 255)


def test_composite_auto_on_dark_garment_turns_black_ink_white(tmp_path: Path) -> None:
    garment = _garment(tmp_path / "garment.png", "black")
    print_file = _print(tmp_path / "print.png", (0, 0, 0, 255))

    result = composite_print(
        garment, print_file, x=0.5, y=0.5, width=0.1, ink="auto", shading=0
    )

    assert result.ink == "white"
    red, green, blue = result.image.getpixel((100, 100))
    assert min(red, green, blue) > 200


def test_composite_auto_on_light_garment_uses_multiply(tmp_path: Path) -> None:
    garment = _garment(tmp_path / "garment.png", "white")
    print_file = _print(tmp_path / "print.png", (255, 0, 0, 255))

    result = composite_print(
        garment, print_file, x=0.5, y=0.5, width=0.1, ink="auto", shading=0
    )

    assert result.ink == "multiply"
    assert result.image.getpixel((100, 100)) == (255, 0, 0)


def test_composite_rejects_out_of_bounds(tmp_path: Path) -> None:
    garment = _garment(tmp_path / "garment.png", "white")
    print_file = _print(tmp_path / "print.png", (255, 0, 0, 255))

    with pytest.raises(ValueError, match="超出画布"):
        composite_print(
            garment, print_file, x=0.1, y=0.5, width=0.5, ink="normal", shading=0
        )


def test_placement_box_and_validation() -> None:
    box = placement_box((200, 200), (20, 20), x=0.5, y=0.5, width=0.1)
    assert box == (90, 90, 20, 20)
    validate_box(box, (200, 200))

    with pytest.raises(ValueError, match="超出画布"):
        validate_box((1, 1, 200, 200), (200, 200))


def test_placement_box_respects_max_height_and_anchors() -> None:
    # 竖长图 100x200：按 width=0.30 会得 300x600，受 max_height=0.40 封顶到 200x400
    left, top, width, height = placement_box(
        (1000, 1000),
        (100, 200),
        x=0.5,
        y=0.19,
        width=0.30,
        max_height=0.40,
        anchor="top",
    )
    assert (left, top, width, height) == (400, 190, 200, 400)

    _, bottom_top, _, bh = placement_box(
        (1000, 1000),
        (100, 100),
        x=0.66,
        y=0.84,
        width=0.065,
        anchor="bottom",
    )
    assert bottom_top + bh == 840


def test_composite_with_region_preset_left_chest(tmp_path: Path) -> None:
    garment = _garment(tmp_path / "garment.png", "white", size=(1000, 1000))
    print_file = _print(tmp_path / "badge.png", (255, 0, 0, 255))

    result = composite_print(
        garment,
        print_file,
        region="left_chest",
        ink="normal",
        shading=0,
    )

    # left_chest 固定中心在 x=0.61 (610), y=0.29 (290)，正面图中心右侧
    assert result.image.getpixel((610, 290)) == (255, 0, 0)
    # 右胸对照点 (320, 290) 必须仍是白底
    assert result.image.getpixel((320, 290)) == (255, 255, 255)


def test_mean_luminance_extremes() -> None:
    assert mean_luminance(Image.new("RGB", (4, 4), "black")) == 0
    assert mean_luminance(Image.new("RGB", (4, 4), "white")) == 255
