from novel_drama_engine import prompts
from novel_drama_engine.demo import demo_round_outputs


def test_all_stage_system_prompts_use_professional_contract_sections():
    stage_prompts = [
        prompts.SOURCE_PARSER_SYSTEM,
        prompts.VIRAL_ASSET_SYSTEM,
        prompts.EPISODE_CONTEXT_SYSTEM,
        prompts.BIBLE_SYSTEM,
        prompts.SERIES_STRUCTURE_SYSTEM,
        prompts.EPISODE_PLAN_SYSTEM,
        prompts.SCRIPT_SYSTEM,
        prompts.QUALITY_SYSTEM,
        prompts.STATE_SYSTEM,
    ]

    for system_prompt in stage_prompts:
        assert "【岗位】" in system_prompt
        assert "【Skill 边界】" in system_prompt
        assert "【任务】" in system_prompt
        assert "【专业方法】" in system_prompt
        assert "【输出纪律】" in system_prompt
        assert "【验收门】" in system_prompt
        assert "【失败模式】" in system_prompt


def test_user_prompts_preserve_pipeline_contract_and_professional_sections():
    outputs = demo_round_outputs(include_sop_stack=True, include_episode_plan=True, target_episode_count=30)
    source_analysis = outputs[0]
    viral_asset_report = outputs[1]
    episode_context = outputs[2]
    story_bible = outputs[3]
    series_structure_plan = outputs[4]
    episode_plan = outputs[5]
    script_batch = outputs[6]
    quality_report = outputs[7]
    previous_context = outputs[8]

    non_writer_prompts = [
        prompts.source_parser_user("武植睁眼看见金莲端药。"),
        prompts.viral_asset_user("武植睁眼看见金莲端药。", source_analysis, target_episode_count=30),
        prompts.episode_context_user(
            "武植睁眼看见金莲端药。",
            previous_context,
            source_analysis,
            round_number=2,
            target_episode_count=30,
            viral_asset_report=viral_asset_report,
        ),
        prompts.bible_user(
            "武植睁眼看见金莲端药。",
            source_analysis,
            episode_context,
            viral_asset_report=viral_asset_report,
        ),
        prompts.series_structure_user(
            "武植睁眼看见金莲端药。",
            source_analysis,
            episode_context,
            story_bible,
            viral_asset_report,
            previous_context,
            target_episode_count=30,
        ),
        prompts.episode_plan_user(
            "武植睁眼看见金莲端药。",
            source_analysis,
            episode_context,
            story_bible,
            previous_context,
            viral_asset_report=viral_asset_report,
            series_structure_plan=series_structure_plan,
        ),
    ]
    writer_prompts = [
        prompts.script_user(
            "武植睁眼看见金莲端药。",
            source_analysis,
            episode_context,
            story_bible,
            previous_context,
            "补足镜头动作。",
            target_episode_count=30,
            episode_plan=episode_plan,
            viral_asset_report=viral_asset_report,
            series_structure_plan=series_structure_plan,
        ),
        prompts.script_episode_user(
            "武植睁眼看见金莲端药。",
            source_analysis,
            episode_context,
            story_bible,
            previous_context,
            script_batch.episodes[0],
            1,
            "补足镜头动作。",
            episode_plan=episode_plan,
            viral_asset_report=viral_asset_report,
            series_structure_plan=series_structure_plan,
        ),
    ]
    non_writer_prompts.extend(
        [
            prompts.quality_user(
                source_analysis,
                episode_context,
            story_bible,
            script_batch,
            previous_context,
            viral_asset_report=viral_asset_report,
            series_structure_plan=series_structure_plan,
            episode_plan=episode_plan,
        ),
        prompts.state_user(
            source_analysis,
            episode_context,
            story_bible,
            script_batch,
            quality_report,
            previous_context,
            episode_plan=episode_plan,
                viral_asset_report=viral_asset_report,
                series_structure_plan=series_structure_plan,
            ),
        ]
    )

    for user_prompt in non_writer_prompts:
        assert "【全局框架】" in user_prompt
        assert "题材诊断 -> 爆款资产提纯 -> 集数/上下文解析" in user_prompt
        assert "【Skill 包运行规范】" in user_prompt
        assert "【输入资产】" in user_prompt
        assert "【决策顺序】" in user_prompt
        assert "【执行步骤】" in user_prompt
        assert "【输出契约】" in user_prompt
        assert "【专业标准】" in user_prompt
        assert "【验收门】" in user_prompt
        assert "【失败修复】" in user_prompt
        assert "【禁止事项】" in user_prompt

    for user_prompt in writer_prompts:
        assert "【创作最小上下文】" in user_prompt
        assert "【全局框架】" not in user_prompt
        assert "【Skill 包运行规范】" in user_prompt
        assert "【输入资产】" in user_prompt
        assert "【决策顺序】" in user_prompt
        assert "【执行步骤】" in user_prompt
        assert "【输出契约】" in user_prompt
        assert "【专业标准】" in user_prompt
        assert "【验收门】" in user_prompt
        assert "【失败修复】" in user_prompt
        assert "【禁止事项】" in user_prompt
