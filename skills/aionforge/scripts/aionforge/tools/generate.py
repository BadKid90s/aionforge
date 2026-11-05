from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from aionforge.core.images import (
    FitMode,
    cutout_background,
    fit_image,
    needs_expand,
    prepare_expand_canvas,
    target_size,
)
from aionforge.run.job import Job

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


def stage_refs(job: Job, refs: Sequence[Ref]) -> list[Path]:
    """有角色名的参考图复制为 work/refs/<role>.<ext>，让图片模型看见文件名。"""
    staged: list[Path] = []
    refs_dir = job.work / "refs"
    for item in refs:
        if not item.role:
            staged.append(item.path)
            continue
        dest = refs_dir / f"{item.role}{item.path.suffix.lower()}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(item.path.read_bytes())
        staged.append(dest)
    return staged


async def run_generate(
    prompt: str,
    refs: Sequence[Ref],
    job: Job,
    image: ImageEditor,
    *,
    name: str,
    ratio: str | None = None,
    fit: FitMode | str = FitMode.expand,
    cutout: bool = False,
    padding: int = 8,
) -> Path:
    if not prompt.strip():
        raise ValueError("prompt 不能为空")
    dest = job.image_path(name)
    prompt_path = job.write_prompt(name, prompt)
    staged = stage_refs(job, refs)
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
        saved = await _apply_ratio(saved, ratio, mode, image, job, name)
    job.record_task(
        name,
        "ok",
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
    job: Job,
    name: str,
) -> Path:
    size = target_size(ratio)
    if mode is FitMode.crop or not needs_expand(path, ratio):
        return fit_image(path, size, FitMode.crop)
    canvas = job.work / f"{name}-expand-in.png"
    prepare_expand_canvas(path, canvas, size)
    await image.edit(EXPAND_PROMPT.format(ratio=ratio), [canvas], path)
    return fit_image(path, size, FitMode.crop)
