from collections.abc import Sequence
from pathlib import Path

from PIL import Image

from aionforge.core.images import FitMode, target_size
from aionforge.run.job import Job
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


def test_parse_ref_with_and_without_role(tmp_path: Path) -> None:
    path = _png(tmp_path / "a.png")
    plain = parse_ref(str(path))
    assert plain.role is None
    assert plain.path == path.resolve()
    labeled = parse_ref(f"garment={path}")
    assert labeled.role == "garment"


async def test_generate_with_refs_uses_edit(tmp_path: Path) -> None:
    job = Job.create(tmp_path, workflow="pdp", slug="g")
    fake = FakeImage()
    ref = _png(tmp_path / "garment.png")
    saved = await run_generate(
        "hero", [Ref(ref)], job, fake, name="main-01", ratio="1:1", fit=FitMode.crop
    )
    assert saved.is_file()
    assert fake.calls[0][0] == "edit"
    assert (job.prompts / "main-01.txt").read_text() == "hero"
    with Image.open(saved) as image:
        assert image.size == (1024, 1024)


async def test_generate_expand_when_ratio_mismatches(tmp_path: Path) -> None:
    job = Job.create(tmp_path, workflow="pdp", slug="g")
    fake = FakeImage()
    ref = _png(tmp_path / "garment.png")
    saved = await run_generate(
        "hero", [Ref(ref)], job, fake, name="tall", ratio="2:3", fit=FitMode.expand
    )
    assert [call[0] for call in fake.calls] == ["edit", "edit"]
    with Image.open(saved) as image:
        assert image.size == target_size("2:3")


async def test_generate_without_refs_uses_generate(tmp_path: Path) -> None:
    job = Job.create(tmp_path, workflow="pdp", slug="g")
    fake = FakeImage()
    await run_generate("plain", [], job, fake, name="x")
    assert fake.calls[0][0] == "generate"


def test_stage_refs_renames_roles_and_deduplicates_same_role(tmp_path: Path) -> None:
    job = Job.create(tmp_path, workflow="tryon", slug="t")
    garment1 = _png(tmp_path / "g1.png")
    garment2 = _png(tmp_path / "g2.png")
    back = _png(tmp_path / "back.png")
    model = _png(tmp_path / "m.jpg")
    Image.new("RGB", (20, 20), "red").save(model)
    staged = stage_refs(
        job,
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
