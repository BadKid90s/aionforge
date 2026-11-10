from collections.abc import Sequence
from pathlib import Path

import pytest
from PIL import Image

from aionforge.core.images import FitMode, target_size
from aionforge.run.workspace import Product, Workspace
from aionforge.tools.generate import Ref, parse_ref, run_generate, stage_refs


class FakeImage:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    async def edit(self, prompt: str, images: Sequence[Path], output: Path) -> Path:
        self.calls.append(("edit", tuple(p.name for p in images)))
        output.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (800, 800), "blue").save(output)
        return output

    async def generate(self, prompt: str, output: Path) -> Path:
        self.calls.append(("generate", ()))
        output.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (800, 800), "green").save(output)
        return output


def _png(path: Path) -> Path:
    Image.new("RGB", (100, 100), "red").save(path)
    return path


def _product(tmp_path: Path) -> Product:
    return Product.create(Workspace.create(tmp_path, "brand"), "dress")


def test_parse_ref_with_and_without_role(tmp_path: Path) -> None:
    path = _png(tmp_path / "a.png")
    plain = parse_ref(str(path))
    assert plain.role is None
    assert plain.path == path.resolve()
    labeled = parse_ref(f"garment={path}")
    assert labeled.role == "garment"


async def test_generate_with_refs_writes_to_bucket(tmp_path: Path) -> None:
    product = _product(tmp_path)
    fake = FakeImage()
    ref = _png(tmp_path / "garment.png")
    saved = await run_generate(
        "hero",
        [Ref(ref)],
        product,
        fake,
        name="dress-black-hero",
        bucket="main",
        ratio="1:1",
        fit=FitMode.crop,
    )
    assert saved == product.workspace.root / "main" / "dress-black-hero.png"
    assert saved.is_file()
    assert fake.calls[0][0] == "edit"
    assert (product.prompts / "main" / "dress-black-hero.txt").read_text() == "hero"
    with Image.open(saved) as image:
        assert image.size == (1024, 1024)


async def test_generate_expand_when_ratio_mismatches(tmp_path: Path) -> None:
    product = _product(tmp_path)
    fake = FakeImage()
    ref = _png(tmp_path / "garment.png")
    saved = await run_generate(
        "hero",
        [Ref(ref)],
        product,
        fake,
        name="tall",
        bucket="main",
        ratio="2:3",
        fit=FitMode.expand,
    )
    assert [call[0] for call in fake.calls] == ["edit", "edit"]
    with Image.open(saved) as image:
        assert image.size == target_size("2:3")


async def test_generate_without_refs_uses_generate(tmp_path: Path) -> None:
    product = _product(tmp_path)
    fake = FakeImage()
    saved = await run_generate(
        "plain", [], product, fake, name="dress-black", bucket="bg_white"
    )
    assert saved == product.workspace.root / "bg_white" / "dress-black.png"
    assert fake.calls[0][0] == "generate"


async def test_generate_intermediate_goes_to_refs(tmp_path: Path) -> None:
    product = _product(tmp_path)
    fake = FakeImage()
    ref = _png(tmp_path / "photo.png")
    saved = await run_generate(
        "extract", [Ref(ref)], product, fake, name="print", store="refs", cutout=False
    )
    assert saved == product.refs / "print.png"


async def test_generate_requires_bucket_or_store(tmp_path: Path) -> None:
    product = _product(tmp_path)
    with pytest.raises(ValueError, match="二选一"):
        await run_generate("x", [], product, FakeImage(), name="x")


def test_stage_refs_renames_roles_and_deduplicates_same_role(tmp_path: Path) -> None:
    product = _product(tmp_path)
    garment1 = _png(tmp_path / "g1.png")
    garment2 = _png(tmp_path / "g2.png")
    back = _png(tmp_path / "back.png")
    model = _png(tmp_path / "m.jpg")
    Image.new("RGB", (20, 20), "red").save(model)
    staged = stage_refs(
        product,
        [
            Ref(garment1, "garment"),
            Ref(garment2, "garment"),
            Ref(back, "garment_back"),
            Ref(model, "model"),
        ],
    )
    assert [p.name for p in staged] == [
        "garment.png",
        "garment_2.png",
        "garment_back.png",
        "model.jpg",
    ]


def test_stage_refs_flattens_transparent_ref_onto_white(tmp_path: Path) -> None:
    product = _product(tmp_path)
    print_ref = tmp_path / "print.png"
    image = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    image.paste((255, 0, 0, 255), (10, 10, 30, 30))
    image.save(print_ref)

    staged = stage_refs(product, [Ref(print_ref, "print")])
    with Image.open(staged[0]) as result:
        assert result.mode == "RGB"
        assert result.getpixel((0, 0)) == (255, 255, 255)
        assert result.getpixel((20, 20)) == (255, 0, 0)
