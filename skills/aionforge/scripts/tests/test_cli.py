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


def test_workspace_init_json() -> None:
    result = runner.invoke(app, ["workspace", "init", "--logo", "品牌 A", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    root = Path(payload["run_dir"])
    assert root.name == "品牌-A"
    for bucket in ("bg_white", "main", "sku", "detail"):
        assert (root / bucket).is_dir()
    assert (root / ".forge" / "workspace.json").is_file()


def test_product_init_json() -> None:
    result = runner.invoke(
        app,
        ["product", "init", "--logo", "brand-a", "--product", "dress", "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    product_dir = Path(payload["product_dir"])
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


def test_generate_writes_intermediate_to_refs(tmp_path: Path, monkeypatch) -> None:
    product_dir = _init_product()
    _fake_adapter(monkeypatch)
    prompt = tmp_path / "p.txt"
    prompt.write_text("extract print on #FFFFFF", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "generate",
            "--product-dir",
            str(product_dir),
            "--store",
            "refs",
            "--prompt-file",
            str(prompt),
            "--name",
            "print",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert Path(payload["images"][0]) == product_dir / "refs" / "print.png"


def test_generate_rejects_bucket_and_store_together(tmp_path: Path) -> None:
    product_dir = _init_product()
    prompt = tmp_path / "p.txt"
    prompt.write_text("x #FFFFFF", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "generate",
            "--product-dir",
            str(product_dir),
            "--bucket",
            "main",
            "--store",
            "refs",
            "--prompt-file",
            str(prompt),
            "--json",
        ],
    )
    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["ok"] is False


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


def test_list_assets(tmp_path: Path) -> None:
    product_dir = _init_product()
    target = product_dir.parents[2] / "main" / "dress-black-hero.png"
    Image.new("RGB", (32, 32), "white").save(target)
    result = runner.invoke(app, ["list", "--logo", "brand-a", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["buckets"]["main"][0]["name"] == "dress-black-hero.png"
