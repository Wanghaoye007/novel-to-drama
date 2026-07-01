from novel_drama_engine import prompts
from novel_drama_engine.demo import demo_round_outputs


def test_viral_asset_prompt_is_internal_asset_for_script_generation():
    source_analysis = demo_round_outputs(include_sop_stack=True, target_episode_count=30)[0]

    user_prompt = prompts.viral_asset_user(
        "林晚在宴会厅被林雪当众逼退。",
        source_analysis,
        target_episode_count=30,
    )

    assert "ViralAssetReport 是系统内部生产资产" in prompts.VIRAL_ASSET_SYSTEM
    assert "不能写成用户可见卖点文案" in prompts.VIRAL_ASSET_SYSTEM
    assert "只供后续集数解析、Story Bible、全剧结构、单集设计和脚本生成消费" in user_prompt
    assert "不得写成用户可见卖点文案、平台简介、投放文案或封面标题" in user_prompt
    assert "signature_scenes 和 small_highlights 每一条都必须写成“人物 + 地点 + 可见动作 + 当场后果”" in user_prompt
    assert "不能写成抽象情绪、爽感、主题或观念" in user_prompt
    assert "整条 SOP 全链路服务于后续脚本生成" in user_prompt
    assert "不要要求用户确认" in user_prompt


def test_series_structure_prompt_controls_rhythm_hooks_and_no_filler():
    outputs = demo_round_outputs(include_sop_stack=True, target_episode_count=30)
    source_analysis, viral_asset_report, episode_context, story_bible = outputs[:4]

    user_prompt = prompts.series_structure_user(
        "林晚在宴会厅被林雪当众逼退。",
        source_analysis,
        episode_context,
        story_bible,
        viral_asset_report,
        None,
        target_episode_count=30,
    )

    assert "全剧节奏、每集信息增量、断点类型、原文锚点和禁水集规则" in prompts.SERIES_STRUCTURE_SYSTEM
    assert "不增加用户确认门" in prompts.SERIES_STRUCTURE_SYSTEM
    assert "不得新增用户确认门、方向选择门或人工审核节点" in user_prompt
    assert "global_emotion_curve、small_climax_cadence、big_climax_cadence 必须共同约束全剧节奏" in user_prompt
    assert "每集必须有独立信息增量" in user_prompt
    assert "ending_hook_type 必须是可执行断点类型" in user_prompt
    assert "source_anchor 必须指向原文具体段落/事件/台词/场面" in user_prompt
    assert "任何 episode_outline 都不能成为水集" in user_prompt
    assert "ending_hook 必须是画面/动作/台词级断点" in user_prompt
    assert "必须能直接被下一步脚本写成最后 2 行" in user_prompt
    assert "不能写“观众想看”“身份悬念推进”“等待揭晓”" in user_prompt
