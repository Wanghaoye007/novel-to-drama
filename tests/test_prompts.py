from novel_drama_engine import prompts
from novel_drama_engine.demo import demo_round_outputs
from novel_drama_engine.models import (
    AdaptationIntensity,
    MethodologyCard,
    MethodologyContext,
    MethodologyStage,
    MethodologyStatus,
    SourceStrengthLevel,
)
from novel_drama_engine.script_quality import build_current_episode_repair_packet


def test_episode_context_prompt_requires_canonical_episode_range(happy_round_outputs):
    source_analysis = happy_round_outputs[0]

    user_prompt = prompts.episode_context_user(
        "林晚被赶出生日宴。",
        None,
        source_analysis,
        round_number=1,
        target_episode_count=30,
    )

    assert "target_episode_range 必须使用 EP 两位格式" in user_prompt
    assert "禁止输出 1-5" in user_prompt


def test_script_prompt_requires_executable_scene_and_shot_contract(happy_round_outputs):
    outputs = demo_round_outputs(include_episode_plan=True)
    source_analysis, episode_context, story_bible, episode_plan = outputs[:4]

    user_prompt = prompts.script_user(
        "武植睁眼看见金莲端药。",
        source_analysis,
        episode_context,
        story_bible,
        None,
        "",
        round_number=1,
        target_episode_count=30,
        episode_plan=episode_plan,
    )

    assert "episode_plan" in user_prompt
    assert "本轮集数硬清单" in user_prompt
    assert "episode 字段必须按顺序等于 1、2、3、4、5" in user_prompt
    assert "缺任一集就是失败" in user_prompt
    assert "three_pull_beats" in user_prompt
    assert "scene.heading 必须严格写成" in user_prompt
    assert "禁止只写 豪华宴会厅" in user_prompt
    assert "每条 action 必须写清景别" in user_prompt
    assert "本地质检只统计 scene.lines 渲染出来的用户可见正片文本" in user_prompt
    assert "不能用长 watch_reason、长 state_update" in user_prompt
    assert "每条 action 必须显式包含一个景别词" in user_prompt
    assert "一句不超过 22 个汉字" in user_prompt
    assert "不合格 action 示例" in user_prompt
    assert "消费理由说明" in user_prompt
    assert "最后一场最后 2 行必须把 cliffhanger" in user_prompt
    assert "观众要看、本集看点、本集钩子" in user_prompt
    assert "3-3-3 节奏规则" in prompts.SCRIPT_SYSTEM
    assert "每约 30 秒必须有情绪波动、信息增量或剧情推进之一" in prompts.SCRIPT_SYSTEM


def test_script_prompt_includes_internal_methodology_context(happy_round_outputs):
    outputs = demo_round_outputs(include_episode_plan=True)
    source_analysis, episode_context, story_bible, episode_plan = outputs[:4]
    context = MethodologyContext(
        source_strength_level=SourceStrengthLevel.STRONG,
        adaptation_intensity=AdaptationIntensity.LIGHT,
        cards=[
            MethodologyCard(
                id="card_001",
                source_id="source_001",
                name="强原文轻改规则",
                category="source_fidelity",
                applies_to_channel=["female"],
                applies_to_genre=["identity"],
                applies_to_stage=[MethodologyStage.SCRIPT_GENERATION],
                trigger="原文已具备强冲突和名场面",
                generation_rule="保留主动方和因果顺序，只做视听化。",
                quality_rule="删除 C1 名场面必须 needs_rewrite。",
                status=MethodologyStatus.ACTIVE,
            )
        ],
    )

    user_prompt = prompts.script_user(
        "林晚被赶出生日宴。",
        source_analysis,
        episode_context,
        story_bible,
        None,
        "",
        round_number=1,
        target_episode_count=30,
        episode_plan=episode_plan,
        methodology_context=context,
    )

    assert "内部方法论卡" in user_prompt
    assert "强原文轻改规则" in user_prompt
    assert "保留主动方和因果顺序" in user_prompt
    assert "用户选择方法论" not in user_prompt


def test_script_episode_prompt_targets_one_episode(happy_round_outputs):
    outputs = demo_round_outputs(include_episode_plan=True)
    source_analysis, episode_context, story_bible, episode_plan, script_batch = outputs[:5]

    user_prompt = prompts.script_episode_user(
        "武植睁眼看见金莲端药。",
        source_analysis,
        episode_context,
        story_bible,
        None,
        script_batch.episodes[0],
        1,
        "补足镜头动作和短台词。",
        episode_plan=episode_plan,
    )

    assert "只生成第 1 集" in user_prompt
    assert "episode 字段必须等于 1" in user_prompt
    assert "不要输出其他集数" in user_prompt
    assert "1-场次 日/夜-内/外-具体地点" in user_prompt
    assert "无景别、无运镜" in user_prompt


def test_episode_plan_prompt_requires_drama_design(happy_round_outputs):
    source_analysis, episode_context, story_bible = happy_round_outputs[:3]

    user_prompt = prompts.episode_plan_user(
        "林晚被赶出生日宴。",
        source_analysis,
        episode_context,
        story_bible,
        None,
    )

    assert "只做改编设计，不写完整台词剧本" in user_prompt
    assert "三波拉扯" in user_prompt
    assert "假打脸" in user_prompt
    assert "3-3-3 节奏规则" in prompts.EPISODE_PLAN_SYSTEM
    assert "反转、危机或选择钩子" in prompts.QUALITY_SYSTEM
    assert "最狠的一句短台词" in user_prompt


def test_prompts_define_general_source_asset_and_hook_contract():
    contract = prompts.SOURCE_ADAPTATION_CONTRACT

    assert "C0 不可改事实" in contract
    assert "C1 必保名场面" in contract
    assert "C2 可视听化资产" in contract
    assert "C3 可压缩资产" in contract
    assert "C4 禁止新增" in contract
    assert "开场钩子双模式" in contract
    assert "原文有强钩子" in contract
    assert "原文无强钩子" in contract
    assert "事实兼容型钩子" in contract
    assert "不得改变主动方" in contract
    assert "不得把深思熟虑改成临时起意" in contract
    assert "对手主动承诺" in contract
    assert "主角主动索要" in contract
    assert "高张力资产" in contract
    assert "人物关系可读性" in contract
    assert "表层关系" in contract
    assert "认识这个人但不知道真实身份" in contract
    assert "先亲密称呼、后又泛问" in contract
    assert "人物行动权规则" in contract
    assert "不得在原文没有重生、预知、马甲、提前布局" in contract
    assert "支持型角色只能提供选择权" in contract
    assert "对手/反派每轮必须有主动设局" in contract


def test_pipeline_prompts_apply_source_fidelity_contract_to_each_stage():
    outputs = demo_round_outputs(include_sop_stack=True, include_episode_plan=True, target_episode_count=30)
    source_analysis = outputs[0]
    viral_asset_report = outputs[1]
    episode_context = outputs[2]
    story_bible = outputs[3]
    series_structure_plan = outputs[4]
    episode_plan = outputs[5]
    script_batch = outputs[6]
    previous_context = outputs[8]

    source_prompt = prompts.source_parser_user("她沉默签下离婚协议。")
    viral_prompt = prompts.viral_asset_user("她沉默签下离婚协议。", source_analysis, target_episode_count=30)
    context_prompt = prompts.episode_context_user(
        "她沉默签下离婚协议。",
        previous_context,
        source_analysis,
        round_number=2,
        target_episode_count=30,
        viral_asset_report=viral_asset_report,
    )
    bible_prompt = prompts.bible_user(
        "她沉默签下离婚协议。",
        source_analysis,
        episode_context,
        viral_asset_report=viral_asset_report,
    )
    series_prompt = prompts.series_structure_user(
        "她沉默签下离婚协议。",
        source_analysis,
        episode_context,
        story_bible,
        viral_asset_report,
        previous_context,
        target_episode_count=30,
    )
    plan_prompt = prompts.episode_plan_user(
        "她沉默签下离婚协议。",
        source_analysis,
        episode_context,
        story_bible,
        previous_context,
        viral_asset_report=viral_asset_report,
        series_structure_plan=series_structure_plan,
    )
    script_prompt = prompts.script_user(
        "她沉默签下离婚协议。",
        source_analysis,
        episode_context,
        story_bible,
        previous_context,
        "",
        target_episode_count=30,
        episode_plan=episode_plan,
        viral_asset_report=viral_asset_report,
        series_structure_plan=series_structure_plan,
    )
    repair_prompt = prompts.script_episode_user(
        "她沉默签下离婚协议。",
        source_analysis,
        episode_context,
        story_bible,
        previous_context,
        script_batch.episodes[0],
        1,
        "修复跑偏人物动机。",
        episode_plan=episode_plan,
        viral_asset_report=viral_asset_report,
        series_structure_plan=series_structure_plan,
    )
    polish_prompt = prompts.hook_dialogue_polish_user(
        "她沉默签下离婚协议。",
        source_analysis,
        episode_context,
        story_bible,
        previous_context,
        script_batch.episodes[0],
        1,
        "结尾钩子太软。",
        episode_plan=episode_plan,
        viral_asset_report=viral_asset_report,
        series_structure_plan=series_structure_plan,
    )
    quality_prompt = prompts.quality_user(
        source_analysis,
        episode_context,
        story_bible,
        script_batch,
        previous_context,
        viral_asset_report=viral_asset_report,
        series_structure_plan=series_structure_plan,
        episode_plan=episode_plan,
    )

    for user_prompt in [
        source_prompt,
        viral_prompt,
        context_prompt,
        bible_prompt,
        series_prompt,
        plan_prompt,
        script_prompt,
        repair_prompt,
        polish_prompt,
        quality_prompt,
    ]:
        assert "【通用改编合同】" in user_prompt
        assert "C0 不可改事实" in user_prompt
        assert "事实兼容型钩子" in user_prompt
        assert "禁止改变 C0" in user_prompt
        assert "人物关系可读性" in user_prompt
        assert "人物行动权规则" in user_prompt

    assert "C0/C1/C2/C3/C4 分级" in context_prompt
    assert "immutable_facts 必须吸收 C0" in bible_prompt
    assert "opening_contract 必须显式判断开场钩子双模式" in series_prompt
    assert "source_assets_to_keep：按 C0/C1/C2/C3" in plan_prompt
    assert "第一场必须保留其核心张力" in script_prompt
    assert "这是按问题类型执行的定向修复，不是默认整集重写" in repair_prompt
    assert "定向修复必须是“回到原文资产 + 修指定缺口”" in repair_prompt
    assert "润色前必须核对本集 C0/C1" in polish_prompt
    assert "原著保真质检" in quality_prompt
    assert "删除了 C1 天然钩子" in quality_prompt
    assert "第一次同框、熟称、身份反转或阵营反转" in quality_prompt
    assert "先叫小雅/姐姐/哥/霍总" in quality_prompt
    assert "支持型角色不得替主角做核心决定" in quality_prompt


def test_quality_and_state_prompts_use_script_batch_digest(happy_round_outputs):
    source_analysis, episode_context, story_bible, script_batch, quality_report, previous_context = (
        happy_round_outputs
    )

    quality_prompt = prompts.quality_user(
        source_analysis,
        episode_context,
        story_bible,
        script_batch,
        previous_context,
    )
    state_prompt = prompts.state_user(
        source_analysis,
        episode_context,
        story_bible,
        script_batch,
        quality_report,
        previous_context,
    )

    assert "script_batch_digest" in quality_prompt
    assert "script_batch_digest" in state_prompt
    assert '"opening_lines"' in quality_prompt
    assert '"tail_lines"' in state_prompt
    assert "△全景摇向宴会厅侧门" not in quality_prompt
    assert "△全景摇向宴会厅侧门" not in state_prompt


def test_episode_repair_prompt_includes_current_episode_repair_packet(happy_round_outputs):
    source_analysis, episode_context, story_bible, script_batch, _, previous_context = (
        happy_round_outputs
    )
    existing_episode = script_batch.episodes[0].model_copy(deep=True)
    existing_episode.scenes[0].lines[0].text = "△林晚站在宴会厅门口。"
    repair_packet = build_current_episode_repair_packet(
        existing_episode,
        "EP01 动作行格式不合格。",
    )

    user_prompt = prompts.script_episode_user(
        "林晚被赶出生日宴。",
        source_analysis,
        episode_context,
        story_bible,
        previous_context,
        existing_episode,
        1,
        "EP01 动作行格式不合格。",
        current_episode_repair_packet=repair_packet,
    )

    assert "current_episode_repair_packet" in user_prompt
    assert "当前集旧稿是唯一文本基准" in user_prompt
    assert "baseline_episode_text" in user_prompt
    assert "△林晚站在宴会厅门口。" in user_prompt
    assert "必须优先遵守 current_episode_repair_packet.allowed_change_scope" in user_prompt


def test_hook_polish_prompt_includes_current_episode_repair_packet(happy_round_outputs):
    source_analysis, episode_context, story_bible, script_batch, _, previous_context = (
        happy_round_outputs
    )
    existing_episode = script_batch.episodes[0].model_copy(
        deep=True,
        update={"cliffhanger": "明天再说。"},
    )
    repair_packet = build_current_episode_repair_packet(
        existing_episode,
        "EP01 结尾钩子太软。",
    )

    user_prompt = prompts.hook_dialogue_polish_user(
        "林晚被赶出生日宴。",
        source_analysis,
        episode_context,
        story_bible,
        previous_context,
        existing_episode,
        1,
        "EP01 结尾钩子太软。",
        current_episode_repair_packet=repair_packet,
    )

    assert "current_episode_repair_packet" in user_prompt
    assert "当前集旧稿是唯一文本基准" in user_prompt
    assert "baseline_episode_text" in user_prompt
    assert "current_episode_repair_packet.baseline_episode_text" in user_prompt


def test_sop_stack_prompts_capture_viral_assets_and_series_structure():
    outputs = demo_round_outputs(include_sop_stack=True, target_episode_count=30)
    source_analysis, viral_asset_report, episode_context, story_bible, series_plan = outputs[:5]

    viral_prompt = prompts.viral_asset_user(
        "林晚被赶出生日宴。",
        source_analysis,
        target_episode_count=30,
    )
    series_prompt = prompts.series_structure_user(
        "林晚被赶出生日宴。",
        source_analysis,
        episode_context,
        story_bible,
        viral_asset_report,
        None,
        target_episode_count=30,
    )
    script_prompt = prompts.script_user(
        "林晚被赶出生日宴。",
        source_analysis,
        episode_context,
        story_bible,
        None,
        "",
        target_episode_count=30,
        viral_asset_report=viral_asset_report,
        series_structure_plan=series_plan,
    )

    assert "至少保留 3 个大高潮名场面" in viral_prompt
    assert "每 3 集一个小高潮" in series_prompt
    assert "每集必须有核心事件、情绪节点、信息增量" in series_prompt
    assert "viral_asset_report" in script_prompt
    assert "series_structure_plan" in script_prompt
    assert "信息增量、断点类型和原文锚点" in script_prompt
