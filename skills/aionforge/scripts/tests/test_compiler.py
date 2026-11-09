from aionforge.compiler import compile_prompt, validate_prompt_text


def test_compile_prompt_five_layers_and_validate() -> None:
    facts = {
        "category": "法式收腰短袖连衣裙",
        "garment_position": "top",
        "visual_features": {
            "silhouette": "微收腰 A 字",
            "length": "中长款过膝",
            "neckline": "法式方领",
            "sleeve": "泡泡短袖，窄边平口",
            "hem": "自然散摆",
        },
        "colors": ["暖杏白 #F7F5F2"],
        "materials_visible": ["哑光醋酸垂感面料"],
        "print": {
            "has_print": True,
            "text_exact": "LUMIERE",
            "placement": "左胸上方",
            "technique": "细密刺绣",
        },
        "uncertain": ["后背隐形拉链头部样式"],
    }
    prompt = compile_prompt(
        shot_title="G1 首屏主视觉（main-hero）",
        style_lock="5200K 柔和棚拍主光，主背景为 #F7F5F2 暖米灰，次背景为 #EFECE6 燕麦米",
        facts=facts,
        roles=["garment", "model"],
        shot_delta="平视七分身，青年女性自然站立，双臂放松垂在身侧，眼神柔和看镜头。",
        typography_prompt="清透莫兰迪胶囊轻杂志风，主标题正体黑体 #2D2D2D 无描边",
        headline="醋酸垂感 高腰显瘦",
        badges=["法式方领", "不易起皱"],
    )
    assert "Campaign Style Lock" in prompt
    assert "Garment Facts Lock" in prompt
    assert "【场景】" in prompt
    assert "【镜头语言】" in prompt
    assert "【氛围与细节】" in prompt
    assert "【约束】" in prompt
    assert "LUMIERE" in prompt
    assert "合理搭配补全" in prompt
    assert "后背隐形拉链头部样式" in prompt
    assert "VISIBLE_TEXT_BLOCK" in prompt
    assert "「醋酸垂感 高腰显瘦」" in prompt
    assert validate_prompt_text(prompt, has_visible_text=True) == []


def test_validate_prompt_text_catches_errors() -> None:
    bad_prompt = "参考图1的衣服和图2的模特，背景用米白色，写上显瘦百搭。"
    issues = validate_prompt_text(bad_prompt, has_visible_text=True)
    assert len(issues) == 4
