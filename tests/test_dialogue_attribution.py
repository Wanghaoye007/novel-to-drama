from novel_drama_engine.dialogue_attribution import (
    dialogue_attribution_quality_issues,
    enrich_source_packets_with_dialogue_cues,
    reconcile_episode_dialogue_roles,
    reconcile_script_batch_dialogue_roles,
)
from novel_drama_engine.models import (
    EpisodeScript,
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    Scene,
    SceneLine,
    ScriptBatch,
    SourceAnalysis,
    StoryBible,
)


def _source_analysis() -> SourceAnalysis:
    return SourceAnalysis(
        characters=[
            "张雅：重生主角，今生不再替苏夏背锅",
            "苏夏：张雅前闺蜜，江毅妻子",
            "江毅：苏夏丈夫，前期误解张雅",
        ],
        events=[],
        conflicts=[],
        visual_moments=[],
        low_value_passages=[],
        candidate_hooks=[],
    )


def _story_bible() -> StoryBible:
    return StoryBible(
        genre="都市重生",
        mainline="重生后的张雅不再替苏夏背锅。",
        characters=[
            "张雅｜重生复仇主角",
            "苏夏｜张雅前闺蜜",
            "江毅｜苏夏丈夫",
        ],
        relationships=["江毅与苏夏：夫妻", "张雅与苏夏：前闺蜜"],
        speech_styles={"张雅": "冷静", "江毅": "强势"},
        immutable_facts=[],
        forbidden_changes=[],
    )


def _source_and_packets() -> tuple[str, EpisodeSourcePackets]:
    source = """# EPISODE 2

闻言我忍不住讥讽地笑了起来。
“你都知道她是个母亲，一个成年人有手有脚，我能管得了她去哪里？她妈都管不住她。”

# EPISODE 3

听见我的话，江毅不屑地笑了。
“这就受不了了？我还有更过分的。”
“拿了一千万，又卖掉了我的车，现在还要拐走我老婆，张雅，我真是给你脸太多了！”
"""
    ep2_start = source.index("# EPISODE 2")
    ep3_start = source.index("# EPISODE 3")
    return source, EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=2,
                source_anchor="# EPISODE 2",
                source_excerpt=source[ep2_start:ep3_start].strip(),
                source_start=ep2_start,
                source_end=ep3_start,
            ),
            EpisodeSourcePacket(
                episode=3,
                source_anchor="# EPISODE 3",
                source_excerpt=source[ep3_start:].strip(),
                source_start=ep3_start,
                source_end=len(source),
            ),
        ]
    )


def _enriched_packets() -> EpisodeSourcePackets:
    source, packets = _source_and_packets()
    return enrich_source_packets_with_dialogue_cues(
        source,
        packets,
        source_analysis=_source_analysis(),
        story_bible=_story_bible(),
    )


def test_source_dialogue_cues_resolve_first_person_speaker_and_vocative_addressee():
    packets = _enriched_packets()
    ep2, ep3 = packets.packets

    first_person = next(cue for cue in ep2.dialogue_cues if cue.text.startswith("你都知道"))
    assert first_person.speaker == "张雅"
    assert first_person.attribution == "first_person_narrator"
    assert first_person.confidence == "high"

    vocative = next(cue for cue in ep3.dialogue_cues if "拿了一千万" in cue.text)
    assert vocative.speaker == "江毅"
    assert vocative.addressee == "张雅"
    assert vocative.confidence == "high"
    assert vocative.source_span_ids


def test_reconcile_episode_dialogue_roles_fixes_split_lines_and_vocative_punctuation():
    packets = _enriched_packets()
    ep2_packet, ep3_packet = packets.packets
    ep2 = EpisodeScript(
        episode=2,
        title="误认",
        hook_3s="张雅冷笑",
        main_emotion="压迫",
        watch_reason="看张雅反击",
        scenes=[
            Scene(
                scene_id="EP02-S01",
                heading="2-1 夜-内-张雅出租屋",
                characters=["张雅", "江毅"],
                lines=[
                    SceneLine(line_id="EP02-S01-L01", kind="action", text="张雅冷笑"),
                    SceneLine(
                        line_id="EP02-S01-L02",
                        kind="dialogue",
                        speaker="江毅",
                        emotion="烦躁",
                        text="你都知道她是个母亲",
                    ),
                    SceneLine(line_id="EP02-S01-L03", kind="dialogue", speaker="江毅", text="成年人有手有脚管不住她"),
                    SceneLine(line_id="EP02-S01-L04", kind="dialogue", speaker="江毅", text="她妈都管不住她"),
                ],
            )
        ],
        cliffhanger="她妈都管不住她",
        state_update={},
    )
    ep3 = EpisodeScript(
        episode=3,
        title="逼问",
        hook_3s="江毅冷笑",
        main_emotion="压迫",
        watch_reason="看江毅逼问",
        scenes=[
            Scene(
                scene_id="EP03-S01",
                heading="3-1 夜-内-张雅出租屋",
                characters=["张雅", "江毅"],
                lines=[
                    SceneLine(line_id="EP03-S01-L01", kind="action", text="江毅冷笑"),
                    SceneLine(
                        line_id="EP03-S01-L02",
                        kind="dialogue",
                        speaker="江毅",
                        text="还拐走我老婆张雅，给你脸太多",
                    ),
                ],
            )
        ],
        cliffhanger="还拐走我老婆张雅，给你脸太多",
        state_update={},
    )

    fixed_ep2, ep2_report = reconcile_episode_dialogue_roles(ep2, ep2_packet)
    fixed_ep3, ep3_report = reconcile_episode_dialogue_roles(ep3, ep3_packet)

    assert [line.speaker for line in fixed_ep2.scenes[0].lines[1:]] == [
        "张雅",
        "张雅",
        "张雅",
    ]
    assert fixed_ep2.scenes[0].lines[1].emotion is None
    assert fixed_ep3.scenes[0].lines[1].text == "还拐走我老婆，张雅，给你脸太多"
    assert len(ep2_report.corrections) == 4
    assert len(ep3_report.corrections) == 1


def test_speaker_conflicts_are_node_scoped_hard_quality_issues():
    ep2_packet = _enriched_packets().packets[0]
    episode = EpisodeScript(
        episode=2,
        title="误认",
        hook_3s="张雅冷笑",
        main_emotion="压迫",
        watch_reason="看张雅反击",
        scenes=[
            Scene(
                scene_id="EP02-S01",
                heading="2-1 夜-内-张雅出租屋",
                characters=["张雅", "江毅"],
                lines=[
                    SceneLine(line_id="EP02-S01-L01", kind="action", text="张雅冷笑"),
                    SceneLine(line_id="EP02-S01-L02", kind="dialogue", speaker="江毅", text="你都知道她是个母亲"),
                    SceneLine(line_id="EP02-S01-L03", kind="dialogue", speaker="江毅", text="成年人有手有脚管不住她"),
                    SceneLine(line_id="EP02-S01-L04", kind="dialogue", speaker="江毅", text="她妈都管不住她"),
                ],
            )
        ],
        cliffhanger="她妈都管不住她",
        state_update={},
    )

    issues = dialogue_attribution_quality_issues(
        ScriptBatch(episodes=[episode]),
        EpisodeSourcePackets(packets=[ep2_packet]),
    )

    assert len(issues) == 1
    issue = issues[0]
    assert issue.code == "SPEAKER_ATTRIBUTION_CONFLICT"
    assert issue.severity == "hard"
    assert issue.episode == 2
    assert issue.scene_id == "EP02-S01"
    assert issue.target_ids == ["EP02-S01-L02", "EP02-S01-L03", "EP02-S01-L04"]


def test_named_context_between_quotes_is_not_promoted_to_high_confidence_speaker():
    source = """# EPISODE 4

我冷笑着开口：“不如你问问你的助理？”
江毅狐疑地拿出手机给助理拨出电话。
接通那刻，喘息声戛然而止。
“怎么了江总？”
“给我查一下苏夏的位置。”
"""
    packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=4,
                source_anchor="# EPISODE 4",
                source_excerpt=source,
                source_start=0,
                source_end=len(source),
            )
        ]
    )

    enriched = enrich_source_packets_with_dialogue_cues(
        source,
        packets,
        source_analysis=_source_analysis(),
        story_bible=_story_bible(),
    )

    first_cue = next(
        cue for cue in enriched.packets[0].dialogue_cues if cue.text == "怎么了江总？"
    )
    assert first_cue.confidence == "medium"


def test_pronoun_chain_after_multiple_named_characters_is_not_auto_corrected():
    source = """# EPISODE 1

江毅冷声道：“夏夏呢？”
江毅在苏夏潜移默化的影响里，早就对我心生恨意。
见我不出声，他一个眼神射向旁边。
他上前一步捏着我的下颌，咬牙道：“我再给你最后一次机会，夏夏去哪了？”
"""
    packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=1,
                source_anchor="# EPISODE 1",
                source_excerpt=source,
                source_start=0,
                source_end=len(source),
            )
        ]
    )

    enriched = enrich_source_packets_with_dialogue_cues(
        source,
        packets,
        source_analysis=_source_analysis(),
        story_bible=_story_bible(),
    )

    cue = next(
        cue
        for cue in enriched.packets[0].dialogue_cues
        if cue.text.startswith("我再给你最后一次机会")
    )
    assert cue.confidence == "medium"


def test_reconcile_script_batch_applies_the_same_source_lock_to_cached_batches():
    packet = _enriched_packets().packets[0]
    episode = EpisodeScript(
        episode=2,
        title="误认",
        hook_3s="张雅冷笑",
        main_emotion="压迫",
        watch_reason="看张雅反击",
        scenes=[
            Scene(
                scene_id="EP02-S01",
                heading="2-1 夜-内-张雅出租屋",
                characters=["张雅", "江毅"],
                lines=[
                    SceneLine(
                        line_id="EP02-S01-L01",
                        kind="dialogue",
                        speaker="江毅",
                        text="你都知道她是个母亲",
                    )
                ],
            )
        ],
        cliffhanger="你都知道她是个母亲",
        state_update={},
    )

    fixed, report = reconcile_script_batch_dialogue_roles(
        ScriptBatch(episodes=[episode]),
        EpisodeSourcePackets(packets=[packet]),
    )

    assert fixed.episodes[0].scenes[0].lines[0].speaker == "张雅"
    assert report.corrections[0].line_id == "EP02-S01-L01"
    assert report.issues == []
