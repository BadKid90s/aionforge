"""logo 工作区与商品工作区。

交付目录只暴露业务结构：

    output/<logo>/
      bg_white/  main/  detail/

提示词、参考图、facts、manifest、历史版本都收在 `.forge/products/<product>/`，
不污染运营浏览的三个 bucket。
"""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

BEIJING_TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")
HIDDEN_DIR = ".forge"
BUCKETS: tuple[str, ...] = ("bg_white", "main", "detail")
STORE_DIRS: tuple[str, ...] = ("refs", "tmp")
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def _now() -> str:
    return datetime.now(BEIJING_TZ).isoformat(timespec="seconds")


def _stamp() -> str:
    return datetime.now(BEIJING_TZ).strftime("%Y%m%d-%H%M%S")


def safe_slug(value: str, fallback: str = "job") -> str:
    """允许中文和常规 slug 字符；路径分隔符、点号等统一转成连字符。"""
    text = str(value or "").strip()
    slug = re.sub(r"[^\w-]+", "-", text, flags=re.UNICODE).strip("-")
    return slug or fallback


def safe_name(value: str, fallback: str = "image") -> str:
    """出图文件名只留 stem，去掉图片扩展名，避免把路径写进 bucket。"""
    text = str(value or "").strip()
    suffix = Path(text).suffix.lower()
    if suffix in _IMAGE_SUFFIXES:
        text = text[: -len(suffix)]
    return safe_slug(text, fallback)


def _dump(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def default_facts(logo: str, product: str) -> dict[str, Any]:
    """新商品的事实模板；字段与 references/contracts/facts.md 保持一致。"""
    return {
        "schema_version": 3,
        "logo": logo,
        "product": product,
        "product_name": "",
        "category": "T恤",
        "garment_position": "top",
        "input_image_type": "flat_lay",
        "visual_features": {
            "silhouette": "",
            "length": "",
            "neckline": "",
            "sleeve": "",
            "cuff": "",
            "hem": "",
            "closure": "无",
            "pockets": "无",
            "waist_hip": "直筒",
        },
        "colors": [],
        "materials_visible": [],
        "print": {
            "has_print": False,
            "source": "",
            "text_exact": "",
            "technique": "",
            "palette": [],
            "elements": [],
            "placements": [],
            "analysis": {},
            "color_adaptation": {},
        },
        "selling_points": [],
        "target_scenes": [],
        "style_lock": "",
        "conversion_driver": "pattern",
        "model": {
            "ref": "",
            "face": "",
            "eyes": "",
            "hair": "",
            "skin": "",
            "bottom": "",
            "accessories": "",
            "room_light": "",
            "uncertain": [],
        },
        "canonical": {
            "garment": "",
            "garment_back": "",
            "anchor": "",
        },
        "uncertain": [],
    }


class Workspace:
    """一个 logo 的交付工作区：三个 bucket + 隐藏的商品数据。"""

    def __init__(self, root: Path, logo: str) -> None:
        self.root = Path(root).expanduser().resolve()
        self.logo = logo
        self.hidden = self.root / HIDDEN_DIR
        self.products = self.hidden / "products"
        self.history = self.hidden / "history"

    @property
    def workspace_path(self) -> Path:
        return self.hidden / "workspace.json"

    def bucket_dir(self, bucket: str) -> Path:
        if bucket not in BUCKETS:
            raise ValueError(f"bucket 必须是 {', '.join(BUCKETS)}，收到：{bucket}")
        return self.root / bucket

    def prepare(self) -> None:
        for bucket in BUCKETS:
            self.bucket_dir(bucket).mkdir(parents=True, exist_ok=True)
        self.products.mkdir(parents=True, exist_ok=True)
        self.history.mkdir(parents=True, exist_ok=True)

    @classmethod
    def create(cls, output_root: Path, logo: str) -> Workspace:
        slug = safe_slug(logo, "logo")
        workspace = cls(Path(output_root) / slug, slug)
        workspace.prepare()
        if not workspace.workspace_path.is_file():
            _dump(
                workspace.workspace_path,
                {
                    "schema_version": 2,
                    "logo": slug,
                    "display_name": str(logo).strip(),
                    "created_at": _now(),
                    "buckets": list(BUCKETS),
                },
            )
        return workspace

    def product(self, product: str) -> Product:
        return Product(self, safe_slug(product, "product"))


class Product:
    """一个商品的工作区：facts / refs / prompts / manifest / history。"""

    def __init__(self, workspace: Workspace, name: str) -> None:
        self.workspace = workspace
        self.name = safe_slug(name, "product")
        self.root = workspace.products / self.name
        self.refs = self.root / "refs"
        self.prompts = self.root / "prompts"
        self.tmp = self.root / "tmp"
        self.history = self.root / "history"

    @property
    def project_path(self) -> Path:
        return self.root / "project.json"

    @property
    def facts_path(self) -> Path:
        return self.root / "facts.json"

    @property
    def manifest_path(self) -> Path:
        return self.root / "manifest.json"

    def prepare(self) -> None:
        self.workspace.prepare()
        self.refs.mkdir(parents=True, exist_ok=True)
        self.prompts.mkdir(parents=True, exist_ok=True)
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.history.mkdir(parents=True, exist_ok=True)

    def bucket_dir(self, bucket: str) -> Path:
        return self.workspace.bucket_dir(bucket)

    def target_path(self, bucket: str, name: str) -> Path:
        """成品路径；同名旧图先归档到商品 history，再覆盖。"""
        self.bucket_dir(bucket)
        stem = safe_name(name)
        dest = self.bucket_dir(bucket) / f"{stem}.png"
        if dest.is_file():
            backup = self.history / f"{_stamp()}-{uuid4().hex[:4]}-{dest.name}"
            shutil.copy2(dest, backup)
        return dest

    def store_path(self, store: str, name: str) -> Path:
        if store not in STORE_DIRS:
            raise ValueError(f"store 必须是 {', '.join(STORE_DIRS)}，收到：{store}")
        directory = self.refs if store == "refs" else self.tmp
        directory.mkdir(parents=True, exist_ok=True)
        dest = directory / f"{safe_name(name)}.png"
        if dest.is_file():
            backup = self.history / f"{_stamp()}-{uuid4().hex[:4]}-{dest.name}"
            shutil.copy2(dest, backup)
        return dest

    def write_prompt(
        self, name: str, text: str, *, bucket: str = "", store: str = ""
    ) -> Path:
        """Prompt 按落点分目录，避免 bg_white 和 sku 同名时互相覆盖。"""
        location = bucket or store or "misc"
        directory = self.prompts / location
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{safe_name(name)}.txt"
        path.write_text(text, encoding="utf-8")
        return path

    def relative_to_workspace(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.workspace.root))
        except ValueError:
            return str(path)

    def resolve(self, value: str | Path) -> Path:
        """解析 facts 里的相对路径：先商品根（refs/...），再 logo 根（bg_white/...）。"""
        path = Path(value).expanduser()
        if path.is_absolute():
            return path
        product_relative = self.root / path
        if product_relative.exists():
            return product_relative.resolve()
        workspace_relative = self.workspace.root / path
        if workspace_relative.exists():
            return workspace_relative.resolve()
        return product_relative.resolve()

    def facts(self) -> dict[str, Any]:
        return _load(self.facts_path)

    def write_facts(self, payload: Mapping[str, Any]) -> Path:
        return _dump(self.facts_path, payload)

    def record_task(
        self,
        name: str,
        status: str,
        *,
        bucket: str = "",
        store: str = "",
        image: Path | None = None,
        prompt: Path | None = None,
        refs: Sequence[Path] = (),
        error: str = "",
        extra: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        manifest = _load(self.manifest_path)
        tasks: list[dict[str, Any]] = list(manifest.get("tasks") or [])
        location = bucket or store or ""
        key = f"{location}/{safe_name(name)}"
        entry: dict[str, Any] = {
            "key": key,
            "name": safe_name(name),
            "status": status,
            "bucket": bucket,
            "store": store,
            "updated_at": _now(),
            "image": self.relative_to_workspace(image) if image is not None else "",
            "prompt": (
                str(prompt.resolve().relative_to(self.root)) if prompt is not None else ""
            ),
            "refs": [str(path) for path in refs],
            "error": error,
        }
        if extra:
            entry.update(extra)
        replaced = False
        for index, existing in enumerate(tasks):
            existing_key = existing.get("key") or (
                f"{existing.get('bucket') or existing.get('store') or ''}/"
                f"{existing.get('name') or ''}"
            )
            if existing_key == key:
                tasks[index] = entry
                replaced = True
                break
        if not replaced:
            tasks.append(entry)
        _dump(
            self.manifest_path,
            {
                "schema_version": 2,
                "logo": self.workspace.logo,
                "product": self.name,
                "tasks": tasks,
            },
        )
        return entry

    @classmethod
    def create(cls, workspace: Workspace, product: str) -> Product:
        instance = cls(workspace, product)
        instance.prepare()
        if not instance.project_path.is_file():
            _dump(
                instance.project_path,
                {
                    "schema_version": 2,
                    "logo": workspace.logo,
                    "product": instance.name,
                    "workspace_root": str(workspace.root),
                    "buckets": list(BUCKETS),
                    "created_at": _now(),
                },
            )
        if not instance.facts_path.is_file():
            _dump(instance.facts_path, default_facts(workspace.logo, instance.name))
        if not instance.manifest_path.is_file():
            _dump(
                instance.manifest_path,
                {
                    "schema_version": 2,
                    "logo": workspace.logo,
                    "product": instance.name,
                    "tasks": [],
                },
            )
        return instance

    @classmethod
    def open(cls, product_dir: Path) -> Product:
        root = Path(product_dir).expanduser().resolve()
        project = _load(root / "project.json")
        if not project:
            raise ValueError(
                f"商品工作区不存在或缺少 project.json：{root}。"
                "先运行 forge product init --logo <logo> --product <product>"
            )
        workspace_root = Path(str(project.get("workspace_root") or "")).expanduser()
        if not workspace_root.is_dir():
            # 工作区被移动时，按 .forge/products/<product> 反推
            try:
                workspace_root = root.parents[2]
            except IndexError as exc:
                raise ValueError(f"无法定位工作区：{root}") from exc
        workspace = Workspace(workspace_root, safe_slug(str(project.get("logo") or ""), "logo"))
        instance = cls(workspace, str(project.get("product") or root.name))
        if instance.root.resolve() != root:
            # 允许把 product 目录单独移动；以实际 product_dir 为准
            instance.root = root
            instance.refs = root / "refs"
            instance.prompts = root / "prompts"
            instance.tmp = root / "tmp"
            instance.history = root / "history"
        instance.prepare()
        return instance
