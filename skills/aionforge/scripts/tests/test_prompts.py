import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "references" / "prompts"
SKILL_DIR = ROOT.parents[1]


def test_skill_prompt_templates_exist() -> None:
    formula = (ROOT / "formula.md").read_text(encoding="utf-8")
    assert "主体" in formula
    assert "镜头语言" in formula
    for name in (
        "extract.md",
        "compose.md",
        "tryon.md",
        "vary.md",
        "sku.md",
        "infographic.md",
        "ghost-mannequin.md",
        "deconstruct.md",
    ):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "forge generate" in text
        assert "图1" not in text
        assert "图2" not in text


def test_tryon_template_uses_roles() -> None:
    text = (ROOT / "tryon.md").read_text(encoding="utf-8")
    assert "garment=" in text
    assert "model=" in text
    assert "成衣图" in text
    assert "模特图" in text


PACK_SKILLS = (
    "aionforge",
    "aionforge-extract",
    "aionforge-compose",
    "aionforge-tryon",
    "aionforge-vary",
    "aionforge-sku",
    "aionforge-deconstruct",
    "aionforge-pdp",
)
SKILLS_ROOT = SKILL_DIR.parent


def test_skill_md_links_resolve() -> None:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\nname: aionforge\n")
    for ref in re.findall(r"`(references/[^`<{]+?\.(?:md|json))`", text):
        assert (SKILL_DIR / ref).is_file(), ref


def test_pack_skills_exist_and_link_hub() -> None:
    for name in PACK_SKILLS:
        skill_md = SKILLS_ROOT / name / "SKILL.md"
        text = skill_md.read_text(encoding="utf-8")
        assert text.startswith(f"---\nname: {name}\n"), name
        if name == "aionforge":
            for sibling in PACK_SKILLS[1:]:
                assert f"`{sibling}`" in text, sibling
            continue
        assert "../aionforge/SKILL.md" in text
        for ref in re.findall(r"`(\.\./aionforge/references/[^`<{]+?\.(?:md|json))`", text):
            assert (SKILLS_ROOT / name / ref).resolve().is_file(), f"{name}: {ref}"


def test_vary_and_compose_templates_use_roles() -> None:
    vary = (ROOT / "vary.md").read_text(encoding="utf-8")
    assert "source=" in vary
    assert "人物锁定" in vary
    assert "服装锁定" in vary
    assert "looks.json" in vary
    assert "把头钉死" in vary
    tryon = (ROOT / "tryon.md").read_text(encoding="utf-8")
    assert "眼部细节" in tryon or "眼神光" in tryon
    compose = (ROOT / "compose.md").read_text(encoding="utf-8")
    assert "print=" in compose
    assert "garment=" in compose
    sku = (ROOT / "sku.md").read_text(encoding="utf-8")
    assert "source=" in sku
    assert "garment=" in sku
    assert "sku-" in sku
    assert "图1" not in sku


def test_infographic_and_deconstruct_templates_have_visible_text_block() -> None:
    info = (ROOT / "infographic.md").read_text(encoding="utf-8")
    assert "VISIBLE_TEXT_BLOCK" in info
    assert "garment_back" in info
    deconstruct = (ROOT / "deconstruct.md").read_text(encoding="utf-8")
    assert "VISIBLE_TEXT_BLOCK" in deconstruct
    assert "layout=" in deconstruct


def test_evals_json_files_valid() -> None:
    evals_dir = SKILL_DIR / "evals"
    trigger = json.loads((evals_dir / "trigger_cases.json").read_text(encoding="utf-8"))
    behavior = json.loads((evals_dir / "behavior_cases.json").read_text(encoding="utf-8"))
    assert len(trigger["cases"]) >= 6
    assert len(behavior["cases"]) >= 4
