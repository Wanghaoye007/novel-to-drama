from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re

from novel_drama_engine.models import (
    EpisodeBeat,
    EpisodeScript,
    RepairPatch,
    RepairPatchBatch,
    Scene,
    SceneLine,
    SourceFact,
)


def _stable_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def line_content_hash(line: SceneLine) -> str:
    """Hash the mutable line payload, excluding its stable identity."""
    return _stable_hash(
        {
            "kind": line.kind,
            "text": line.text,
            "speaker": line.speaker,
            "emotion": line.emotion,
        }
    )


def scene_heading_hash(scene: Scene) -> str:
    return _stable_hash(scene.heading)


def canonicalize_episode_nodes(episode: EpisodeScript) -> EpisodeScript:
    """Normalize node IDs without trusting provider-provided identities."""
    canonical = episode.model_copy(deep=True)
    normalized_scenes: list[Scene] = []
    for scene_index, scene in enumerate(canonical.scenes, start=1):
        expected_scene_id = f"EP{canonical.episode:02d}-S{scene_index:02d}"
        normalized_lines: list[SceneLine] = []
        for line_index, line in enumerate(scene.lines, start=1):
            expected_line_id = f"{expected_scene_id}-L{line_index:02d}"
            normalized_lines.append(line.model_copy(update={"line_id": expected_line_id}))
        normalized_scenes.append(
            scene.model_copy(
                update={"scene_id": expected_scene_id, "lines": normalized_lines}
            )
        )
    return canonical.model_copy(update={"scenes": normalized_scenes})


def build_authorized_repair_patches(
    episode: EpisodeScript,
    *,
    repair_mode: str,
    issue_code: str,
    target_line_ids: list[str] | None = None,
    target_scene_ids: list[str] | None = None,
    required_fact_ids: list[str] | None = None,
    forbidden_fact_ids: list[str] | None = None,
    preserve_beat_ids: list[str] | None = None,
    preserve_state_after: list[str] | None = None,
) -> list[RepairPatch]:
    """Create the immutable patch allow-list before the repair model runs."""
    canonical = canonicalize_episode_nodes(episode)
    line_locations = _line_locations(canonical)
    scene_locations = _scene_locations(canonical)
    line_ids = list(dict.fromkeys(target_line_ids or []))
    scene_ids = list(dict.fromkeys(target_scene_ids or []))

    # A repair mode is a description, not an authorization. The only writable
    # nodes are the scene/line IDs carried by a structured QualityIssue.
    # This deliberately leaves legacy free-text findings with an empty patch
    # list instead of expanding them to an entire opening, ending, or scene.

    patches: list[RepairPatch] = []
    for scene_id in scene_ids:
        scene_index = scene_locations.get(scene_id)
        if scene_index is None:
            continue
        scene = canonical.scenes[scene_index]
        patches.append(
            RepairPatch(
                patch_id=f"P-EP{canonical.episode:02d}-{len(patches) + 1:02d}",
                episode=canonical.episode,
                scene_id=scene_id,
                target_type="scene_heading",
                target_ids=[scene_id],
                operation="replace",
                expected_before_hash=scene_heading_hash(scene),
                issue_code=issue_code,
                required_fact_ids=list(required_fact_ids or []),
                forbidden_fact_ids=list(forbidden_fact_ids or []),
                preserve_beat_ids=list(preserve_beat_ids or []),
                preserve_state_after=list(preserve_state_after or []),
            )
        )
    for line_id in line_ids:
        location = line_locations.get(line_id)
        if location is None:
            continue
        scene_index, line_index = location
        scene = canonical.scenes[scene_index]
        line = scene.lines[line_index]
        patches.append(
            RepairPatch(
                patch_id=f"P-EP{canonical.episode:02d}-{len(patches) + 1:02d}",
                episode=canonical.episode,
                scene_id=scene.scene_id,
                target_type=_line_target_type(line),
                target_ids=[line_id],
                operation="replace",
                expected_before_hash=line_content_hash(line),
                issue_code=issue_code,
                required_fact_ids=list(required_fact_ids or []),
                forbidden_fact_ids=list(forbidden_fact_ids or []),
                preserve_beat_ids=list(preserve_beat_ids or []),
                preserve_state_after=list(preserve_state_after or []),
            )
        )
    return patches


@dataclass(frozen=True)
class PatchApplicationResult:
    accepted: bool
    episode: EpisodeScript
    applied_patch_ids: list[str]
    rejections: list[str]
    audit: list[dict[str, object]]


def _compact(value: str) -> str:
    return re.sub(r"[\s\W_]+", "", value).lower()


def _line_target_type(line: SceneLine) -> str:
    return "action" if line.kind == "action" else "dialogue"


def _line_locations(episode: EpisodeScript) -> dict[str, tuple[int, int]]:
    return {
        line.line_id: (scene_index, line_index)
        for scene_index, scene in enumerate(episode.scenes)
        for line_index, line in enumerate(scene.lines)
        if line.line_id
    }


def _scene_locations(episode: EpisodeScript) -> dict[str, int]:
    return {
        scene.scene_id: scene_index
        for scene_index, scene in enumerate(episode.scenes)
        if scene.scene_id
    }


def _authorization_mismatch(candidate: RepairPatch, allowed: RepairPatch) -> str | None:
    fields = (
        "episode",
        "scene_id",
        "target_type",
        "target_ids",
        "operation",
        "expected_before_hash",
        "issue_code",
        "required_fact_ids",
        "forbidden_fact_ids",
        "preserve_beat_ids",
        "preserve_state_after",
    )
    if any(getattr(candidate, field) != getattr(allowed, field) for field in fields):
        return "patch does not match the system-authorized target"
    return None


def _protected_fact_ids(patch: RepairPatch, beats: list[EpisodeBeat]) -> set[str]:
    protected: set[str] = set()
    for beat in beats:
        if beat.beat_id in patch.preserve_beat_ids:
            protected.update(beat.required_fact_ids)
    return protected


def _validate_fact_preservation(
    *,
    patch: RepairPatch,
    before_text: str,
    after_text: str,
    facts_by_id: dict[str, SourceFact],
    beats: list[EpisodeBeat],
) -> str | None:
    for fact_id in _protected_fact_ids(patch, beats):
        fact = facts_by_id.get(fact_id)
        if fact is None:
            continue
        evidence = _compact(fact.content)
        if evidence and evidence in _compact(before_text) and evidence not in _compact(after_text):
            return f"patch removes protected source fact {fact_id}"
    for fact_id in patch.forbidden_fact_ids:
        fact = facts_by_id.get(fact_id)
        if fact is not None and _compact(fact.content) in _compact(after_text):
            return f"patch introduces forbidden source fact {fact_id}"
    return None


def _verify_untouched_nodes(
    baseline: EpisodeScript,
    candidate: EpisodeScript,
    *,
    target_ids: set[str],
) -> str | None:
    baseline_lines = {
        line.line_id: line.model_dump(mode="json")
        for scene in baseline.scenes
        for line in scene.lines
        if line.line_id
    }
    candidate_lines = {
        line.line_id: line.model_dump(mode="json")
        for scene in candidate.scenes
        for line in scene.lines
        if line.line_id
    }
    for line_id, before in baseline_lines.items():
        if line_id in target_ids:
            continue
        if candidate_lines.get(line_id) != before:
            return f"patch changed non-target node {line_id}"
    baseline_scenes = {
        scene.scene_id: scene
        for scene in baseline.scenes
        if scene.scene_id
    }
    candidate_scenes = {
        scene.scene_id: scene
        for scene in candidate.scenes
        if scene.scene_id
    }
    for scene_id, before in baseline_scenes.items():
        if scene_id in target_ids:
            continue
        after = candidate_scenes.get(scene_id)
        if after is None or after.heading != before.heading or after.characters != before.characters:
            return f"patch changed non-target scene {scene_id}"
    return None


def apply_repair_patch_batch(
    baseline: EpisodeScript,
    patch_batch: RepairPatchBatch,
    *,
    allowed_patches: list[RepairPatch],
    source_facts: list[SourceFact] | None = None,
    episode_beats: list[EpisodeBeat] | None = None,
) -> PatchApplicationResult:
    """Apply model patch output only when every operation matches system scope."""
    original = canonicalize_episode_nodes(baseline)
    if patch_batch.episode != original.episode:
        return PatchApplicationResult(
            accepted=False,
            episode=original,
            applied_patch_ids=[],
            rejections=["patch batch episode does not match baseline"],
            audit=[],
        )
    if not patch_batch.patches:
        return PatchApplicationResult(
            accepted=False,
            episode=original,
            applied_patch_ids=[],
            rejections=["repair model returned no patches"],
            audit=[],
        )

    allowed_by_id = {patch.patch_id: patch for patch in allowed_patches if patch.patch_id}
    seen_patch_ids: set[str] = set()
    candidate = original.model_copy(deep=True)
    facts_by_id = {fact.fact_id: fact for fact in source_facts or []}
    beats = episode_beats or []
    target_ids: set[str] = set()
    audit: list[dict[str, object]] = []

    for patch in patch_batch.patches:
        if not patch.patch_id or patch.patch_id in seen_patch_ids:
            return PatchApplicationResult(
                accepted=False,
                episode=original,
                applied_patch_ids=[],
                rejections=["patch id is missing or duplicated"],
                audit=audit,
            )
        seen_patch_ids.add(patch.patch_id)
        allowed = allowed_by_id.get(patch.patch_id)
        if allowed is None:
            return PatchApplicationResult(
                accepted=False,
                episode=original,
                applied_patch_ids=[],
                rejections=["patch id is not system-authorized"],
                audit=audit,
            )
        mismatch = _authorization_mismatch(patch, allowed)
        if mismatch:
            return PatchApplicationResult(
                accepted=False,
                episode=original,
                applied_patch_ids=[],
                rejections=[mismatch],
                audit=audit,
            )
        if patch.episode != original.episode or patch.replacement is None:
            return PatchApplicationResult(
                accepted=False,
                episode=original,
                applied_patch_ids=[],
                rejections=["patch has an invalid episode or replacement"],
                audit=audit,
            )
        if patch.target_type == "scene_heading":
            if len(patch.target_ids) != 1 or patch.target_ids[0] != patch.scene_id:
                return PatchApplicationResult(False, original, [], ["scene heading patch has invalid target IDs"], audit)
            scene_locations = _scene_locations(candidate)
            scene_index = scene_locations.get(patch.scene_id or "")
            if scene_index is None:
                return PatchApplicationResult(False, original, [], ["scene heading target is missing"], audit)
            scene = candidate.scenes[scene_index]
            if scene_heading_hash(scene) != patch.expected_before_hash:
                return PatchApplicationResult(False, original, [], ["expected_before_hash does not match scene heading"], audit)
            candidate.scenes[scene_index] = scene.model_copy(update={"heading": patch.replacement})
            target_ids.add(patch.scene_id or "")
            audit.append({"patch_id": patch.patch_id, "target_ids": patch.target_ids, "accepted": True})
            continue
        if patch.target_type not in {"action", "dialogue"} or len(patch.target_ids) != 1:
            return PatchApplicationResult(False, original, [], ["patch target type is unsupported"], audit)
        line_id = patch.target_ids[0]
        line_locations = _line_locations(candidate)
        location = line_locations.get(line_id)
        if location is None:
            return PatchApplicationResult(False, original, [], ["patch line target is missing"], audit)
        scene_index, line_index = location
        scene = candidate.scenes[scene_index]
        line = scene.lines[line_index]
        if scene.scene_id != patch.scene_id or _line_target_type(line) != patch.target_type:
            return PatchApplicationResult(False, original, [], ["patch target does not match scene or line type"], audit)
        if line_content_hash(line) != patch.expected_before_hash:
            return PatchApplicationResult(False, original, [], ["expected_before_hash does not match line"], audit)
        fact_error = _validate_fact_preservation(
            patch=patch,
            before_text=line.text,
            after_text=patch.replacement,
            facts_by_id=facts_by_id,
            beats=beats,
        )
        if fact_error:
            return PatchApplicationResult(False, original, [], [fact_error], audit)
        lines = list(scene.lines)
        lines[line_index] = line.model_copy(update={"text": patch.replacement})
        candidate.scenes[scene_index] = scene.model_copy(update={"lines": lines})
        target_ids.add(line_id)
        audit.append({"patch_id": patch.patch_id, "target_ids": patch.target_ids, "accepted": True})

    untouched_error = _verify_untouched_nodes(original, candidate, target_ids=target_ids)
    if untouched_error:
        return PatchApplicationResult(False, original, [], [untouched_error], audit)
    if candidate.state_update != original.state_update:
        return PatchApplicationResult(False, original, [], ["patch changed protected state_update"], audit)
    return PatchApplicationResult(
        accepted=True,
        episode=candidate,
        applied_patch_ids=[patch.patch_id for patch in patch_batch.patches],
        rejections=[],
        audit=audit,
    )
