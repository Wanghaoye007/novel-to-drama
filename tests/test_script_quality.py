from novel_drama_engine.demo import demo_round_outputs
from novel_drama_engine.models import (
    EpisodeScript,
    QualityReport,
    QualityScores,
    QualityStatus,
    Scene,
    SceneLine,
    ScriptBatch,
)
from novel_drama_engine.script_quality import (
    build_script_novelty_report,
    build_current_episode_repair_packet,
    cliffhanger_field_is_performed,
    episode_needs_hook_dialogue_polish,
    episode_quality_metrics,
    episode_quality_warnings,
    has_action_line_template,
    episode_repair_instruction,
    has_abnormal_repetition,
    has_executable_shot_language,
    has_explanatory_cliffhanger,
    hook_dialogue_polish_instruction,
    merge_script_novelty_into_quality_report,
    render_script_novelty_report,
    script_batch_quality_warnings,
)


def test_happy_demo_outputs_meet_reference_script_density(happy_round_outputs):
    script_batch = happy_round_outputs[3]

    for episode in script_batch.episodes:
        metrics = episode_quality_metrics(episode)
        assert metrics.chars >= 800
        assert metrics.scenes >= 2
        assert metrics.total_scene_lines >= 28
        assert metrics.action_lines >= 10
        assert metrics.voiced_lines >= 18
        assert metrics.shot_language_lines >= 8
        assert metrics.invalid_action_format_lines == 0
        assert metrics.long_voiced_lines == 0
        assert metrics.invalid_scene_headings == 0
        assert episode_quality_warnings(episode) == []


def test_happy_demo_outputs_pass_cross_episode_novelty_gate(happy_round_outputs):
    script_batch = happy_round_outputs[3]

    report = build_script_novelty_report(script_batch)

    assert report.overall_score >= 7
    assert report.blocking_issues == []
    assert render_script_novelty_report(report).startswith("# Script Novelty Report")


def test_cross_episode_novelty_gate_blocks_repeated_episode_batch(happy_round_outputs):
    source_episode = happy_round_outputs[3].episodes[0]
    script_batch = ScriptBatch(
        episodes=[
            source_episode.model_copy(update={"episode": 1, "title": "重复样本 A"}, deep=True),
            source_episode.model_copy(update={"episode": 2, "title": "重复样本 B"}, deep=True),
            source_episode.model_copy(update={"episode": 3, "title": "重复样本 C"}, deep=True),
        ]
    )

    report = build_script_novelty_report(script_batch)

    assert report.overall_score < 7
    assert report.blocking_issues
    assert any(
        issue.kind in {"overall", "scene_skeleton", "action_chain"}
        and issue.severity == "blocking"
        for issue in report.similarity_issues
    )
    assert "跨集新鲜度不足" in report.rewrite_instruction


def test_cross_episode_novelty_gate_downgrades_usable_quality_report(happy_round_outputs):
    source_episode = happy_round_outputs[3].episodes[0]
    repeated_batch = ScriptBatch(
        episodes=[
            source_episode.model_copy(update={"episode": 1, "title": "重复样本 A"}, deep=True),
            source_episode.model_copy(update={"episode": 2, "title": "重复样本 B"}, deep=True),
        ]
    )
    novelty_report = build_script_novelty_report(repeated_batch)
    quality_report = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=9,
            continuity=9,
            video_feasibility=9,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )

    merged = merge_script_novelty_into_quality_report(quality_report, novelty_report)

    assert merged.status == QualityStatus.NEEDS_REWRITE
    assert any(issue.startswith("script_novelty:") for issue in merged.blocking_issues)
    assert "禁止复用同一套场景" in merged.rewrite_instruction


def test_quality_warnings_reject_short_static_episode():
    episode = EpisodeScript(
        episode=1,
        title="薄弱样例",
        hook_3s="她来了。",
        main_emotion="平",
        watch_reason="信息不足。",
        scenes=[
            Scene(
                heading="1-1 日-内-屋内",
                characters=["甲", "乙"],
                lines=[
                    SceneLine(kind="action", text="△甲站着。"),
                    SceneLine(kind="dialogue", speaker="甲", emotion="平", text="你好。"),
                    SceneLine(kind="dialogue", speaker="乙", emotion="平", text="嗯。"),
                ],
            )
        ],
        cliffhanger="她来了。",
        state_update={},
    )

    warnings = episode_quality_warnings(episode)

    assert any("too short" in warning for warning in warnings)
    assert any("action lines" in warning for warning in warnings)
    assert any("opening" in warning for warning in warnings)


def test_quality_warnings_reject_generic_scene_heading():
    episode = EpisodeScript(
        episode=1,
        title="泛化场景头",
        hook_3s="谁敢碰她一下！",
        main_emotion="压迫",
        watch_reason="观众要看她反击。",
        scenes=[
            Scene(
                heading="豪华宴会厅",
                characters=["甲", "乙"],
                lines=[
                    SceneLine(kind="action", text="△中近景推近甲，灯光压暗，酒杯占前景。"),
                    SceneLine(kind="dialogue", speaker="甲", emotion="冷", text="滚出去！"),
                    SceneLine(kind="dialogue", speaker="乙", emotion="怒", text="凭什么？"),
                ],
            )
        ],
        cliffhanger="门外传来一声冷笑：谁说她不配？",
        state_update={},
    )

    warnings = episode_quality_warnings(episode)

    assert any("non-shooting scene headings" in warning for warning in warnings)
    assert any("1-1 夜-内-具体地点" in warning for warning in warnings)


def test_quality_warnings_reject_exposed_analysis_and_abstract_action():
    episode = EpisodeScript(
        episode=1,
        title="分析外露",
        hook_3s="滚出去！",
        main_emotion="羞辱",
        watch_reason="观众要看女主反击。",
        scenes=[
            Scene(
                heading="1-1 夜-内-林家宴会厅",
                characters=["林晚", "林雪"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△中景推近林晚，本集看点是她如何反击，众人震惊。",
                    ),
                    SceneLine(kind="dialogue", speaker="林雪", emotion="冷", text="滚出去！"),
                    SceneLine(kind="dialogue", speaker="林晚", emotion="冷", text="凭什么？"),
                ],
            )
        ],
        cliffhanger="门外有人冷笑：谁敢动她？",
        state_update={},
    )

    warnings = episode_quality_warnings(episode)

    assert any("exposes hook/watch_reason analysis" in warning for warning in warnings)
    assert any("abstract action lines" in warning for warning in warnings)


def test_batch_quality_warnings_reject_episode_range_mismatch(happy_round_outputs):
    script_batch = happy_round_outputs[3]

    warnings = script_batch_quality_warnings(script_batch, "EP01-EP01")

    assert any("mismatch target range EP01-EP01" in warning for warning in warnings)
    assert any("got EP01,EP02,EP03,EP04,EP05" in warning for warning in warnings)


def test_batch_quality_warnings_accept_expected_episode_range(happy_round_outputs):
    script_batch = happy_round_outputs[3]

    assert script_batch_quality_warnings(script_batch, "EP01-EP05") == []


def test_episode_repair_instruction_names_local_quality_gaps():
    episode = EpisodeScript(
        episode=1,
        title="短稿",
        hook_3s="谁敢拦我！",
        main_emotion="压迫",
        watch_reason="系统内部看点。",
        scenes=[
            Scene(
                heading="1-1 夜-内-温家走廊",
                characters=["女主", "温舟"],
                lines=[
                    SceneLine(kind="action", text="△中景推近女主，她站在门口。"),
                    SceneLine(kind="dialogue", speaker="女主", text="让开。"),
                    SceneLine(kind="dialogue", speaker="温舟", text="不行。"),
                ],
            )
        ],
        cliffhanger="让开。",
        state_update={},
    )

    instruction = episode_repair_instruction(episode, "补足镜头。")

    assert "补足镜头。" in instruction
    assert "当前本地质检" in instruction
    assert "必须补足缺口" in instruction
    assert "action 行硬格式" in instruction
    assert "禁止以“△女主/△温铮/△他/△她/△门外/△突然”直接开头" in instruction
    assert "至少增加" in instruction
    assert "本集本地阻断项" in instruction


def test_episode_repair_instruction_limits_cliffhanger_fix_to_tail(happy_round_outputs):
    episode = happy_round_outputs[3].episodes[0].model_copy(
        deep=True,
        update={"cliffhanger": "明天再说。"},
    )

    instruction = episode_repair_instruction(episode, "EP01 结尾钩子太软。")

    assert "修复级别：结尾钩子局部修复" in instruction
    assert "只修最后一场最后 8-12 行" in instruction
    assert "不要整集重写" in instruction
    assert "必须整集重写" not in instruction


def test_episode_repair_instruction_limits_action_format_to_local_patch(
    happy_round_outputs,
):
    episode = happy_round_outputs[3].episodes[0].model_copy(deep=True)
    episode.scenes[0].lines[0].text = "△林晚站在宴会厅门口。"

    instruction = episode_repair_instruction(episode, "EP01 动作行格式不合格。")

    assert "修复级别：格式局部修复" in instruction
    assert "只修不合格 action 行" in instruction
    assert "不要整集重写" in instruction
    assert "必须整集重写" not in instruction


def test_current_episode_repair_packet_makes_existing_episode_the_baseline(
    happy_round_outputs,
):
    episode = happy_round_outputs[3].episodes[0].model_copy(deep=True)
    episode.scenes[0].lines[0].text = "△林晚站在宴会厅门口。"

    packet = build_current_episode_repair_packet(
        episode,
        "EP01 动作行格式不合格。",
    )

    assert packet.episode == 1
    assert packet.repair_mode == "format_patch"
    assert "当前集旧稿是唯一文本基准" in packet.baseline_policy
    assert "只修不合格 action 行" in packet.allowed_change_scope
    assert "△林晚站在宴会厅门口。" in packet.baseline_episode_text
    assert any("action lines violating" in target for target in packet.editable_targets)
    assert "不得新增无原文依据的新剧情、新道具、新证据或新狠话" in packet.forbidden_changes


def test_hook_dialogue_polish_instruction_targets_tail_and_dialogue_gaps():
    episode = EpisodeScript(
        episode=2,
        title="软结尾",
        hook_3s="你到底是谁？",
        main_emotion="悬疑",
        watch_reason="系统内部看点。",
        scenes=[
            Scene(
                heading="2-1 夜-内-温家玄关",
                characters=["女主", "温铮"],
                lines=[
                    SceneLine(kind="action", text="△中景推近女主，她拉开门。"),
                    SceneLine(kind="dialogue", speaker="温铮", text="你是谁？"),
                    SceneLine(kind="dialogue", speaker="女主", text="明天再说。"),
                    SceneLine(kind="action", text="△中景女主转身离开。"),
                ],
            )
        ],
        cliffhanger="明天再说。",
        state_update={},
    )

    instruction = hook_dialogue_polish_instruction(episode, "结尾太软。")

    assert episode_needs_hook_dialogue_polish(episode)
    assert "结尾钩子/对白密度二次编译" in instruction
    assert "不要整集重写" in instruction
    assert "最后 8-12 行" in instruction
    assert "转身离开" in instruction
    assert "全局修复背景" in instruction


def test_quality_normalizes_explanatory_cliffhanger_field_to_performed_tail():
    episode = EpisodeScript(
        episode=2,
        title="说明化钩子",
        hook_3s="你到底是谁？",
        main_emotion="悬疑",
        watch_reason="系统内部看点。",
        scenes=[
            Scene(
                heading="2-1 夜-内-温家玄关",
                characters=["女主", "温铮"],
                lines=[
                    SceneLine(kind="action", text="△中近景推近女主侧脸，手机屏幕占前景，BGM骤停，切到温铮发白的指节。"),
                    SceneLine(kind="dialogue", speaker="女主", text="这东西，为什么在你手里？"),
                ],
            )
        ],
        cliffhanger="温铮震惊，留下关于女主真实身份的悬念。",
        state_update={},
    )

    warnings = episode_quality_warnings(episode)

    assert has_explanatory_cliffhanger("温铮震惊，留下关于女主真实身份的悬念。")
    assert episode.cliffhanger == "这东西，为什么在你手里？"
    assert cliffhanger_field_is_performed(episode)
    assert not any("cliffhanger field" in warning for warning in warnings)


def test_quality_accepts_cliffhanger_field_copied_from_final_hook():
    episode = EpisodeScript(
        episode=2,
        title="道具反问",
        hook_3s="你到底是谁？",
        main_emotion="悬疑",
        watch_reason="系统内部看点。",
        scenes=[
            Scene(
                heading="2-1 夜-内-温家玄关",
                characters=["女主", "温铮"],
                lines=[
                    SceneLine(kind="action", text="△中近景推近女主侧脸，手机屏幕占前景，BGM骤停，切到温铮发白的指节。"),
                    SceneLine(kind="dialogue", speaker="女主", text="这东西，为什么在你手里？"),
                ],
            )
        ],
        cliffhanger="这东西，为什么在你手里？",
        state_update={},
    )

    warnings = episode_quality_warnings(episode)

    assert not has_explanatory_cliffhanger(episode.cliffhanger)
    assert cliffhanger_field_is_performed(episode)
    assert not any("cliffhanger field" in warning for warning in warnings)


def test_quality_accepts_performed_prop_action_cliffhanger():
    episode = EpisodeScript(
        episode=3,
        title="屏幕证据",
        hook_3s="手机亮了。",
        main_emotion="惊",
        watch_reason="系统内部看点。",
        scenes=[
            Scene(
                heading="3-1 夜-内-编辑部",
                characters=["主编"],
                lines=[
                    SceneLine(kind="action", text="△中近景推近主编，手机屏幕占前景，BGM骤停。"),
                    SceneLine(kind="dialogue", speaker="主编", text="谁发来的？"),
                    SceneLine(
                        kind="action",
                        text="△特写定镜，手机屏幕弹出一条新消息：Ellie的心脏还在跳。",
                    ),
                ],
            )
        ],
        cliffhanger="手机屏幕弹出一条新消息：Ellie的心脏还在跳。",
        state_update={},
    )

    warnings = episode_quality_warnings(episode)

    assert not any("cliffhanger is too soft" in warning for warning in warnings)


def test_executable_shot_language_accepts_vertical_camera_moves():
    assert has_executable_shot_language(
        "△特写一只手轻推武植的胳膊，镜头顺手臂上移，定格在金莲担忧的脸上。"
    )


def test_executable_shot_language_accepts_static_closeup():
    assert has_executable_shot_language("△特写武植艰难睁开眼，视线模糊，只剩一点烛光。")


def test_action_line_template_requires_shot_size_and_motion_opening():
    assert has_action_line_template(
        "△中近景推近女主侧脸，手机屏幕占前景，BGM骤停，切到温铮发白的指节。"
    )
    assert has_action_line_template(
        "△EP01 全景横移过生日宴长桌，水晶灯冷光压下；镜头跟拍保安把林晚推到画面中央。"
    )
    assert not has_action_line_template("△女主站在门口。")
    assert not has_action_line_template("△突然有人冲进来。")


def test_quality_warnings_reject_abnormal_repeated_words(happy_round_outputs):
    episode = happy_round_outputs[3].episodes[0].model_copy(deep=True)
    episode.scenes[0].lines[0].text = (
        "△特写推近师傅贪婪贪婪贪婪张大的嘴，切到现金落满桌面。"
    )

    warnings = episode_quality_warnings(episode)

    assert has_abnormal_repetition("师傅贪婪贪婪贪婪张大嘴")
    assert any("abnormal repeated words/phrases" in warning for warning in warnings)


def test_demo_outputs_song_profile_for_haoheng_dasong_source():
    outputs = demo_round_outputs(
        source_text="《豪横大宋》 武植睁眼看见金莲端药，西门庆在清河施压。",
        target_episode_count=30,
    )
    source_analysis = outputs[0]
    script_batch = outputs[3]
    first = script_batch.episodes[0]

    assert "武植" in source_analysis.characters
    assert "金莲" in first.scenes[0].characters
    assert any(
        line.kind == "os" and line.speaker == "武植"
        for scene in first.scenes
        for line in scene.lines
    )
    assert first.watch_reason.startswith("观众要看现代认知")
    assert episode_quality_warnings(first) == []
