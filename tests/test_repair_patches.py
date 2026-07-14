import pytest
from pydantic import ValidationError

from novel_drama_engine.models import (
    EpisodeBeat,
    EpisodeScript,
    QualityIssue,
    RepairPatch,
    RepairPatchBatch,
    Scene,
    SceneLine,
    SourceFact,
)
from novel_drama_engine.rounds import ScriptBatchGenerator
from novel_drama_engine.script_quality import build_current_episode_repair_packet
from novel_drama_engine.repair_patches import (
    apply_repair_patch_batch,
    line_content_hash,
)


def _episode() -> EpisodeScript:
    return EpisodeScript(
        episode=1,
        title="合同风波",
        hook_3s="别碰那份合同。",
        main_emotion="压迫",
        watch_reason="系统内部字段",
        scenes=[
            Scene(
                heading="1-1 夜-内-会议室",
                characters=["林晚", "赵明"],
                lines=[
                    SceneLine(kind="action", text="△近景推近林晚攥住合同边角。"),
                    SceneLine(kind="dialogue", speaker="林晚", text="我不签。"),
                    SceneLine(kind="dialogue", speaker="赵明", text="由不得你。"),
                ],
            ),
            Scene(
                heading="1-2 夜-内-会议室门口",
                characters=["林晚", "赵明"],
                lines=[
                    SceneLine(kind="action", text="△中景跟拍赵明夺走合同。"),
                    SceneLine(kind="dialogue", speaker="赵明", text="合同归我。"),
                ],
            ),
        ],
        cliffhanger="合同归我。",
        state_update={"contract": "赵明拿走"},
    )


def _patch(
    episode: EpisodeScript,
    *,
    patch_id: str = "P-EP01-01",
    target_id: str = "EP01-S01-L02",
    replacement: str = "我不会签。",
    expected_before_hash: str | None = None,
    preserve_beat_ids: list[str] | None = None,
) -> RepairPatch:
    line = next(
        line
        for scene in episode.scenes
        for line in scene.lines
        if line.line_id == target_id
    )
    return RepairPatch(
        patch_id=patch_id,
        episode=episode.episode,
        scene_id="EP01-S01",
        target_type="dialogue",
        target_ids=[target_id],
        operation="replace",
        expected_before_hash=expected_before_hash or line_content_hash(line),
        replacement=replacement,
        issue_code="MISSING_REQUIRED_FACT",
        required_fact_ids=[],
        forbidden_fact_ids=[],
        preserve_beat_ids=preserve_beat_ids or [],
        preserve_state_after=["contract"],
    )


def test_episode_script_canonicalizes_stable_scene_and_line_ids():
    episode = _episode()

    assert [scene.scene_id for scene in episode.scenes] == ["EP01-S01", "EP01-S02"]
    assert [line.line_id for line in episode.scenes[0].lines] == [
        "EP01-S01-L01",
        "EP01-S01-L02",
        "EP01-S01-L03",
    ]


def test_episode_script_does_not_trust_model_supplied_node_ids():
    episode = _episode().model_copy(deep=True)
    episode.scenes[0].scene_id = "model-scene"
    episode.scenes[0].lines[0].line_id = "model-line"

    canonical = EpisodeScript.model_validate(episode.model_dump(mode="json"))

    assert canonical.scenes[0].scene_id == "EP01-S01"
    assert canonical.scenes[0].lines[0].line_id == "EP01-S01-L01"


def test_patch_with_stale_before_hash_is_rejected_without_mutating_baseline():
    episode = _episode()
    patch = _patch(episode, expected_before_hash="stale")

    result = apply_repair_patch_batch(
        episode,
        RepairPatchBatch(episode=1, patches=[patch]),
        allowed_patches=[patch],
    )

    assert result.accepted is False
    assert result.episode == episode
    assert "expected_before_hash does not match" in result.rejections[0]


def test_patch_cannot_escape_its_authorized_scene_or_line():
    episode = _episode()
    allowed_patch = _patch(episode)
    foreign_patch = allowed_patch.model_copy(
        update={
            "scene_id": "EP01-S02",
            "target_ids": ["EP01-S02-L02"],
        }
    )

    result = apply_repair_patch_batch(
        episode,
        RepairPatchBatch(episode=1, patches=[foreign_patch]),
        allowed_patches=[allowed_patch],
    )

    assert result.accepted is False
    assert result.episode == episode
    assert "does not match the system-authorized target" in result.rejections[0]


def test_patch_batch_with_an_extra_unauthorized_patch_is_rejected_atomically():
    episode = _episode()
    allowed_patch = _patch(episode)
    overflow_patch = _patch(
        episode,
        patch_id="P-EP01-02",
        target_id="EP01-S01-L03",
        replacement="你没资格逼我。",
    )

    result = apply_repair_patch_batch(
        episode,
        RepairPatchBatch(episode=1, patches=[allowed_patch, overflow_patch]),
        allowed_patches=[allowed_patch],
    )

    assert result.accepted is False
    assert result.episode == episode
    assert result.applied_patch_ids == []
    assert result.rejections == ["patch id is not system-authorized"]


def test_patch_protocol_rejects_insert_delete_and_scene_block_operations():
    episode = _episode()
    patch = _patch(episode)

    with pytest.raises(ValidationError):
        RepairPatch.model_validate(
            {**patch.model_dump(mode="json"), "operation": "delete"}
        )
    with pytest.raises(ValidationError):
        RepairPatch.model_validate(
            {**patch.model_dump(mode="json"), "target_type": "scene_block"}
        )


def test_patch_cannot_reverse_a_protected_source_fact_in_a_beat():
    episode = _episode().model_copy(deep=True)
    episode.scenes[0].lines[1].text = "林晚拒绝签署合同。"
    source_fact = SourceFact(
        fact_id="F-contract-refusal",
        content="林晚拒绝签署合同。",
        source_span_ids=["S-00000000-00000009-abc12345"],
        fact_type="event",
        fact_types=["event"],
        confidence=1.0,
        status="source_confirmed",
    )
    beat = EpisodeBeat(
        beat_id="EP01-B01",
        event=source_fact.content,
        source_span_ids=source_fact.source_span_ids,
        required_fact_ids=[source_fact.fact_id],
    )
    patch = _patch(
        episode,
        replacement="林晚签署合同。",
        preserve_beat_ids=[beat.beat_id],
    )

    result = apply_repair_patch_batch(
        episode,
        RepairPatchBatch(episode=1, patches=[patch]),
        allowed_patches=[patch],
        source_facts=[source_fact],
        episode_beats=[beat],
    )

    assert result.accepted is False
    assert result.episode == episode
    assert "removes protected source fact F-contract-refusal" in result.rejections[0]


def test_patch_changes_only_its_target_line_and_preserves_other_nodes_verbatim():
    episode = _episode()
    patch = _patch(episode)

    result = apply_repair_patch_batch(
        episode,
        RepairPatchBatch(episode=1, patches=[patch]),
        allowed_patches=[patch],
    )

    assert result.accepted is True
    assert result.episode.scenes[0].lines[1].text == "我不会签。"
    assert result.episode.scenes[0].lines[2] == episode.scenes[0].lines[2]
    assert result.episode.scenes[1] == episode.scenes[1]


def test_repair_generator_requests_patch_batch_not_full_episode(happy_round_outputs):
    source_analysis, episode_context, story_bible, script_batch, _, previous_context = (
        happy_round_outputs
    )
    existing_episode = script_batch.episodes[0]
    repair_packet = build_current_episode_repair_packet(
        existing_episode,
        "EP01 action format is invalid",
    )

    class CapturingLLM:
        def __init__(self) -> None:
            self.response_model = None
            self.user = ""

        def complete(self, *, system, user, response_model):
            self.response_model = response_model
            self.user = user
            return RepairPatchBatch(episode=1, patches=[])

    llm = CapturingLLM()
    result = ScriptBatchGenerator(llm).run_repair_patches(
        "林晚拒绝签合同。",
        source_analysis,
        episode_context,
        story_bible,
        previous_context,
        existing_episode,
        1,
        "只修指定 action 行。",
        current_episode_repair_packet=repair_packet,
    )

    assert result == RepairPatchBatch(episode=1, patches=[])
    assert llm.response_model is RepairPatchBatch
    assert "RepairPatchBatch" in llm.user
    assert "不得输出 EpisodeScript" in llm.user


def test_repair_packet_authorizes_only_stable_node_bound_patches():
    episode = _episode()

    packet = build_current_episode_repair_packet(
        episode,
        "EP01 action lines violating format",
        quality_issue=QualityIssue(
            code="STRUCTURE_INVALID",
            severity="hard",
            episode=episode.episode,
            scene_id=episode.scenes[0].scene_id,
            target_ids=[episode.scenes[0].lines[0].line_id],
            evidence=[episode.scenes[0].lines[0].text],
            message="EP01 action line violates the shooting format.",
        ),
    )

    assert packet.repair_mode == "format_patch"
    assert packet.repair_patches
    assert all(patch.patch_id.startswith("P-EP01-") for patch in packet.repair_patches)
    assert all(patch.scene_id for patch in packet.repair_patches)
    assert all(patch.target_ids for patch in packet.repair_patches)
    assert all(patch.expected_before_hash for patch in packet.repair_patches)
    assert all(patch.target is None for patch in packet.repair_patches)
    assert all(patch.issue is None for patch in packet.repair_patches)
