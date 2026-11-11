from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
import pytest
from PIL import Image, ImageDraw
from typer.testing import CliRunner

from aionforge.cli.main import app

runner = CliRunner()


class _FakeResponse:
    status_code = 200


@pytest.fixture(autouse=True)
def _hermetic(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in list(os.environ):
        if name.startswith(
            (
                "XAI_",
                "OPENAI_",
                "DASHSCOPE_",
                "ARK_",
                "AIONFORGE_",
                "GEMINI_",
                "GOOGLE_",
                "HUNYUAN_",
                "QIANFAN_",
            )
        ):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: _FakeResponse())
    yield


def test_doctor_json_reports_checks() -> None:
    result = runner.invoke(app, ["doctor", "--json"])
    payload = json.loads(result.output)
    names = {c["name"] for c in payload["checks"]}
    assert {"image.selected", "image.api_key", "storage.writable"} <= names


def test_doctor_with_key_includes_connectivity(monkeypatch) -> None:
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    result = runner.invoke(app, ["doctor", "--json"])
    payload = json.loads(result.output)
    names = {c["name"] for c in payload["checks"]}
    assert {"image.api_key", "image.reachable", "image.selected"} <= names
    selected = next(c for c in payload["checks"] if c["name"] == "image.selected")
    assert selected["detail"].startswith("grok/")


def test_doctor_uses_google_gemini_base_url(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "g-key")
    monkeypatch.setenv("GOOGLE_GEMINI_BASE_URL", "http://gemini-proxy.example/v1beta")
    result = runner.invoke(app, ["doctor", "--json"])
    payload = json.loads(result.output)
    selected = next(c for c in payload["checks"] if c["name"] == "image.selected")
    assert selected["detail"].startswith("gemini/")
    base = next(c for c in payload["checks"] if c["name"] == "image.base")
    assert "http://gemini-proxy.example/v1beta" in base["detail"]


def test_doctor_warns_extra_keys(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "o-key")
    monkeypatch.setenv("GEMINI_API_KEY", "g-key")
    result = runner.invoke(app, ["doctor", "--json"])
    payload = json.loads(result.output)
    selected = next(c for c in payload["checks"] if c["name"] == "image.selected")
    assert selected["detail"].startswith("openai/")
    extra = next(c for c in payload["checks"] if c["name"] == "image.also_configured")
    assert "gemini" in extra["detail"]
    assert extra["pass"] is True


def test_doctor_reports_log_file_in_workdir() -> None:
    result = runner.invoke(app, ["doctor", "--json"])
    payload = json.loads(result.output)
    log = next(c for c in payload["checks"] if c["name"] == "logging.file")
    assert log["pass"] is True
    assert Path(log["detail"]) == Path("logs/forge.log")


def test_doctor_storage_checks_workdir() -> None:
    """storage.writable 应检查真实写入位置（当前工作目录），而非用户 home。"""
    result = runner.invoke(app, ["doctor", "--json"])
    payload = json.loads(result.output)
    storage = next(c for c in payload["checks"] if c["name"] == "storage.writable")
    assert storage["pass"] is True
    assert Path(storage["detail"]) == Path.cwd()


def test_doctor_deep_runs_real_edit(monkeypatch) -> None:
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    _fake_adapter(monkeypatch)
    result = runner.invoke(app, ["doctor", "--deep", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    deep = next(c for c in payload["checks"] if c["name"] == "image.deep_edit")
    assert deep["pass"] is True
    assert "1024x1024" in deep["detail"]


def test_product_init_json() -> None:
    result = runner.invoke(
        app,
        ["product", "init", "--logo", "brand-a", "--product", "dress", "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    product_dir = Path(payload["product_dir"])
    root = product_dir.parents[2]
    for bucket in ("bg_white", "main", "detail"):
        assert (root / bucket).is_dir()
    assert (root / ".forge" / "workspace.json").is_file()
    assert (product_dir / "facts.json").is_file()
    assert (product_dir / "manifest.json").is_file()
    assert (product_dir / "refs").is_dir()
    assert (product_dir / "prompts").is_dir()


def _init_product() -> Path:
    result = runner.invoke(
        app,
        ["product", "init", "--logo", "brand-a", "--product", "dress", "--json"],
    )
    assert result.exit_code == 0, result.output
    return Path(json.loads(result.output)["product_dir"])


def _write_placements(product_dir: Path, placements: list[dict]) -> None:
    facts_path = product_dir / "facts.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    facts["print"]["placements"] = placements
    facts_path.write_text(json.dumps(facts, ensure_ascii=False), encoding="utf-8")


def _fake_adapter(monkeypatch) -> None:
    class Fake:
        async def edit(self, prompt, images, output):
            output.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (1024, 1024), "white").save(output)
            return output

        async def generate(self, prompt, output):
            output.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (1024, 1024), "white").save(output)
            return output

        async def aclose(self):
            return None

    monkeypatch.setenv("XAI_API_KEY", "k")
    monkeypatch.setattr("aionforge.adapters.factory.build_image_adapter", lambda settings: Fake())


def _fake_logo_adapter(monkeypatch) -> None:
    class Fake:
        async def edit(self, prompt, images, output):
            output.parent.mkdir(parents=True, exist_ok=True)
            image = Image.new("RGB", (800, 800), "white")
            ImageDraw.Draw(image).rectangle((200, 200, 599, 599), fill="red")
            image.save(output)
            return output

        async def generate(self, prompt, output):
            raise AssertionError("logo 提取必须走 edit")

        async def aclose(self):
            return None

    monkeypatch.setenv("XAI_API_KEY", "k")
    monkeypatch.setattr("aionforge.adapters.factory.build_image_adapter", lambda settings: Fake())


def test_generate_writes_into_bucket(tmp_path: Path, monkeypatch) -> None:
    product_dir = _init_product()
    _fake_adapter(monkeypatch)
    prompt = tmp_path / "p.txt"
    prompt.write_text("a white dress, background #FFFFFF", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "generate",
            "--product-dir",
            str(product_dir),
            "--bucket",
            "bg_white",
            "--prompt-file",
            str(prompt),
            "--name",
            "dress-black",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    expected = product_dir.parents[2] / "bg_white" / "dress-black.png"
    assert Path(payload["images"][0]) == expected
    assert expected.is_file()
    assert (product_dir / "prompts" / "bg_white" / "dress-black.txt").is_file()


def test_cutout_command_writes_refs(tmp_path: Path) -> None:
    product_dir = _init_product()
    source = tmp_path / "logo.jpg"
    image = Image.new("RGB", (100, 100), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 30, 70, 70), fill="red")
    image.save(source)

    result = runner.invoke(
        app,
        [
            "cutout",
            "--input",
            str(source),
            "--product-dir",
            str(product_dir),
            "--name",
            "short-print",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    dest = product_dir / "refs" / "short-print.png"
    assert Path(payload["images"][0]) == dest
    with Image.open(dest) as result_image:
        assert result_image.mode == "RGBA"
        assert result_image.getpixel((0, 0))[3] == 0


def test_cutout_command_cleans_white_plate_inside_alpha(tmp_path: Path) -> None:
    product_dir = _init_product()
    source = tmp_path / "logo.png"
    image = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 89, 89), fill=(255, 255, 255, 255))
    draw.rectangle((35, 35, 64, 64), fill=(255, 0, 0, 255))
    image.save(source)

    result = runner.invoke(
        app,
        [
            "cutout",
            "--input",
            str(source),
            "--product-dir",
            str(product_dir),
            "--name",
            "print",
            "--padding",
            "2",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    with Image.open(product_dir / "refs" / "print.png") as result_image:
        assert result_image.size == (34, 34)
        assert result_image.getpixel((17, 17))[:3] == (255, 0, 0)


def test_cutout_command_ai_cleans_white_background(tmp_path: Path, monkeypatch) -> None:
    product_dir = _init_product()
    _fake_logo_adapter(monkeypatch)
    source = tmp_path / "logo.png"
    Image.new("RGB", (100, 100), "white").save(source)

    result = runner.invoke(
        app,
        [
            "cutout",
            "--input",
            str(source),
            "--product-dir",
            str(product_dir),
            "--name",
            "print",
            "--ai",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    dest = product_dir / "refs" / "print.png"
    with Image.open(dest) as result_image:
        assert result_image.mode == "RGBA"
        assert result_image.getpixel((0, 0))[3] == 0
        assert result_image.getpixel((result_image.width // 2, result_image.height // 2))[3] == 255
    manifest = json.loads((product_dir / "manifest.json").read_text(encoding="utf-8"))
    task = next(item for item in manifest["tasks"] if item["name"] == "print")
    assert task["mode"] == "ai-cutout"


def test_extract_core_element_command_is_ai_powered(
    tmp_path: Path, monkeypatch
) -> None:
    product_dir = _init_product()
    _fake_logo_adapter(monkeypatch)
    source = tmp_path / "logo.png"
    Image.new("RGB", (120, 120), "white").save(source)

    result = runner.invoke(
        app,
        [
            "extract-core-element",
            "--input",
            str(source),
            "--product-dir",
            str(product_dir),
            "--name",
            "chest-mark",
            "--element-hint",
            "红色方块",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["command"] == "extract-core-element"
    assert payload["mode"] == "ai-element"
    assert payload["complete"] is True
    assert payload["element_hint"] == "红色方块"
    assert len(payload["images"]) == 1

    dest = Path(payload["images"][0])
    with Image.open(dest) as image:
        assert image.mode == "RGBA"
        assert image.getpixel((0, 0))[3] == 0
    # 不是连通域拆分：不应产出 -element-01.png 这类碎片
    assert not (product_dir / "refs" / "chest-mark-element-01.png").exists()

    manifest = json.loads((product_dir / "manifest.json").read_text(encoding="utf-8"))
    task = next(t for t in manifest["tasks"] if t["name"] == "chest-mark")
    assert task["mode"] == "ai-element"
    assert task["element_hint"] == "红色方块"
    assert task["complete"] is True


def test_composite_command_writes_bucket(tmp_path: Path) -> None:
    product_dir = _init_product()
    garment = tmp_path / "garment.png"
    Image.new("RGB", (100, 100), "white").save(garment)
    print_file = tmp_path / "print.png"
    print_image = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    ImageDraw.Draw(print_image).rectangle((0, 0, 9, 9), fill=(255, 0, 0, 255))
    print_image.save(print_file)

    result = runner.invoke(
        app,
        [
            "composite",
            "--garment",
            str(garment),
            "--print",
            str(print_file),
            "--product-dir",
            str(product_dir),
            "--bucket",
            "bg_white",
            "--name",
            "tee-red",
            "--x",
            "0.5",
            "--y",
            "0.5",
            "--width",
            "0.2",
            "--ink",
            "normal",
            "--shading",
            "0",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    dest = product_dir.parents[2] / "bg_white" / "tee-red.png"
    assert Path(payload["images"][0]) == dest
    with Image.open(dest) as image:
        assert image.getpixel((50, 50)) == (255, 0, 0)
    manifest = json.loads((product_dir / "manifest.json").read_text(encoding="utf-8"))
    task = next(item for item in manifest["tasks"] if item["name"] == "tee-red")
    assert task["mode"] == "composite"
    assert task["ink"] == "normal"


def test_composite_placement_reads_facts(tmp_path: Path) -> None:
    product_dir = _init_product()
    print_file = product_dir / "refs" / "print.png"
    print_file.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (10, 10), (255, 0, 0, 255)).save(print_file)
    _write_placements(
        product_dir,
        [
            {
                "id": "front-badge",
                "side": "front",
                "source": "refs/print.png",
                "x": 0.5,
                "y": 0.5,
                "width": 0.2,
                "ink": "normal",
            }
        ],
    )
    garment = tmp_path / "garment.png"
    Image.new("RGB", (100, 100), "white").save(garment)

    result = runner.invoke(
        app,
        [
            "composite",
            "--product-dir",
            str(product_dir),
            "--placement",
            "front-badge",
            "--garment",
            str(garment),
            "--bucket",
            "bg_white",
            "--name",
            "tee-red",
            "--shading",
            "0",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["placement"] == "front-badge"
    dest = product_dir.parents[2] / "bg_white" / "tee-red.png"
    with Image.open(dest) as image:
        assert image.getpixel((50, 50)) == (255, 0, 0)
    manifest = json.loads((product_dir / "manifest.json").read_text(encoding="utf-8"))
    task = next(item for item in manifest["tasks"] if item["name"] == "tee-red")
    assert task["placement_id"] == "front-badge"


def test_composite_placement_with_color_adaptation(tmp_path: Path) -> None:
    product_dir = _init_product()
    raw_print = product_dir / "refs" / "print.png"
    fit_print = product_dir / "refs" / "black-fit.png"
    raw_print.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (10, 10), (10, 10, 10, 255)).save(raw_print)
    Image.new("RGBA", (10, 10), (255, 255, 255, 255)).save(fit_print)
    _write_placements(
        product_dir,
        [
            {
                "id": "back-main",
                "side": "back",
                "source": "refs/print.png",
                "x": 0.5,
                "y": 0.5,
                "width": 0.2,
                "ink": "multiply",
                "adaptations": {
                    "black": {
                        "source": "refs/black-fit.png",
                        "ink": "normal",
                    }
                },
            }
        ],
    )
    garment = tmp_path / "garment-black.png"
    Image.new("RGB", (100, 100), "black").save(garment)

    result = runner.invoke(
        app,
        [
            "composite",
            "--product-dir",
            str(product_dir),
            "--placement",
            "back-main",
            "--color",
            "black",
            "--garment",
            str(garment),
            "--bucket",
            "bg_white",
            "--name",
            "tee-black-back",
            "--shading",
            "0",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    dest = product_dir.parents[2] / "bg_white" / "tee-black-back.png"
    with Image.open(dest) as image:
        assert image.getpixel((50, 50)) == (255, 255, 255)


def test_composite_placement_missing_lists_ids(tmp_path: Path) -> None:
    product_dir = _init_product()
    _write_placements(product_dir, [{"id": "back-main", "source": "refs/print.png"}])
    garment = tmp_path / "garment.png"
    Image.new("RGB", (100, 100), "white").save(garment)

    result = runner.invoke(
        app,
        [
            "composite",
            "--product-dir",
            str(product_dir),
            "--placement",
            "nope",
            "--garment",
            str(garment),
            "--bucket",
            "bg_white",
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert "找不到 placement" in payload["error"]["reason"]
    assert "back-main" in payload["error"]["reason"]


def test_composite_placement_requires_planned_facts(tmp_path: Path) -> None:
    product_dir = _init_product()
    garment = tmp_path / "garment.png"
    Image.new("RGB", (100, 100), "white").save(garment)

    result = runner.invoke(
        app,
        [
            "composite",
            "--product-dir",
            str(product_dir),
            "--placement",
            "front-badge",
            "--garment",
            str(garment),
            "--bucket",
            "bg_white",
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert "print.placements" in payload["error"]["reason"]


def test_composite_requires_print_or_placement(tmp_path: Path) -> None:
    product_dir = _init_product()
    garment = tmp_path / "garment.png"
    Image.new("RGB", (100, 100), "white").save(garment)

    result = runner.invoke(
        app,
        [
            "composite",
            "--product-dir",
            str(product_dir),
            "--garment",
            str(garment),
            "--bucket",
            "bg_white",
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert "必须提供" in payload["error"]["reason"]


def test_print_metrics_command_json(tmp_path: Path) -> None:
    print_file = tmp_path / "print.png"
    image = Image.new("RGBA", (100, 50), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 29, 29), fill=(255, 0, 0, 255))
    draw.rectangle((40, 10, 59, 29), fill=(0, 0, 255, 255))
    image.save(print_file)

    result = runner.invoke(
        app, ["print", "metrics", "--input", str(print_file), "--json"]
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    metrics = payload["prints"][0]
    assert metrics["has_alpha"] is True
    assert metrics["bbox"] == [10, 10, 60, 30]
    assert metrics["aspect"] == pytest.approx(2.5)
    assert {entry["hex"] for entry in metrics["palette"]} == {"#FF0000", "#0000FF"}


def test_print_adapt_command_writes_refs(tmp_path: Path) -> None:
    product_dir = _init_product()
    garment = tmp_path / "black.png"
    Image.new("RGB", (100, 100), "black").save(garment)
    print_file = tmp_path / "print.png"
    Image.new("RGBA", (20, 20), (0, 0, 0, 255)).save(print_file)

    result = runner.invoke(
        app,
        [
            "print",
            "adapt",
            "--print",
            str(print_file),
            "--garment",
            str(garment),
            "--product-dir",
            str(product_dir),
            "--name",
            "print-fit",
            "--strategy",
            "auto",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    dest = product_dir / "refs" / "print-fit.png"
    assert Path(payload["images"][0]) == dest
    assert payload["strategy"] == "white"
    assert payload["contrast_after"] > payload["contrast_before"]
    with Image.open(dest) as image:
        assert image.getpixel((10, 10))[:3] == (255, 255, 255)
    manifest = json.loads((product_dir / "manifest.json").read_text(encoding="utf-8"))
    task = next(item for item in manifest["tasks"] if item["name"] == "print-fit")
    assert task["mode"] == "print-adapt"


def test_print_adapt_rejects_opaque_print(tmp_path: Path) -> None:
    product_dir = _init_product()
    garment = tmp_path / "white.png"
    Image.new("RGB", (100, 100), "white").save(garment)
    print_file = tmp_path / "print.png"
    Image.new("RGB", (20, 20), "red").save(print_file)

    result = runner.invoke(
        app,
        [
            "print",
            "adapt",
            "--print",
            str(print_file),
            "--garment",
            str(garment),
            "--product-dir",
            str(product_dir),
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert "透明印花" in payload["error"]["reason"]


def test_verify_white_background(tmp_path: Path) -> None:
    white = tmp_path / "white.png"
    Image.new("RGB", (1024, 1024), "white").save(white)
    result = runner.invoke(
        app,
        ["verify", "--image", str(white), "--ratio", "1:1", "--white-bg", "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert all(item["pass"] for item in payload["checks"])

    red = tmp_path / "red.png"
    Image.new("RGB", (1024, 1024), "red").save(red)
    result = runner.invoke(
        app, ["verify", "--image", str(red), "--white-bg", "--json"]
    )
    assert result.exit_code == 1
    payload = json.loads(result.output)
    white_check = next(item for item in payload["checks"] if item["name"] == "white_bg")
    assert white_check["pass"] is False


def test_verify_print_flags_white_edge_and_specks(tmp_path: Path) -> None:
    path = tmp_path / "print.png"
    image = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 89, 89), fill=(255, 255, 255, 255))
    draw.rectangle((30, 30, 69, 69), fill=(255, 0, 0, 255))
    draw.point((95, 95), fill=(0, 0, 0, 255))
    image.save(path)

    result = runner.invoke(
        app,
        [
            "verify",
            "--image",
            str(path),
            "--print",
            "--min-side",
            "8",
            "--json",
        ],
    )
    assert result.exit_code == 1
    payload = json.loads(result.output)
    checks = {item["name"]: item for item in payload["checks"]}
    assert checks["alpha"]["pass"] is True
    assert checks["print.white_edge"]["pass"] is False
    assert checks["print.specks"]["pass"] is False


def test_verify_print_passes_clean_alpha(tmp_path: Path) -> None:
    path = tmp_path / "print.png"
    image = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle((20, 20, 79, 79), fill=(255, 0, 0, 255))
    image.save(path)

    result = runner.invoke(
        app,
        ["verify", "--image", str(path), "--print", "--min-side", "8", "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert all(item["pass"] for item in payload["checks"])


def test_prompt_check_passes_and_fails(tmp_path: Path) -> None:
    good = tmp_path / "good.txt"
    good.write_text("背景 #F7F5F2，成衣图为唯一标准。", encoding="utf-8")
    result = runner.invoke(app, ["prompt", "check", "--file", str(good), "--json"])
    assert result.exit_code == 0, result.output

    bad = tmp_path / "bad.txt"
    bad.write_text("参考图1的衣服和图2的模特。", encoding="utf-8")
    result = runner.invoke(
        app,
        ["prompt", "check", "--file", str(bad), "--visible-text", "--json"],
    )
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert len(payload["issues"]) >= 3


def test_prompt_check_checks_print_text(tmp_path: Path) -> None:
    prompt = tmp_path / "p.txt"
    prompt.write_text("背景 #FFFFFF，胸前印花。", encoding="utf-8")
    facts = tmp_path / "facts.json"
    facts.write_text(
        json.dumps({"print": {"has_print": True, "text_exact": "LOVE"}}),
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["prompt", "check", "--file", str(prompt), "--facts", str(facts), "--json"],
    )
    assert result.exit_code == 1
    assert "LOVE" in json.loads(result.output)["issues"][0]
