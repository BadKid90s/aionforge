"""印花核心元素的 AI 语义提取：输出一枚完整、闭合、可独立使用的图标。

与按 alpha 连通域拆碎片（会把一朵花拆成几十个碎片）不同，这里让图片模型理解
「哪个元素可以独立成立」，把它单独画到纯白底上；透明通道仍由本地 flood fill
生成，保证边缘干净、白色设计元素不被误挖。

由 CLI 一等命令 `forge extract-core-element` 调用；该命令始终走图片模型，
不做连通域拆分，也不静默回落本地。典型用途：后背大图配一枚左胸心口小标。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageChops

from aionforge.core.images import cutout_background, flatten_to_rgb
from aionforge.run.workspace import Product, safe_name
from aionforge.tools.generate import ImageEditor

DEFAULT_ELEMENT_HINT = (
    "从参考图案中选出轮廓最完整、最适合单独缩小成小尺寸图标的那一个视觉元素"
    "（优先图形/图标/符号，而不是一整行文字）"
)

ELEMENT_EXTRACT_PROMPT = """# Role: 服装印花核心元素提取（左胸心口小标）

把参考印花稿中的【一个】核心视觉元素，单独提取成一枚完整、独立、可缩小的图标。

## 目标元素
{element_hint}

## Rules
1. 只保留上述【一个】元素。彻底删除参考图里的其余全部内容：
   所有其他文字、字母、数字、标语、边框、装饰、星星、底纹、背景色块。
   不要因为它们在原图里离得近就把它们带进来。
2. 元素必须轮廓闭合、完整无裁切，四周留足白色留白（元素约占画面 60-75%），
   任何笔画、描边、装饰都不能被画框切断。
3. 形状、颜色、线条粗细、手绘笔触、涂鸦质感、明暗和表情必须与参考图一致。
   不要重新设计、不要美化、不要简化、不要补全、不要改成别的风格。
4. 不要新增任何文字、字母、数字、水印、二维码或说明标签。
   原元素内部本来就带的字（例如徽章里的字母）可以原样保留。
5. 纯白 #FFFFFF 干净背景，平面 2D 印花稿，正面平视，无透视。
   不要渐变背景、阴影、立体感、布料、模特、衣服、吊牌或场景杂物。
6. 元素居中，正方形构图。只输出一张图片，不要拼图，不要多个变体。
"""

# 元素离画布边缘至少留这么多比例，才认为没被画框裁断
_MIN_MARGIN_RATIO = 0.02


def _content_bbox(image: Image.Image, *, tolerance: int = 12) -> tuple[int, int, int, int] | None:
    """在纯白底图上找非白内容的包围盒（不依赖 numpy）。"""
    rgb = image.convert("RGB")
    white = Image.new("RGB", rgb.size, (255, 255, 255))
    diff = ImageChops.difference(rgb, white).convert("L")
    mask = diff.point(lambda value: 255 if value > tolerance else 0)
    return mask.getbbox()


def _completeness(image: Image.Image) -> dict[str, Any]:
    """检查模型输出的元素是否完整闭合、四周留白充足。"""
    width, height = image.size
    bbox = _content_bbox(image)
    if bbox is None:
        return {"complete": False, "reason": "模型输出为空白", "bbox": None, "margin_ratio": 0.0}
    x0, y0, x1, y1 = bbox
    margin = min(x0, y0, width - x1, height - y1)
    ratio = margin / max(1, min(width, height))
    complete = ratio >= _MIN_MARGIN_RATIO
    return {
        "complete": complete,
        "reason": "" if complete else "元素贴到画布边缘，可能被裁断",
        "bbox": [x0, y0, x1, y1],
        "margin_ratio": round(ratio, 4),
    }


def _normalize_model_output(source: Path, dest: Path) -> Path:
    """模型可能返回 JPEG 字节或带 alpha 的 PNG，统一铺白底存成 PNG。"""
    with Image.open(source) as image:
        flatten_to_rgb(image, "white").save(dest, format="PNG")
    return dest


async def run_element_extract(
    source: Path,
    product: Product,
    image: ImageEditor,
    *,
    name: str = "core-element",
    element_hint: str = "",
    padding: int = 12,
    denoise: int = 4,
    threshold: int = 238,
    tolerance: int = 18,
    prompt_template: str = ELEMENT_EXTRACT_PROMPT,
) -> tuple[Path, dict[str, Any]]:
    """用图片模型提取一枚完整独立元素，返回 (透明底 PNG 路径, 质检元信息)。"""
    hint = (element_hint or "").strip() or DEFAULT_ELEMENT_HINT
    prompt = prompt_template.format(element_hint=hint)
    stem = safe_name(name)
    product.tmp.mkdir(parents=True, exist_ok=True)

    staged = product.tmp / f"{stem}-element-in.png"
    with Image.open(source) as source_image:
        flattened = flatten_to_rgb(source_image, "white")
        # 限制输入边长，避免大稿撑爆 multipart 请求体
        if max(flattened.size) > 1536:
            flattened.thumbnail((1536, 1536), Image.Resampling.LANCZOS)
        flattened.save(staged, format="PNG")

    model_output = product.tmp / f"{stem}-element-model.png"
    cleaned = product.tmp / f"{stem}-element-cleaned.png"
    await image.edit(prompt, [staged], model_output)
    _normalize_model_output(model_output, cleaned)

    with Image.open(cleaned) as check:
        quality = _completeness(check.convert("RGB"))

    cutout_background(
        cleaned,
        padding=max(0, int(padding)),
        threshold=threshold,
        tolerance=tolerance,
        remove_enclosed_white=False,  # 保护白色花瓣、白色字标等设计白墨
        denoise=max(0, int(denoise)),
    )
    dest = product.store_path("refs", name)
    dest.write_bytes(cleaned.read_bytes())
    prompt_path = product.write_prompt(name, prompt, store="refs")

    meta: dict[str, Any] = {
        "mode": "ai-element",
        "source": str(source),
        "element_hint": hint,
        "complete": quality["complete"],
        "complete_reason": quality["reason"],
        "content_bbox": quality["bbox"],
        "margin_ratio": quality["margin_ratio"],
        "raw": str(model_output),
        "padding": padding,
        "denoise": denoise,
    }
    product.record_task(
        name,
        "ok",
        store="refs",
        image=dest,
        prompt=prompt_path,
        refs=[source],
        extra={**meta, "cleaned": str(cleaned)},
    )
    return dest, meta
