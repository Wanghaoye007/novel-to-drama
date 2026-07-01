from novel_drama_engine.demo import demo_round_outputs
from novel_drama_engine.models import EpisodeScript, Scene, SceneLine
from novel_drama_engine.script_quality import (
    episode_quality_metrics,
    episode_quality_warnings,
    has_executable_shot_language,
    script_batch_quality_warnings,
)


def test_happy_demo_outputs_meet_reference_script_density(happy_round_outputs):
    script_batch = happy_round_outputs[3]

    for episode in script_batch.episodes:
        metrics = episode_quality_metrics(episode)
        assert metrics.chars >= 800
        assert metrics.scenes >= 2
        assert metrics.action_lines >= 8
        assert metrics.voiced_lines >= 16
        assert metrics.shot_language_lines >= 8
        assert metrics.long_voiced_lines == 0
        assert metrics.invalid_scene_headings == 0
        assert episode_quality_warnings(episode) == []


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


def test_batch_quality_warnings_reject_episode_range_mismatch(happy_round_outputs):
    script_batch = happy_round_outputs[3]

    warnings = script_batch_quality_warnings(script_batch, "EP01-EP01")

    assert any("mismatch target range EP01-EP01" in warning for warning in warnings)
    assert any("got EP01,EP02,EP03,EP04,EP05" in warning for warning in warnings)


def test_batch_quality_warnings_accept_expected_episode_range(happy_round_outputs):
    script_batch = happy_round_outputs[3]

    assert script_batch_quality_warnings(script_batch, "EP01-EP05") == []


def test_executable_shot_language_accepts_vertical_camera_moves():
    assert has_executable_shot_language(
        "△特写一只手轻推武植的胳膊，镜头顺手臂上移，定格在金莲担忧的脸上。"
    )


def test_executable_shot_language_accepts_static_closeup():
    assert has_executable_shot_language("△特写武植艰难睁开眼，视线模糊，只剩一点烛光。")


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
