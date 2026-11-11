import re
from pathlib import Path

from aionforge.run.workspace import default_facts

SKILLS_ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = SKILLS_ROOT / "aionforge"
TOOLS_DIR = SKILL_DIR / "references" / "tools"
CONTRACTS_DIR = SKILL_DIR / "references" / "contracts"

ALLOWED_FRONTMATTER = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
COMMAND_RE = re.compile(r"\bforge\s+[a-z]")
FLAG_RE = re.compile(r"--[a-z][a-z-]+")
LINK_RE = re.compile(r"\]\(([^)]+)\)")


def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---\n", 4)
    if end == -1:
        return "", text
    return text[4:end], text[end + 5 :]


def _yaml_value(raw: str, key: str) -> str:
    lines = raw.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith(f"{key}:"):
            continue
        value = line.split(":", 1)[1].strip()
        if value in {"|", ">", "|-", ">-", "|+", ">+"}:
            parts: list[str] = []
            for continuation in lines[index + 1 :]:
                if continuation.startswith((" ", "\t")):
                    parts.append(continuation.strip())
                else:
                    break
            return " ".join(parts)
        return value.strip("\"'")
    return ""


def _skills() -> list[Path]:
    return sorted(path for path in SKILLS_ROOT.iterdir() if (path / "SKILL.md").is_file())


def test_skill_frontmatter_follows_spec() -> None:
    for skill in _skills():
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        raw, body = _split_frontmatter(text)
        assert raw, skill.name
        keys = {
            line.split(":", 1)[0].strip()
            for line in raw.splitlines()
            if line and not line.startswith((" ", "\t"))
        }
        assert keys <= ALLOWED_FRONTMATTER, (skill.name, keys)
        name = _yaml_value(raw, "name")
        description = _yaml_value(raw, "description")
        assert name == skill.name, skill.name
        assert NAME_RE.fullmatch(name), name
        assert 1 <= len(description) <= 1024, (skill.name, len(description))
        assert len(body.splitlines()) <= 500, skill.name


def test_flow_skills_have_no_cli_syntax() -> None:
    for skill in _skills():
        if skill.name == "aionforge":
            continue
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        _, body = _split_frontmatter(text)
        assert "```bash" not in body, skill.name
        assert not COMMAND_RE.search(body), skill.name
        assert not FLAG_RE.search(body), skill.name


def test_flow_skills_follow_four_step_loop() -> None:
    for skill in _skills():
        if skill.name == "aionforge":
            continue
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        _, body = _split_frontmatter(text)
        for step in ("思考", "事实锁定", "生成", "检查"):
            assert step in body, (skill.name, step)


def test_entry_lists_all_flows() -> None:
    entry = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    for skill in _skills():
        if skill.name == "aionforge":
            continue
        assert f"`{skill.name}`" in entry, skill.name


def test_tool_cards_are_complete_and_indexed() -> None:
    cards = sorted(TOOLS_DIR.glob("*.md"))
    card_names = {card.name for card in cards if card.name != "index.md"}
    index = (TOOLS_DIR / "index.md").read_text(encoding="utf-8")
    linked: set[str] = set()
    for target in LINK_RE.findall(index):
        if not target.endswith(".md"):
            continue
        resolved = (TOOLS_DIR / target).resolve()
        if resolved.parent == TOOLS_DIR.resolve():
            linked.add(resolved.name)
    assert linked == card_names, (linked, card_names)

    required = (
        "| command |",
        "## 参数",
        "## 输出",
        "## 保证",
        "## 不适用",
        "## 失败与处置",
        "## 标准调用",
    )
    for card in cards:
        if card.name == "index.md":
            continue
        text = card.read_text(encoding="utf-8")
        assert not text.startswith("---\n"), card.name
        for heading in required:
            assert heading in text, (card.name, heading)


def test_relative_markdown_links_resolve() -> None:
    paths = list((SKILL_DIR / "references").rglob("*.md"))
    paths += [skill / "SKILL.md" for skill in _skills()]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for target in LINK_RE.findall(text):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            if target.endswith("/"):
                continue
            target_path = (path.parent / target.split("#", 1)[0]).resolve()
            assert target_path.exists(), f"{path}: {target}"


def test_facts_schema_version_is_v3() -> None:
    assert default_facts("logo", "product")["schema_version"] == 3
    facts = (CONTRACTS_DIR / "facts.md").read_text(encoding="utf-8")
    assert '"schema_version": 3' in facts


def test_legacy_design_is_removed() -> None:
    assert not (SKILL_DIR / "scripts" / "aionforge" / "core" / "elements.py").exists()
    assert not (SKILL_DIR / "references" / "facts.md").exists()
    assert not (SKILL_DIR / "references" / "pipeline.md").exists()
    assert not (TOOLS_DIR / "extract-element.md").exists()
    index = (TOOLS_DIR / "index.md").read_text(encoding="utf-8")
    assert "extract-element" not in index
