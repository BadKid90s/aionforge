import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "references" / "prompts"


def test_skill_prompt_templates_exist() -> None:
    for name in ("extract.md", "compose.md", "tryon.md", "vary.md"):
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


def test_skill_md_links_resolve() -> None:
    skill = ROOT.parents[1]
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\nname: aionforge\n")
    for ref in re.findall(r"`(references/[^`<{]+?\.(?:md|json))`", text):
        assert (skill / ref).is_file(), ref


def test_vary_and_compose_templates_use_roles() -> None:
    vary = (ROOT / "vary.md").read_text(encoding="utf-8")
    assert "source=" in vary
    assert "人物锁定" in vary
    assert "服装锁定" in vary
    assert "本张机位与姿势" in vary
    assert "把头钉死" in vary
    tryon = (ROOT / "tryon.md").read_text(encoding="utf-8")
    assert "眼部细节" in tryon or "眼神光" in tryon
    compose = (ROOT / "compose.md").read_text(encoding="utf-8")
    assert "print=" in compose
    assert "garment=" in compose
