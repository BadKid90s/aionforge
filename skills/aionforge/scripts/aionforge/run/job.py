"""一次出图任务的运行目录：project.json / plan.json / manifest.json / images / work。"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

BEIJING_TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")


def slugify(value: str, fallback: str = "job") -> str:
    return re.sub(r"[^\w-]+", "-", value, flags=re.UNICODE).strip("-") or fallback


def new_job_id(slug: str) -> str:
    stamp = datetime.now(BEIJING_TZ).strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{uuid4().hex[:4]}-{slugify(slug)}"


def _now() -> str:
    return datetime.now(BEIJING_TZ).isoformat(timespec="seconds")


def _dump(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


class Job:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.images = self.root / "images"
        self.work = self.root / "work"
        self.prompts = self.work / "prompts"

    @property
    def project_path(self) -> Path:
        return self.root / "project.json"

    @property
    def plan_path(self) -> Path:
        return self.root / "plan.json"

    @property
    def manifest_path(self) -> Path:
        return self.root / "manifest.json"

    def prepare(self) -> None:
        self.images.mkdir(parents=True, exist_ok=True)
        self.prompts.mkdir(parents=True, exist_ok=True)

    @classmethod
    def create(
        cls,
        base: Path,
        *,
        workflow: str,
        slug: str,
        extra: Mapping[str, Any] | None = None,
    ) -> Job:
        job = cls(base / new_job_id(slug))
        job.prepare()
        project: dict[str, Any] = {
            "workflow": workflow,
            "slug": slugify(slug),
            "created_at": _now(),
        }
        if extra:
            project.update(extra)
        _dump(job.project_path, project)
        _dump(job.plan_path, {"tasks": []})
        _dump(job.manifest_path, {"tasks": []})
        return job

    @classmethod
    def open(cls, root: Path) -> Job:
        job = cls(root)
        job.prepare()
        if not job.project_path.is_file():
            _dump(
                job.project_path,
                {"workflow": "ad-hoc", "slug": slugify(root.name), "created_at": _now()},
            )
        if not job.manifest_path.is_file():
            _dump(job.manifest_path, {"tasks": []})
        return job

    def write_prompt(self, name: str, text: str) -> Path:
        self.prepare()
        path = self.prompts / f"{name}.txt"
        path.write_text(text, encoding="utf-8")
        return path

    def image_path(self, name: str) -> Path:
        self.prepare()
        return self.images / f"{name}.png"

    def relative(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.root))
        except ValueError:
            return str(path)

    def write_plan(self, tasks: Sequence[Mapping[str, Any]]) -> Path:
        return _dump(self.plan_path, {"tasks": list(tasks)})

    def record_task(
        self,
        name: str,
        status: str,
        *,
        image: Path | None = None,
        prompt: Path | None = None,
        refs: Sequence[Path] = (),
        error: str = "",
        extra: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        manifest = _load(self.manifest_path)
        tasks: list[dict[str, Any]] = list(manifest.get("tasks") or [])
        entry: dict[str, Any] = {
            "name": name,
            "status": status,
            "updated_at": _now(),
            "image": self.relative(image) if image is not None else "",
            "prompt": self.relative(prompt) if prompt is not None else "",
            "refs": [str(path) for path in refs],
            "error": error,
        }
        if extra:
            entry.update(extra)
        replaced = False
        for index, existing in enumerate(tasks):
            if existing.get("name") == name:
                tasks[index] = entry
                replaced = True
                break
        if not replaced:
            tasks.append(entry)
        _dump(self.manifest_path, {"tasks": tasks})
        return entry
