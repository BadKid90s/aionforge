"""生图 Prompt 的静态底线检查。

只检查能确定性判断的内容：参考图指代方式、Style Lock 色号、图内文字隔离块、
印花原文是否逐字进入 Prompt。审美与事实一致性仍由宿主 Agent 看图质检。
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

_FORBIDDEN_INDEX_RE = re.compile(r"图\s*[1-9一二三四五六七八九]")
_HEX_RE = re.compile(r"#[0-9A-Fa-f]{6}\b")


def validate_prompt_text(
    prompt: str,
    *,
    has_visible_text: bool = False,
    facts: Mapping[str, Any] | None = None,
) -> list[str]:
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

    if facts:
        print_info = facts.get("print") or {}
        if print_info.get("has_print"):
            text_exact = str(print_info.get("text_exact") or "").strip()
            if text_exact and text_exact not in prompt:
                issues.append(f"印花原文「{text_exact}」没有逐字出现在 Prompt 中")
    return issues
