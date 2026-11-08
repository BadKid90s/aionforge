from __future__ import annotations

import base64
import json
from pathlib import Path

import httpx
from PIL import Image

from aionforge.adapters.image import GeminiImageAdapter


def _png(path: Path, color: str = "red") -> Path:
    Image.new("RGB", (8, 8), color).save(path)
    return path


def _png_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _gemini_ok(b64: str) -> dict:
    return {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "ok"},
                        {"inlineData": {"mimeType": "image/png", "data": b64}},
                    ]
                }
            }
        ]
    }


def _adapter(handler) -> GeminiImageAdapter:
    client = httpx.AsyncClient(
        base_url="https://generativelanguage.googleapis.com/v1beta",
        headers={"x-goog-api-key": "g-key"},
        transport=httpx.MockTransport(handler),
    )
    return GeminiImageAdapter(client, model="gemini-3-pro-image")


async def test_edit_posts_generate_content_with_inline_images(tmp_path: Path) -> None:
    result = _png(tmp_path / "result.png", "blue")
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=_gemini_ok(_png_b64(result)))

    ref = _png(tmp_path / "garment.png")
    dest = tmp_path / "out.png"
    saved = await _adapter(handler).edit("wear this dress", [ref], dest)

    assert saved == dest
    assert dest.is_file()
    assert captured["url"].endswith("/models/gemini-3-pro-image:generateContent")
    parts = captured["body"]["contents"][0]["parts"]
    assert parts[0] == {"text": "wear this dress"}
    assert parts[1]["inline_data"]["mime_type"] == "image/png"
    assert parts[1]["inline_data"]["data"] == _png_b64(ref)
    assert captured["body"]["generationConfig"]["responseModalities"] == ["TEXT", "IMAGE"]


async def test_generate_sends_text_only_and_writes_image(tmp_path: Path) -> None:
    result = _png(tmp_path / "result.png", "green")
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=_gemini_ok(_png_b64(result)))

    dest = tmp_path / "plain.png"
    await _adapter(handler).generate("a white t-shirt", dest)

    parts = captured["body"]["contents"][0]["parts"]
    assert parts == [{"text": "a white t-shirt"}]
    assert dest.is_file()


async def test_edit_raises_when_response_has_no_image(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "no image"}]}}]},
        )

    dest = tmp_path / "out.png"
    try:
        await _adapter(handler).edit("x", [_png(tmp_path / "a.png")], dest)
    except RuntimeError as exc:
        assert "图片" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
