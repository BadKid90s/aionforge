from aionforge.core.prompt_check import validate_prompt_text


def test_validate_prompt_text_accepts_good_prompt() -> None:
    prompt = (
        "背景 #F7F5F2，成衣图为唯一标准。"
        "【VISIBLE_TEXT_BLOCK】主标题：「醋酸垂感」"
    )
    assert (
        validate_prompt_text(
            prompt,
            has_visible_text=True,
            facts={"print": {"has_print": True, "text_exact": "醋酸垂感"}},
        )
        == []
    )


def test_validate_prompt_text_catches_errors() -> None:
    bad_prompt = "参考图1的衣服和图2的模特，背景用米白色，写上显瘦百搭。"
    issues = validate_prompt_text(bad_prompt, has_visible_text=True)
    assert len(issues) == 4


def test_validate_prompt_text_requires_exact_print_text() -> None:
    issues = validate_prompt_text(
        "背景 #FFFFFF，胸前印花。",
        facts={"print": {"has_print": True, "text_exact": "LOVE"}},
    )
    assert any("LOVE" in issue for issue in issues)
