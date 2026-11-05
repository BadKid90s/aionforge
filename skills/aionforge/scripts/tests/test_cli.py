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
        if name.startswith(("XAI_", "OPENAI_", "DASHSCOPE_", "ARK_", "AIONFORGE_")):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: _FakeResponse())
    yield


def test_doctor_json_reports_checks() -> None:
    result = runner.invoke(app, ["doctor", "--json"])
    payload = json.loads(result.output)
    assert isinstance(payload["ok"], bool)
    assert result.exit_code == (0 if payload["ok"] else 1)
    names = {c["name"] for c in payload["checks"]}
    assert {"image.api_key", "storage.writable"} <= names


def test_doctor_with_key_includes_connectivity(monkeypatch) -> None:
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    result = runner.invoke(app, ["doctor", "--json"])
    payload = json.loads(result.output)
    names = {c["name"] for c in payload["checks"]}
    assert {"image.api_key", "image.reachable"} <= names


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
