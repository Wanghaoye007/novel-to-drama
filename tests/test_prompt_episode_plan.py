from novel_drama_engine import prompts
from novel_drama_engine.demo import demo_round_outputs


def test_episode_plan_system_limits_output_to_drama_engineering():
    system_prompt = prompts.EPISODE_PLAN_SYSTEM

    assert "只做单集戏剧工程设计" in system_prompt
    assert "不写正片脚本" in system_prompt
    assert "3 个以上物理动作链" in system_prompt
    assert "至少 2 次情绪转向" in system_prompt
    assert "结尾截断" in system_prompt


def test_episode_plan_user_requires_field_level_episode_contract(happy_round_outputs):
    source_analysis, episode_context, story_bible = happy_round_outputs[:3]

    user_prompt = prompts.episode_plan_user(
        "武植睁眼看见金莲端药。",
        source_analysis,
        episode_context,
        story_bible,
        None,
    )

    required_phrases = [
        "这一步只做戏剧工程设计，不写正片脚本",
        "每集必须按 EpisodeDramaPlan 字段逐项填写",
        "drama_engine：戏剧引擎",
        "protagonist_misbelief 和 truth_gap：误认知/真相差",
        "physical_action_chain：3 个以上物理动作链",
        "主体 + 动作 + 对象 + 当场后果",
        "scene_dynamics：场景动态",
        "emotional_turns：至少 2 次情绪转向",
        "audience_information_gap：观众知道但角色不知道的信息差",
        "three_pull_beats：三波拉扯",
        "false_payoff：至少一次假打脸/期待落空",
        "planted_key：一个早埋晚用的道具",
        "strongest_line：全集最狠的一句短台词",
        "短于 18 个汉字",
        "cliffhanger_design：结尾截断",
    ]
    for phrase in required_phrases:
        assert phrase in user_prompt


def test_episode_plan_user_bans_abstract_shortcuts_and_preserves_genre_guard():
    source_text = "武大郎在大宋醒来，误以为金莲要害他。"
    outputs = demo_round_outputs(source_text=source_text, include_sop_stack=True)
    source_analysis, viral_asset_report, episode_context, story_bible, series_plan = outputs[:5]

    user_prompt = prompts.episode_plan_user(
        source_text,
        source_analysis,
        episode_context,
        story_bible,
        None,
        viral_asset_report=viral_asset_report,
        series_structure_plan=series_plan,
    )

    assert "禁止抽象词如“增强爽感”" in user_prompt
    assert "“制造悬念”" in user_prompt
    assert "谁做什么、对谁做、造成什么当场后果" in user_prompt
    assert "男频穿越 / 大宋 / 武大郎 / 金莲 / 西门庆" in user_prompt
    assert "现代认知差、轻喜误会反转、护妻/经商打脸" in user_prompt
    assert "不得套真假千金、豪门认亲、宴会验亲或亲哥哥救场模板" in user_prompt
