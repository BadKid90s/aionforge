import pytest
from PIL import Image, ImageDraw

from aionforge.core.elements import extract_alpha_elements


def _element_image(
    size: tuple[int, int],
    boxes: list[tuple[tuple[int, int, int, int], str]],
    *,
    extra_point: tuple[int, int] | None = None,
) -> Image.Image:
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    for box, color in boxes:
        draw.rectangle(box, fill=color)
    if extra_point is not None:
        draw.point(extra_point, fill=(0, 0, 0, 255))
    return image


def test_extract_elements_splits_components_and_marks_edge() -> None:
    image = _element_image(
        (100, 100),
        [
            ((15, 15, 34, 34), (255, 0, 0, 255)),
            ((50, 50, 79, 79), (0, 0, 255, 255)),
            ((0, 0, 9, 9), (0, 255, 0, 255)),
        ],
        extra_point=(90, 90),
    )

    elements = extract_alpha_elements(image, min_pixels=16, padding=2)

    assert [element.index for element in elements] == [1, 2, 3]
    assert [element.area for element in elements] == [100, 400, 900]
    assert [element.touches_edge for element in elements] == [True, False, False]
    assert [element.image.size for element in elements] == [
        (14, 14),
        (24, 24),
        (34, 34),
    ]
    assert elements[1].image.getpixel((12, 12))[:3] == (255, 0, 0)
    assert elements[1].image.getpixel((0, 0))[3] == 0


def test_extract_elements_requires_alpha() -> None:
    with pytest.raises(ValueError, match="透明底"):
        extract_alpha_elements(Image.new("RGB", (20, 20), "white"))


def test_extract_elements_ignores_tiny_specks() -> None:
    image = _element_image(
        (40, 40),
        [((10, 10, 29, 29), (255, 0, 0, 255))],
        extra_point=(2, 2),
    )
    elements = extract_alpha_elements(image, min_pixels=4, padding=0)
    assert len(elements) == 1
    assert elements[0].area == 400
