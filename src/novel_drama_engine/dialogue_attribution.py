from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from hashlib import sha256
import re

from novel_drama_engine.models import (
    DialogueAttributionCorrection,
    DialogueAttributionReport,
    EpisodeScript,
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    QualityIssue,
    SceneLine,
    ScriptBatch,
    SourceAnalysis,
    SourceDialogueCue,
    SourceSpan,
    StoryBible,
)
from novel_drama_engine.source_facts import build_source_spans


_QUOTE_RE = re.compile(r"“(?P<curly>[^”]+)”|「(?P<corner>[^」]+)」|\"(?P<plain>[^\"\n]+)\"")
_SPEECH_VERBS = (
    "说",
    "道",
    "问",
    "喊",
    "吼",
    "骂",
    "答",
    "开口",
    "低声",
    "冷声",
    "怒声",
    "喝道",
    "嘟囔",
    "结巴",
)
_SPEECH_VERB_RE = "(?:" + "|".join(map(re.escape, _SPEECH_VERBS)) + ")"
_PUNCTUATION = "，,。！？!?；;：:、"


def _character_name(value: str) -> str:
    return re.split(r"[：:｜|]", value, maxsplit=1)[0].strip()


def _known_character_names(
    source_analysis: SourceAnalysis,
    story_bible: StoryBible,
) -> list[str]:
    names = [
        *(_character_name(item) for item in story_bible.characters),
        *(_character_name(item) for item in source_analysis.characters),
    ]
    return list(dict.fromkeys(name for name in names if 1 <= len(name) <= 12))


def _narrator_name(
    source_analysis: SourceAnalysis,
    story_bible: StoryBible,
) -> str | None:
    for item in [*story_bible.characters, *source_analysis.characters]:
        name = _character_name(item)
        if name and ("主角" in item or "女主" in item or "男主" in item):
            return name
    candidates = _known_character_names(source_analysis, story_bible)
    return candidates[0] if candidates else None


def _last_named_character(prefix: str, names: list[str]) -> str | None:
    matches = [
        (prefix.rfind(name), name)
        for name in names
        if prefix.rfind(name) >= 0
    ]
    return max(matches, default=(-1, None))[1]


def _explicit_speaker(prefix: str, names: list[str]) -> str | None:
    tail = prefix[-100:].rstrip(" \t\r\n。！？!?")
    clause = re.split(r"[。！？!?\n]", tail)[-1]
    matched: list[tuple[int, str]] = []
    for name in names:
        for match in re.finditer(
            rf"{re.escape(name)}[^。！？!?\n]{{0,36}}{_SPEECH_VERB_RE}",
            clause,
        ):
            matched.append((match.start(), name))
    if matched:
        return max(matched)[1]
    return _last_named_character(clause, names)


def _first_person_context(prefix: str, names: list[str]) -> bool:
    tail = prefix[-120:].rstrip(" \t\r\n。！？!?")
    clauses = [part.strip() for part in re.split(r"[。！？!?\n]", tail) if part.strip()]
    if not clauses:
        return False
    current = clauses[-1]
    current_has_speech_verb = bool(re.search(_SPEECH_VERB_RE, current))
    first_person_subject = re.compile(
        r"(?:^|[，,])(?:闻言|见状|顿时|这时|下一秒|可|但|于是|接着|片刻|随后)?我(?:们)?"
    )
    if current_has_speech_verb:
        if first_person_subject.search(current):
            return True
        previous = clauses[-2] if len(clauses) >= 2 else ""
        return bool(first_person_subject.search(previous))
    if any(name in tail for name in names):
        return False
    return bool(first_person_subject.search(current))


def _source_span_ids(
    spans: list[SourceSpan],
    *,
    start: int,
    end: int,
) -> list[str]:
    return [span.span_id for span in spans if span.start < end and start < span.end]


def _addressee(text: str, names: list[str], speaker: str) -> str | None:
    for name in names:
        if name == speaker:
            continue
        if re.search(
            rf"(?:^|[，,。！？!?；;：:])\s*{re.escape(name)}\s*[，,：:]",
            text,
        ):
            return name
    return None


def _packet_source_range(
    source_text: str,
    packet: EpisodeSourcePacket,
) -> tuple[int, int]:
    if (
        packet.source_start is not None
        and packet.source_end is not None
        and 0 <= packet.source_start < packet.source_end <= len(source_text)
    ):
        return packet.source_start, packet.source_end
    excerpt = packet.source_excerpt.strip()
    start = source_text.find(excerpt)
    return (start, start + len(excerpt)) if start >= 0 else (0, 0)


def _dialogue_cues_for_packet(
    source_text: str,
    packet: EpisodeSourcePacket,
    *,
    names: list[str],
    narrator: str | None,
    spans: list[SourceSpan],
) -> list[SourceDialogueCue]:
    start, end = _packet_source_range(source_text, packet)
    if end <= start:
        return []
    source_slice = source_text[start:end]
    cues: list[SourceDialogueCue] = []
    previous_quote_end = 0
    last_speaker: str | None = None
    last_confidence: str = "medium"
    for match in _QUOTE_RE.finditer(source_slice):
        text = next(value for value in match.groupdict().values() if value is not None).strip()
        if not text:
            continue
        prefix = source_slice[previous_quote_end : match.start()]
        speaker = _explicit_speaker(prefix, names)
        attribution = "explicit_name"
        confidence = "high"
        if speaker is None and narrator and _first_person_context(prefix, names):
            speaker = narrator
            attribution = "first_person_narrator"
        elif speaker is None and last_speaker is not None and not prefix.strip():
            speaker = last_speaker
            attribution = "context_carry"
            confidence = last_confidence
        elif speaker is None and last_speaker is not None:
            # A name mentioned between two quotes may be the listener, object,
            # or person being discussed. Keep the prior speaker only as a
            # low-trust hint; never let broad context mutate the script.
            speaker = last_speaker
            attribution = "context_carry"
            confidence = "medium"
        if speaker is None:
            previous_quote_end = match.end()
            continue

        absolute_start = start + match.start()
        absolute_end = start + match.end()
        digest = sha256(
            f"{packet.episode}|{speaker}|{absolute_start}|{text}".encode("utf-8")
        ).hexdigest()[:10]
        cues.append(
            SourceDialogueCue(
                cue_id=f"D-EP{packet.episode:02d}-{digest}",
                speaker=speaker,
                text=text,
                source_span_ids=_source_span_ids(
                    spans,
                    start=absolute_start,
                    end=absolute_end,
                ),
                attribution=attribution,
                confidence=confidence,
                addressee=_addressee(text, names, speaker),
            )
        )
        last_speaker = speaker
        last_confidence = confidence
        previous_quote_end = match.end()
    return cues


def enrich_source_packets_with_dialogue_cues(
    source_text: str,
    packets: EpisodeSourcePackets,
    *,
    source_analysis: SourceAnalysis,
    story_bible: StoryBible,
) -> EpisodeSourcePackets:
    names = _known_character_names(source_analysis, story_bible)
    narrator = _narrator_name(source_analysis, story_bible)
    spans = build_source_spans(source_text)
    return packets.model_copy(
        update={
            "packets": [
                packet.model_copy(
                    update={
                        "dialogue_cues": _dialogue_cues_for_packet(
                            source_text,
                            packet,
                            names=names,
                            narrator=narrator,
                            spans=spans,
                        )
                    }
                )
                for packet in packets.packets
            ]
        }
    )


def _normalize_dialogue(value: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", value, flags=re.UNICODE).lower()


@dataclass(frozen=True)
class _MatchedWindow:
    scene_index: int
    line_indexes: tuple[int, ...]
    score: float


def _window_score(source_text: str, candidate_text: str) -> float:
    source = _normalize_dialogue(source_text)
    candidate = _normalize_dialogue(candidate_text)
    if len(candidate) < 4 or len(source) < 4:
        return 0.0
    ratio = SequenceMatcher(None, source, candidate).ratio()
    coverage = min(len(candidate), len(source)) / max(len(source), 1)
    if candidate in source:
        ratio = max(ratio, 0.9)
    return ratio * 0.75 + coverage * 0.25


def _best_window(
    episode: EpisodeScript,
    cue: SourceDialogueCue,
) -> _MatchedWindow | None:
    best: _MatchedWindow | None = None
    for scene_index, scene in enumerate(episode.scenes):
        voiced_indexes = [
            index
            for index, line in enumerate(scene.lines)
            if line.kind in {"dialogue", "os", "vo"}
        ]
        for start in range(len(voiced_indexes)):
            for size in range(1, min(4, len(voiced_indexes) - start) + 1):
                indexes = tuple(voiced_indexes[start : start + size])
                if any(
                    right != left + 1
                    for left, right in zip(indexes, indexes[1:])
                ):
                    continue
                candidate = "".join(scene.lines[index].text for index in indexes)
                score = _window_score(cue.text, candidate)
                if best is None or score > best.score:
                    best = _MatchedWindow(scene_index, indexes, score)
    return best if best is not None and best.score >= 0.52 else None


def _restore_addressee_punctuation(text: str, cue: SourceDialogueCue) -> str:
    addressee = cue.addressee
    if not addressee or addressee not in text:
        return text
    source_pattern = re.search(
        rf"(^|[，,。！？!?；;：:])\s*{re.escape(addressee)}\s*([，,：:])",
        cue.text,
    )
    if source_pattern is None:
        return text
    index = text.find(addressee)
    before = text[index - 1] if index > 0 else ""
    after_index = index + len(addressee)
    after = text[after_index] if after_index < len(text) else ""
    prefix = text[:index]
    suffix = text[after_index:]
    if index > 0 and before not in _PUNCTUATION:
        prefix += "，"
    if after not in _PUNCTUATION:
        suffix = "，" + suffix
    return prefix + addressee + suffix


def _quality_issues_for_episode(
    episode: EpisodeScript,
    packet: EpisodeSourcePacket,
) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    for cue in packet.dialogue_cues:
        if cue.confidence != "high":
            continue
        window = _best_window(episode, cue)
        if window is None:
            continue
        scene = episode.scenes[window.scene_index]
        lines = [scene.lines[index] for index in window.line_indexes]
        wrong_speakers = [line for line in lines if line.speaker != cue.speaker]
        if wrong_speakers:
            issues.append(
                QualityIssue(
                    code="SPEAKER_ATTRIBUTION_CONFLICT",
                    severity="hard",
                    episode=episode.episode,
                    scene_id=scene.scene_id,
                    target_ids=[line.line_id for line in wrong_speakers if line.line_id],
                    evidence=[
                        f"source cue {cue.cue_id}: {cue.speaker}：{cue.text}",
                        *[
                            f"script {line.line_id or '-'}: {line.speaker or '-'}：{line.text}"
                            for line in wrong_speakers
                        ],
                    ],
                    message=(
                        f"EP{episode.episode:02d} 原文对白被分配给错误说话人；"
                        f"应为 {cue.speaker}。"
                    ),
                )
            )
        for line in lines:
            restored = _restore_addressee_punctuation(line.text, cue)
            if restored != line.text:
                issues.append(
                    QualityIssue(
                        code="DIALOGUE_ROLE_CONFLICT",
                        severity="hard",
                        episode=episode.episode,
                        scene_id=scene.scene_id,
                        target_ids=[line.line_id] if line.line_id else [],
                        evidence=[
                            f"source cue {cue.cue_id}: {cue.text}",
                            f"script {line.line_id or '-'}: {line.text}",
                        ],
                        message=(
                            f"EP{episode.episode:02d} 对白压缩改变了称呼对象语义；"
                            f"{cue.addressee} 是被叫的人，不是关系名词的一部分。"
                        ),
                    )
                )
    return issues


def dialogue_attribution_quality_issues(
    script_batch: ScriptBatch,
    packets: EpisodeSourcePackets,
) -> list[QualityIssue]:
    packets_by_episode = {packet.episode: packet for packet in packets.packets}
    return [
        issue
        for episode in script_batch.episodes
        for issue in _quality_issues_for_episode(
            episode,
            packets_by_episode.get(
                episode.episode,
                EpisodeSourcePacket(
                    episode=episode.episode,
                    source_anchor="",
                    source_excerpt="",
                ),
            ),
        )
    ]


def build_dialogue_attribution_report(
    script_batch: ScriptBatch,
    packets: EpisodeSourcePackets,
    *,
    corrections: list[DialogueAttributionCorrection] | None = None,
) -> DialogueAttributionReport:
    return DialogueAttributionReport(
        corrections=list(corrections or []),
        issues=dialogue_attribution_quality_issues(script_batch, packets),
    )


def reconcile_episode_dialogue_roles(
    episode: EpisodeScript,
    packet: EpisodeSourcePacket,
) -> tuple[EpisodeScript, DialogueAttributionReport]:
    corrections: list[DialogueAttributionCorrection] = []
    scenes = [scene.model_copy(deep=True) for scene in episode.scenes]
    working = episode.model_copy(update={"scenes": scenes})
    for cue in packet.dialogue_cues:
        if cue.confidence != "high":
            continue
        window = _best_window(working, cue)
        if window is None:
            continue
        scene = scenes[window.scene_index]
        lines = list(scene.lines)
        for line_index in window.line_indexes:
            line = lines[line_index]
            updates: dict[str, str | None] = {}
            if line.speaker != cue.speaker:
                corrections.append(
                    DialogueAttributionCorrection(
                        episode=episode.episode,
                        scene_id=scene.scene_id,
                        line_id=line.line_id,
                        cue_id=cue.cue_id,
                        field="speaker",
                        before=line.speaker or "",
                        after=cue.speaker,
                    )
                )
                updates["speaker"] = cue.speaker
                if line.emotion:
                    corrections.append(
                        DialogueAttributionCorrection(
                            episode=episode.episode,
                            scene_id=scene.scene_id,
                            line_id=line.line_id,
                            cue_id=cue.cue_id,
                            field="emotion",
                            before=line.emotion,
                            after="",
                        )
                    )
                    updates["emotion"] = None
            restored = _restore_addressee_punctuation(line.text, cue)
            if restored != line.text:
                corrections.append(
                    DialogueAttributionCorrection(
                        episode=episode.episode,
                        scene_id=scene.scene_id,
                        line_id=line.line_id,
                        cue_id=cue.cue_id,
                        field="addressee_punctuation",
                        before=line.text,
                        after=restored,
                    )
                )
                updates["text"] = restored
                if working.cliffhanger == line.text:
                    working = working.model_copy(update={"cliffhanger": restored})
            if updates:
                lines[line_index] = line.model_copy(update=updates)
        characters = list(scene.characters)
        if any(lines[index].speaker == cue.speaker for index in window.line_indexes):
            if cue.speaker not in characters:
                characters.append(cue.speaker)
        scenes[window.scene_index] = scene.model_copy(
            update={"lines": lines, "characters": characters}
        )
        working = working.model_copy(update={"scenes": scenes})

    issues = _quality_issues_for_episode(working, packet)
    return working, DialogueAttributionReport(corrections=corrections, issues=issues)


def reconcile_script_batch_dialogue_roles(
    script_batch: ScriptBatch,
    packets: EpisodeSourcePackets,
) -> tuple[ScriptBatch, DialogueAttributionReport]:
    packets_by_episode = {packet.episode: packet for packet in packets.packets}
    corrections: list[DialogueAttributionCorrection] = []
    episodes: list[EpisodeScript] = []
    for episode in script_batch.episodes:
        packet = packets_by_episode.get(episode.episode)
        if packet is None:
            episodes.append(episode)
            continue
        reconciled, report = reconcile_episode_dialogue_roles(episode, packet)
        episodes.append(reconciled)
        corrections.extend(report.corrections)

    reconciled_batch = script_batch.model_copy(update={"episodes": episodes})
    return reconciled_batch, build_dialogue_attribution_report(
        reconciled_batch,
        packets,
        corrections=corrections,
    )
