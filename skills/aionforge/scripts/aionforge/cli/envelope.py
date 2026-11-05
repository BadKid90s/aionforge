"""CLI 结果信封：{ok, run_dir, images, error}。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def envelope(
    *,
    ok: bool,
    run_dir: Path | None = None,
    images: list[Path] | None = None,
    error: dict[str, str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": ok,
        "run_dir": str(run_dir) if run_dir else None,
        "images": [str(p) for p in (images or [])],
        "error": error,
    }
    if extra:
        payload.update(extra)
    return payload


def print_json(payload: dict[str, Any]) -> None:
    import typer

    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


def error_payload(stage: str, reason: str, suggestion: str) -> dict[str, str]:
    return {"stage": stage, "reason": reason, "suggestion": suggestion}
