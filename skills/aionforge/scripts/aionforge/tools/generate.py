from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from PIL import Image

from aionforge.core.images import (
    FitMode,
    cutout_background,
    fit_image,
    needs_expand,
    prepare_expand_canvas,
    target_size,
)
from aionforge.run.workspace import Product

EXPAND_PROMPT = """# Role: 画面扩图

把参考图扩展到 {ratio}，铺满整个画布。

## Rules
1. 原图主体、人脸、服装、印花、构图中心保持不变。
2. 只向缺口方向延伸场景、地面、墙面或棚拍背景，内容和光线必须接上原图。
3. 画面必须铺满 {ratio}，禁止白边、黑边、模糊填充条、letterbox、pillarbox。
4. 不要添加第二个人、不要改衣服、不要加水印。
"""

_ROLE_REF = re.compile(r"^([a-z][a-z0-9_]*)=(.+)$", re.IGNORECASE)


@dataclass(frozen=True)
class Ref:
    path: Path
    role: str | None = None


class ImageEditor(Protocol):
    async def edit(self, prompt: str, images: Sequence[Path], output: Path) -> Path: ...

    async def generate(self, prompt: str, output: Path) -> Path: ...


def parse_ref(raw: str) -> Ref:
    text = raw.strip()
    match = _ROLE_REF.match(text)
    if match:
        role, path_s = match.group(1).lower(), match.group(2)
        path = Path(path_s).expanduser()
    else:
        role, path = None, Path(text).expanduser()
    if not path.is_file():
        raise ValueError(f"参考图不存在：{path}")
    return Ref(path=path.resolve(), role=role)


def _flatten_for_api(source: Path, dest: Path) -> Path:
    """把透明参考图铺到白底再传给模型。

    不少网关会把带 alpha 的参考图压成黑底，模型随即把黑色当成画面背景，
    导致白底商品图变成黑底。铺白底既保留图案，也避免这种背景偏移。
    """
    with Image.open(source) as img:
        if "A" not in img.getbands():
            dest.write_bytes(source.read_bytes())
            return dest
        rgba = img.convert("RGBA")
        canvas = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        Image.alpha_composite(canvas, rgba).convert("RGB").save(dest, format="PNG")
    return dest


def stage_refs(product: Product, refs: Sequence[Ref]) -> list[Path]:
    """有角色名的参考图复制为 refs/<role>.<ext>（同角色多张加序号），让图片模型看见文件名。"""
    staged: list[Path] = []
    role_counts: dict[str, int] = {}
    for item in refs:
        if not item.role:
            staged.append(item.path)
            continue
        count = role_counts.get(item.role, 0) + 1
        role_counts[item.role] = count
        stem = item.role if count == 1 else f"{item.role}_{count}"
        dest = product.refs / f"{stem}{item.path.suffix.lower()}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        _flatten_for_api(item.path, dest)
        staged.append(dest)
    return staged


async def run_generate(
    prompt: str,
    refs: Sequence[Ref],
    product: Product,
    image: ImageEditor,
    *,
    name: str,
    bucket: str | None = None,
    store: str | None = None,
    ratio: str | None = None,
    fit: FitMode | str = FitMode.expand,
    cutout: bool = False,
    padding: int = 8,
    background: str = "white",
) -> Path:
    if not prompt.strip():
        raise ValueError("prompt 不能为空")
    if bool(bucket) == bool(store):
        raise ValueError("--bucket 与 --store 必须二选一：成品用 bucket，中间产物用 store")
    dest = product.target_path(bucket, name) if bucket else product.store_path(store or "", name)
    prompt_path = product.write_prompt(
        name, prompt, bucket=bucket or "", store=store or ""
    )
    staged = stage_refs(product, refs)
    mode = FitMode(fit) if not isinstance(fit, FitMode) else fit
    if mode is FitMode.pad:
        mode = FitMode.expand
    if staged:
        saved = await image.edit(prompt, staged, dest)
    else:
        saved = await image.generate(prompt, dest)
    if cutout:
        cutout_background(saved, padding=padding)
    elif ratio:
        saved = await _apply_ratio(saved, ratio, mode, image, product, name, background)
    product.record_task(
        name,
        "ok",
        bucket=bucket or "",
        store=store or "",
        image=saved,
        prompt=prompt_path,
        refs=[item.path for item in refs],
        extra={
            "ratio": ratio or "",
            "fit": str(mode),
            "cutout": cutout,
            "roles": [item.role or "" for item in refs],
        },
    )
    return saved


async def _apply_ratio(
    path: Path,
    ratio: str,
    mode: FitMode,
    image: ImageEditor,
    product: Product,
    name: str,
    background: str = "white",
) -> Path:
    size = target_size(ratio)
    if mode is FitMode.crop or not needs_expand(path, ratio):
        return fit_image(path, size, FitMode.crop, background=background)
    canvas = product.tmp / f"{name}-expand-in.png"
    prepare_expand_canvas(path, canvas, size)
    await image.edit(EXPAND_PROMPT.format(ratio=ratio), [canvas], path)
    return fit_image(path, size, FitMode.crop, background=background)
