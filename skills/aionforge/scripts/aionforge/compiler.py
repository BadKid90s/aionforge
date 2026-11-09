"""按公式组装生图 Prompt 并做静态校验。

组段顺序见 `references/prompts/formula.md`：
用途 → 主体（Garment Facts Lock）→ 场景 → 风格（Campaign Style Lock）
→ 镜头语言 → 氛围与细节 → 参考图角色 → VISIBLE_TEXT_BLOCK → 约束。
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

_FORBIDDEN_INDEX_RE = re.compile(r"图\s*[1-9一二三四五六七八九]")
_HEX_RE = re.compile(r"#[0-9A-Fa-f]{6}\b")

ROLE_LABELS: dict[str, str] = {
    "garment": "成衣图（garment，唯一正面商品事实源）",
    "garment_front": "正面成衣图（garment_front，正面商品事实源）",
    "garment_back": "背面成衣图（garment_back，后背结构与下摆事实源）",
    "model": "模特图（model，人物五官、眼型与眼神光锁定源）",
    "print": "印花图（print，图案与字母逐字还原源）",
    "source": "锚点成片（source，跨镜头同一模特与场景参考源）",
    "style": "风格参考图（style，仅借光线与色调，严禁复制其服装款式与文字）",
    "layout": "版式参考图（layout，仅借构图网格与留白比例，严禁复制其服装款式、人脸与品牌 Logo）",
    "pose": "姿势参考图（pose，只借身体姿态、手脚与头朝向；五官跟模特图或成片，衣服跟成衣图）",
}


def compile_garment_facts(facts: dict[str, Any]) -> str:
    """将 facts.json 编译为确定性的服装事实锁定段落。"""
    lines: list[str] = ["【商品事实锁定（Garment Facts Lock）】"]
    category = facts.get("category") or "女装成衣"
    position = facts.get("garment_position") or "full_body"
    lines.append(f"- 品类与部位：{category}（{position}）")

    vf = facts.get("visual_features") or {}
    feature_parts: list[str] = []
    for key, label in (
        ("silhouette", "廓形"),
        ("length", "衣长/裙长"),
        ("neckline", "领口"),
        ("sleeve", "袖型与袖口"),
        ("hem", "下摆"),
        ("closure", "门襟/扣链"),
        ("pockets", "口袋"),
        ("waist_hip", "腰臀剪裁"),
    ):
        val = vf.get(key)
        if val:
            feature_parts.append(f"{label}：{val}")
    if feature_parts:
        lines.append("- 结构细节：" + "；".join(feature_parts))

    colors = facts.get("colors") or []
    materials = facts.get("materials_visible") or []
    if colors or materials:
        lines.append(
            f"- 颜色与可见材质：颜色为 {'、'.join(colors) or '按成衣图'}；"
            f"材质肌理为 {'、'.join(materials) or '按成衣图真实织物纹理'}"
        )

    print_info = facts.get("print") or {}
    if print_info.get("has_print"):
        text_exact = print_info.get("text_exact") or ""
        placement = print_info.get("placement") or "按成衣图位置"
        technique = print_info.get("technique") or "清晰平整印制"
        lines.append(
            f"- 印花锁定：位置在{placement}，工艺为{technique}；"
            f"图案文字逐字严格为「{text_exact}」，只印一次，禁止拼写变形或镜像翻转"
        )
    else:
        lines.append("- 印花锁定：纯色无印花，禁止凭空添加任何图案、字母或胸标")

    if position == "top":
        lines.append(
            "- 合理搭配补全：主商品为上装，下装搭配低饱和极简基础款裤装或半裙，不抢上装焦点"
        )
    elif position == "bottom":
        lines.append(
            "- 合理搭配补全：主商品为下装，上衣搭配修身纯色基础款并塞衣角，完整露出腰头与版型"
        )

    uncertain = facts.get("uncertain") or []
    if uncertain:
        joined = "、".join(uncertain)
        lines.append(
            f"- 未知部位禁令（Uncertain）：{joined} 在原图中不可见，严禁凭空捏造装饰或复杂结构"
        )
    return "\n".join(lines)


def compile_reference_roles(roles: Sequence[str]) -> str:
    """将参考图角色列表编译为素材角色说明段落。"""
    lines = ["【参考图角色与隔离契约】"]
    if not roles:
        lines.append("- 本张为无参考图生成，完全依据下方商品事实与构图指令绘制。")
        return "\n".join(lines)
    for role in roles:
        desc = ROLE_LABELS.get(role, f"{role} 参考图")
        lines.append(f"- {desc}")
    if "model" in roles or "source" in roles:
        lines.append(
            "- 人物一致性铁律：保留参考人物的眼型、瞳色、双眼皮、眼神光与五官比例，"
            "但头部朝向、颈部与视线必须随本张姿势自然转动，不要把头钉死在原图角度。"
        )
    return "\n".join(lines)


def compile_visible_text_block(
    *,
    typography_prompt: str = "",
    headline: str = "",
    subheadline: str = "",
    badges: Sequence[str] = (),
) -> str:
    """编译画面内印字隔离块（VISIBLE_TEXT_BLOCK）或无字声明。"""
    has_any = bool(headline.strip() or subheadline.strip() or badges)
    if not has_any:
        return (
            "【VISIBLE_TEXT_BLOCK（纯视觉无字模式）】\n"
            "- 画面内禁止出现任何文字、字母、水印、价格签、促销角标或品牌 Logo。"
        )
    lines = ["【VISIBLE_TEXT_BLOCK（画面内仅允许渲染以下「」内的文字）】"]
    if typography_prompt.strip():
        lines.append(f"- 平台排版美学：{typography_prompt.strip()}")
    if headline.strip():
        lines.append(f"- 主标题：「{headline.strip()}」")
    if subheadline.strip():
        lines.append(f"- 副标题：「{subheadline.strip()}」")
    if badges:
        quoted = " ".join(f"「{b.strip()}」" for b in badges if b.strip())
        lines.append(f"- 卖点胶囊/批注标签：{quoted}")
    lines.append(
        "- 印字铁律：画面中仅允许出现上述「」内的文字，笔画清晰锐利；"
        "严禁把字重、字号、Hex 色号、对齐方式等排版元指令文字渲染进画面。"
    )
    return "\n".join(lines)


def compile_prompt(
    *,
    shot_title: str,
    style_lock: str,
    facts: dict[str, Any],
    roles: Sequence[str],
    shot_delta: str,
    garment_scale: str = "主体占画面 70%–80%，保留 20%–30% 干净呼吸留白",
    scene: str = "",
    typography_prompt: str = "",
    headline: str = "",
    subheadline: str = "",
    badges: Sequence[str] = (),
    anti_ai_tips: str = (
        "85mm 定焦镜头质感，真实织物经纬线与自然垂坠重力褶皱，真实皮肤微纹理，拒绝塑料磨皮感。"
    ),
) -> str:
    """按 formula.md 组段顺序组装生图 Prompt。"""
    scene_line = scene.strip() or (
        "场景与空间按风格锁定及参考图（成片 / 模特图）还原，不要另起一套房间。"
    )
    sections = [
        f"一张女装电商视觉图：{shot_title.strip()}。",
        compile_garment_facts(facts),
        f"【场景】\n- {scene_line}",
        f"【风格（Campaign Style Lock）】\n- {style_lock.strip()}",
        (
            "【镜头语言】\n"
            f"- 画面占比与留白：{garment_scale.strip()}\n"
            f"- 机位与姿态：{shot_delta.strip()}"
        ),
        f"【氛围与细节】\n- {anti_ai_tips.strip()}",
        compile_reference_roles(roles),
        compile_visible_text_block(
            typography_prompt=typography_prompt,
            headline=headline,
            subheadline=subheadline,
            badges=badges,
        ),
        (
            "【约束】\n"
            "- 只输出一张照片。无水印、无边框、无拼图。\n"
            "- 用成衣图 / 模特图 / 印花图 / 锚点成片指代参考图，不要写图序号。"
        ),
    ]
    return "\n\n".join(sections) + "\n"


def validate_prompt_text(prompt: str, *, has_visible_text: bool = False) -> list[str]:
    """静态检查生图 Prompt 是否违反核心底线，返回问题列表（空列表表示通过）。"""
    issues: list[str] = []
    if _FORBIDDEN_INDEX_RE.search(prompt):
        issues.append(
            "禁止使用「图1 / 图2」指代参考图，请改用「成衣图 / 模特图 / 印花图 / 锚点成片」"
        )
    if not _HEX_RE.search(prompt):
        issues.append("Style Lock 缺少 6 位 Hex 色号（如 #F7F5F2）")
    if has_visible_text:
        if "VISIBLE_TEXT_BLOCK" not in prompt:
            issues.append("含画面内文字的 Prompt 必须包含 VISIBLE_TEXT_BLOCK 隔离块")
        if "「" not in prompt or "」" not in prompt:
            issues.append("VISIBLE_TEXT_BLOCK 中的待渲染文字必须用「...」包裹")
    return issues
