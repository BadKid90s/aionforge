"""平面印花 logo 的 AI 提取：模型清洗白底，本地生成透明通道。

模型只负责语义判断——哪些白色是背景残留、哪些白色属于图案内部；alpha 仍由
本地 flood fill 生成，避免依赖模型直接输出透明图，也避免把文字和形状重画两遍。
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from aionforge.core.images import cutout_background, flatten_to_rgb
from aionforge.run.workspace import Product, safe_name
from aionforge.tools.generate import ImageEditor

LOGO_EXTRACT_PROMPT = """# Role: 平面印花图案提取

把参考图中的平面印花图案完整提取到纯白背景上。只清理背景，不重新设计。

## Rules
1. 图案的形状、颜色、文字、字体、笔画、粗细、比例和相对位置必须与参考图一致。
   逐字保留，禁止重画、改字、补字、简化或美化。
2. 去掉图案外围的白色背景、白边、白色残留和半透明白色光晕。
3. 保留图案内部本来就属于设计的白色：白色文字、白色描边、白色高光、
   眼睛留白、图案内部的白色块。判断标准是它在图案轮廓内部，而不是图案外围的底色。
4. 输出纯白 #FFFFFF 背景，不要灰色、米色、棋盘格或透明棋盘格。
5. 图案完整居中，四周留少量白边，不裁掉任何笔画、描边或装饰。
6. 不要输出衣服、模特、衣架、吊牌、场景或任何背景杂物。
   不要添加阴影、渐变、材质、水印、二维码或说明文字。
7. 只输出一张图片，不要拼图。
"""


def _normalize_model_output(source: Path, dest: Path) -> Path:
    """模型返回的可能是 JPEG 字节或带 alpha 的 PNG，统一铺白底存成 PNG。"""
    with Image.open(source) as image:
        flatten_to_rgb(image, "white").save(dest, format="PNG")
    return dest


async def run_logo_extract(
    source: Path,
    product: Product,
    image: ImageEditor,
    *,
    name: str = "print",
    padding: int = 8,
    threshold: int = 238,
    tolerance: int = 18,
    remove_enclosed_white: bool = False,
    denoise: int = 0,
    prompt: str = LOGO_EXTRACT_PROMPT,
) -> Path:
    """用图片模型清洗平面 logo 稿，再本地抠成透明 PNG。"""
    if not prompt.strip():
        raise ValueError("prompt 不能为空")
    padding = max(padding, 0)
    threshold = min(max(int(threshold), 0), 255)
    tolerance = min(max(int(tolerance), 0), 255)
    denoise = max(int(denoise), 0)
    stem = safe_name(name)
    staged = product.tmp / f"{stem}-extract-in.png"
    product.tmp.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as source_image:
        flatten_to_rgb(source_image, "white").save(staged, format="PNG")
    model_output = product.tmp / f"{stem}-extract-model.png"
    cleaned = product.tmp / f"{stem}-extract-cleaned.png"
    await image.edit(prompt, [staged], model_output)
    _normalize_model_output(model_output, cleaned)
    cutout_background(
        cleaned,
        padding=padding,
        threshold=threshold,
        tolerance=tolerance,
        remove_enclosed_white=remove_enclosed_white,
        denoise=denoise,
    )
    dest = product.store_path("refs", name)
    dest.write_bytes(cleaned.read_bytes())
    prompt_path = product.write_prompt(name, prompt, store="refs")
    product.record_task(
        name,
        "ok",
        store="refs",
        image=dest,
        prompt=prompt_path,
        refs=[source],
        extra={
            "mode": "ai-cutout",
            "source": str(source),
            "raw": str(model_output),
            "cleaned": str(cleaned),
            "threshold": threshold,
            "tolerance": tolerance,
            "remove_enclosed_white": remove_enclosed_white,
            "denoise": denoise,
        },
    )
    return dest
