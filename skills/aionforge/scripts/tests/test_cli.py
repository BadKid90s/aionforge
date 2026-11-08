from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
import pytest
from PIL import Image
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


def test_job_init_json(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["job", "init", "--workflow", "pdp", "--slug", "dress", "--json"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    run_dir = Path(payload["run_dir"])
    assert (run_dir / "project.json").is_file()
    assert payload["workflow"] == "pdp"


def test_generate_requires_prompt() -> None:
    result = runner.invoke(app, ["generate", "--json"])
    assert result.exit_code != 0


def test_generate_with_fake_adapter(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XAI_API_KEY", "k")

    class Fake:
        async def edit(self, prompt, images, output):
            Image.new("RGB", (64, 64), "white").save(output)
            return output

        async def generate(self, prompt, output):
            Image.new("RGB", (64, 64), "white").save(output)
            return output

        async def aclose(self):
            return None

    monkeypatch.setattr("aionforge.adapters.factory.build_image_adapter", lambda settings: Fake())
    prompt = tmp_path / "p.txt"
    prompt.write_text("a dress", encoding="utf-8")
    result = runner.invoke(
        app,
        ["generate", "--prompt-file", str(prompt), "--name", "main-01", "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["images"]
    assert Path(payload["images"][0]).is_file()
