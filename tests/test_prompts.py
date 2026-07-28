import json

from novel_drama_engine import prompts
from novel_drama_engine.demo import demo_round_outputs
from novel_drama_engine.models import (
    AdaptationIntensity,
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    SourceDialogueCue,
    MethodologyCard,
    MethodologyContext,
    MethodologyStage,
    MethodologyStatus,
    SourceStrengthLevel,
    SourceAnnotation,
    SourceAnnotationEpisode,
    StoryBible,
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


def test_script_prompt_prioritizes_creative_drama_without_shooting_constraints(happy_round_outputs):
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
    assert "action 写可看见的动作、道具、表情、空间压迫、声音或转场" in user_prompt
    assert "首稿不按 action/对白/镜头数量凑行" in user_prompt
    assert "每条 action 必须写清景别" not in user_prompt
    assert "每条 action 必须显式包含一个景别词" not in user_prompt
    assert "scene.lines 合计至少 28 行" not in user_prompt
    assert "一句不超过 22 个汉字" in user_prompt
    assert "无景别、无运镜" not in user_prompt
    assert "消费理由说明" in user_prompt
    assert "最后一场最后 2 行必须把 cliffhanger" in user_prompt
    assert "观众要看、本集看点、本集钩子" in user_prompt
    assert "先输出 creative_script" in prompts.SCRIPT_SYSTEM
    assert "AI 视频执行" not in prompts.SCRIPT_SYSTEM
    assert "3-3-3 节奏规则" in prompts.SCRIPT_SYSTEM
    assert "每约 30 秒必须有情绪波动、信息增量或剧情推进之一" in prompts.SCRIPT_SYSTEM


def test_script_prompt_does_not_dump_internal_methodology_context(happy_round_outputs):
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

    assert "创作最小上下文" in user_prompt
    assert "内部方法论卡" not in user_prompt
    assert "强原文轻改规则" not in user_prompt
    assert "保留主动方和因果顺序" not in user_prompt
    assert "用户选择方法论" not in user_prompt


def test_script_writer_prompt_does_not_leak_future_story_bible_or_context_events():
    outputs = demo_round_outputs(include_episode_plan=True)
    source_analysis, episode_context, _, episode_plan = outputs[:4]
    future_event = "中央调查组在婚礼现场抓捕反派"
    packet = EpisodeSourcePacket(
        episode=1,
        source_anchor="姐姐下葬后，妹妹靠近醉酒姐夫",
        source_excerpt="姐姐下葬一个月后，妹妹从背后抱住醉酒的姐夫。姐夫立刻推开她。",
        c0_facts=["姐夫先推开妹妹"],
        c1_must_keep_assets=["从背后环抱后被推开"],
        c4_forbidden_additions=[f"不得提前泄露：{future_event}"],
    )
    bible = StoryBible(
        genre="复仇",
        mainline=future_event,
        characters=["妹妹", "姐夫", "调查组负责人"],
        relationships=["妹妹与姐夫互相试探", f"{future_event}后关系终结"],
        speech_styles={"妹妹": "克制", "姐夫": "伪善", "调查组负责人": "威严"},
        immutable_facts=["姐夫先推开妹妹", future_event],
        forbidden_changes=[f"不得提前泄露：{future_event}"],
    )
    bounded_context = episode_context.model_copy(
        update={"must_carry_context": [future_event]}
    )
    source_annotation = SourceAnnotation(
        north_star="原文优先",
        global_must_keep=[future_event],
        global_forbidden_changes=[f"不得提前泄露：{future_event}"],
        removable_passages=[future_event],
        episodes=[
            SourceAnnotationEpisode(
                episode=1,
                source_anchor=packet.source_anchor,
                source_excerpt=packet.source_excerpt,
                core_conflict="妹妹靠近，姐夫推开",
                must_keep_events=["姐夫先推开妹妹"],
                forbidden_changes=[f"不得提前泄露：{future_event}"],
            )
        ],
    )

    user_prompt = prompts.script_user(
        packet.source_excerpt,
        source_analysis,
        bounded_context,
        bible,
        None,
        "",
        round_number=1,
        target_episode_count=40,
        episode_plan=episode_plan,
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
        source_annotation=source_annotation,
    )

    assert "姐夫先推开妹妹" in user_prompt
    assert "妹妹" in user_prompt
    assert "姐夫" in user_prompt
    assert future_event not in user_prompt
    assert "调查组负责人" not in user_prompt


def test_script_writer_prompt_uses_minimal_source_contract_not_upstream_dumps(
    happy_round_outputs,
):
    outputs = demo_round_outputs(include_sop_stack=True, include_episode_plan=True)
    source_analysis = outputs[0]
    viral_asset_report = outputs[1]
    episode_context = outputs[2]
    story_bible = outputs[3]
    series_structure_plan = outputs[4]
    episode_plan = outputs[5]
    previous_context = outputs[8]
    methodology_context = MethodologyContext(
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
        previous_context,
        "",
        round_number=1,
        target_episode_count=30,
        episode_plan=episode_plan,
        viral_asset_report=viral_asset_report,
        series_structure_plan=series_structure_plan,
        methodology_context=methodology_context,
    )
    repair_prompt = prompts.script_episode_user(
        "林晚被赶出生日宴。",
        source_analysis,
        episode_context,
        story_bible,
        previous_context,
        outputs[6].episodes[0],
        1,
        "EP01 原文偏离。",
        episode_plan=episode_plan,
        viral_asset_report=viral_asset_report,
        series_structure_plan=series_structure_plan,
        methodology_context=methodology_context,
    )
    combined_prompt = "\n".join([user_prompt, repair_prompt])

    assert "创作最小上下文" in combined_prompt
    assert "source_analysis_digest" not in combined_prompt
    assert "viral_asset_report" not in combined_prompt
    assert "series_structure_plan" not in combined_prompt
    assert "强原文轻改规则" not in combined_prompt
    assert "保留主动方和因果顺序" not in combined_prompt
    assert "previous_context_handoff_digest" in combined_prompt
    assert "episode_context_boundary" in combined_prompt


def test_script_prompt_mode_env_cannot_reenable_legacy_writer_context(
    happy_round_outputs,
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_SCRIPT_PROMPT_MODE", "legacy")
    outputs = demo_round_outputs(include_sop_stack=True, include_episode_plan=True)
    source_analysis = outputs[0]
    viral_asset_report = outputs[1]
    episode_context = outputs[2]
    story_bible = outputs[3]
    series_structure_plan = outputs[4]
    episode_plan = outputs[5]
    methodology_context = MethodologyContext(
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
        viral_asset_report=viral_asset_report,
        series_structure_plan=series_structure_plan,
        methodology_context=methodology_context,
    )

    assert prompts.script_prompt_mode() == "creative"
    assert "创作最小上下文" in user_prompt
    assert "viral_asset_report" not in user_prompt
    assert "series_structure_plan" not in user_prompt
    assert "内部方法论卡" not in user_prompt
    assert "强原文轻改规则" not in user_prompt


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
    assert "无景别、无运镜" not in user_prompt
    assert "每条 action 必须以 △ 开头" not in user_prompt


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


def test_script_generation_prompts_make_source_fidelity_a_generation_metric(
    happy_round_outputs,
):
    source_analysis, episode_context, story_bible, script_batch, _, previous_context = (
        happy_round_outputs
    )

    script_prompt = prompts.script_user(
        "林晚被赶出生日宴。",
        source_analysis,
        episode_context,
        story_bible,
        previous_context,
        "",
        1,
    )
    repair_prompt = prompts.script_episode_user(
        "林晚被赶出生日宴。",
        source_analysis,
        episode_context,
        story_bible,
        previous_context,
        script_batch.episodes[0],
        1,
        "EP01 源文相似度不足。",
    )
    polish_prompt = prompts.hook_dialogue_polish_user(
        "林晚被赶出生日宴。",
        source_analysis,
        episode_context,
        story_bible,
        previous_context,
        script_batch.episodes[0],
        1,
        "结尾钩子太软。",
    )

    for user_prompt in [script_prompt, repair_prompt, polish_prompt]:
        assert "生成期源文保真硬指标" in user_prompt
        assert "源文相似度不得低于 5/10" in user_prompt
        assert "低于 5/10 的稿件视为无效输出" in user_prompt
        assert "返回 EpisodeScript 前必须先自检 source_fidelity_target" in user_prompt


def test_script_prompts_pin_source_assets_as_visible_scene_line_contract(
    happy_round_outputs,
):
    source_analysis, episode_context, story_bible, script_batch, _, previous_context = (
        happy_round_outputs
    )
    packet = EpisodeSourcePacket(
        episode=1,
        source_anchor="颁奖礼羞辱",
        source_excerpt="灯光打到她身上，掌心被掐到鲜血淋漓。",
        c0_facts=["解约协议提前放在办公室"],
        c1_must_keep_assets=["颁奖台灯光聚焦时的紧身裙窘迫"],
        source_evidence_assets=["停车场鲜血淋漓的掌心"],
        c2_visual_assets=["暗光座位区与明亮颁奖台反差"],
        golden_lines=["协议记得看"],
    )
    packets = EpisodeSourcePackets(packets=[packet])

    script_prompt = prompts.script_user(
        "灯光打到她身上，掌心被掐到鲜血淋漓。",
        source_analysis,
        episode_context,
        story_bible,
        previous_context,
        "",
        1,
        episode_source_packets=packets,
    )
    repair_prompt = prompts.script_episode_user(
        "灯光打到她身上，掌心被掐到鲜血淋漓。",
        source_analysis,
        episode_context,
        story_bible,
        previous_context,
        script_batch.episodes[0],
        1,
        "EP01 缺少原文资产。",
        episode_source_packet=packet,
    )

    for user_prompt in [script_prompt, repair_prompt]:
        assert "source_fidelity_must_render" in user_prompt
        assert "必须逐条落到 scene.lines" in user_prompt
        assert "不能只写在 title/hook_3s/watch_reason/cliffhanger/state_update" in user_prompt
        assert "颁奖台灯光聚焦时的紧身裙窘迫" in user_prompt
        assert "停车场鲜血淋漓的掌心" in user_prompt
        assert "协议记得看" in user_prompt


def test_script_prompts_treat_source_dialogue_speaker_and_addressee_as_locked_roles(
    happy_round_outputs,
):
    source_analysis, episode_context, story_bible, script_batch, _, previous_context = (
        happy_round_outputs
    )
    packet = EpisodeSourcePacket(
        episode=1,
        source_anchor="原文对白",
        source_excerpt="江毅冷笑：‘还要拐走我老婆，张雅。’",
        dialogue_cues=[
            SourceDialogueCue(
                cue_id="D-EP01-source",
                speaker="江毅",
                addressee="张雅",
                text="还要拐走我老婆，张雅。",
                source_span_ids=["S-EP01"],
                attribution="explicit_name",
                confidence="high",
            )
        ],
    )

    prompt = prompts.script_episode_user(
        packet.source_excerpt,
        source_analysis,
        episode_context,
        story_bible,
        previous_context,
        script_batch.episodes[0],
        1,
        "修复说话人。",
        episode_source_packet=packet,
    )

    assert "原文对白角色锁" in prompt
    assert "speaker 和 addressee 不得互换" in prompt
    assert '"speaker": "江毅"' in prompt
    assert '"addressee": "张雅"' in prompt


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


def test_script_batch_digest_never_repeats_lines_between_opening_and_tail(
    happy_round_outputs,
):
    script_batch = happy_round_outputs[3].model_copy(deep=True)
    episode = script_batch.episodes[0]
    episode.scenes = episode.scenes[:1]
    episode.scenes[0].lines = [
        episode.scenes[0].lines[index % len(episode.scenes[0].lines)].model_copy(
            update={"text": f"唯一内容-{index}"}
        )
        for index in range(16)
    ]

    rendered = prompts.render_script_batch_digest("script_batch_digest", script_batch)
    payload = json.loads(rendered.removeprefix("script_batch_digest: "))
    digest = payload["episodes"][0]

    assert len(digest["opening_lines"]) == 8
    assert len(digest["tail_lines"]) == 8
    assert set(digest["opening_lines"]).isdisjoint(digest["tail_lines"])


def test_episode_repair_prompt_includes_current_episode_repair_packet(happy_round_outputs):
    source_analysis, episode_context, story_bible, script_batch, _, previous_context = (
        happy_round_outputs
    )
    existing_episode = script_batch.episodes[0].model_copy(deep=True)
    existing_episode.scenes[0].lines[0].text = "△林晚站在宴会厅门口。"
    repair_packet = build_current_episode_repair_packet(
        existing_episode,
        "EP01 动作行格式不合格。",
        source_evidence_targets=["EP01 缺少原文资产：亲哥哥救场"],
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
    assert "当前集原文契约是唯一内容基准" in user_prompt
    assert "旧稿只作为问题定位参考" in user_prompt
    assert "baseline_episode_text" in user_prompt
    assert "△林晚站在宴会厅门口。" in user_prompt
    assert "必须优先遵守 current_episode_repair_packet.allowed_change_scope" in user_prompt
    assert "source_evidence_targets" in user_prompt
    assert "source_evidence_targets 是本集必须补回的原文证据" in user_prompt
    assert "current_episode_repair_packet.baseline_episode_text 是当前集旧稿的文本基准" not in user_prompt
    assert "protected_elements 必须照抄" not in user_prompt


def test_script_batch_prompt_makes_source_packet_boundary_override_episode_plan(
    happy_round_outputs,
):
    source_analysis, episode_context, story_bible, _, _, previous_context = (
        happy_round_outputs
    )

    user_prompt = prompts.script_user(
        "林晚被赶出生日宴。",
        source_analysis,
        episode_context,
        story_bible,
        previous_context,
        "",
        1,
    )

    assert "source packet 是当前集原文边界" in user_prompt
    assert "EpisodeDramaPlan 只能在当前集 source packet 边界内执行" in user_prompt


def test_script_prompt_does_not_dump_untrusted_episode_mapping(
    happy_round_outputs,
):
    source_analysis, episode_context, story_bible, script_batch, _, previous_context = (
        happy_round_outputs
    )
    episode_context = episode_context.model_copy(
        update={
            "source_to_episode_mapping": [
                {
                    "source": "WRONG_CROSS_EPISODE_MAPPING_SHOULD_NOT_REACH_SCRIPT",
                    "target_episode": "EP02",
                    "retained_assets": ["错误跨集资产"],
                }
            ]
        },
        deep=True,
    )

    user_prompt = prompts.script_user(
        "林晚被赶出生日宴。",
        source_analysis,
        episode_context,
        story_bible,
        previous_context,
        "",
        1,
    )
    polish_prompt = prompts.hook_dialogue_polish_user(
        "林晚被赶出生日宴。",
        source_analysis,
        episode_context,
        story_bible,
        previous_context,
        script_batch.episodes[0],
        1,
        "结尾钩子太软。",
    )
    combined_prompt = "\n".join([user_prompt, polish_prompt])

    assert "WRONG_CROSS_EPISODE_MAPPING_SHOULD_NOT_REACH_SCRIPT" not in combined_prompt
    assert "source_to_episode_mapping" not in combined_prompt
    assert "episode_context_boundary" in combined_prompt


def test_episode_repair_prompt_makes_source_packet_boundary_override_episode_plan(
    happy_round_outputs,
):
    source_analysis, episode_context, story_bible, script_batch, _, previous_context = (
        happy_round_outputs
    )
    existing_episode = script_batch.episodes[0]

    user_prompt = prompts.script_episode_user(
        "林晚被赶出生日宴。",
        source_analysis,
        episode_context,
        story_bible,
        previous_context,
        existing_episode,
        1,
        "EP01 原文偏离。",
    )

    assert "source packet 是当前集原文边界" in user_prompt
    assert "EpisodeDramaPlan 只能在当前集 source packet 边界内执行" in user_prompt


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


def test_source_evidence_hook_polish_prompt_uses_source_contract_baseline(
    happy_round_outputs,
):
    source_analysis, episode_context, story_bible, script_batch, _, previous_context = (
        happy_round_outputs
    )
    existing_episode = script_batch.episodes[0].model_copy(
        deep=True,
        update={"cliffhanger": "明天再说。"},
    )
    repair_packet = build_current_episode_repair_packet(
        existing_episode,
        "EP01 源文证据未落到正片。",
        source_evidence_targets=["EP01 缺少原文资产：亲哥哥救场"],
    )

    user_prompt = prompts.hook_dialogue_polish_user(
        "林晚被赶出生日宴。",
        source_analysis,
        episode_context,
        story_bible,
        previous_context,
        existing_episode,
        1,
        "EP01 源文证据未落到正片。",
        current_episode_repair_packet=repair_packet,
    )

    assert "当前集原文契约是唯一内容基准" in user_prompt
    assert "current_episode_repair_packet.baseline_episode_text 是唯一文本基准" not in user_prompt
    assert "必须保留 existing_episode" not in user_prompt


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
    assert "创作最小上下文" in script_prompt
    assert "viral_asset_report" not in script_prompt
    assert "series_structure_plan" not in script_prompt
    assert "信息增量、断点类型和原文锚点" in script_prompt
