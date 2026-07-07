from novel_drama_engine.demo import demo_round_outputs
from novel_drama_engine.models import (
    EpisodeScript,
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    Scene,
    SceneLine,
    ScriptBatch,
    QualityReport,
    QualityScores,
    QualityStatus,
)
from novel_drama_engine.source_evidence import (
    build_source_evidence_report,
    merge_source_evidence_into_quality_report,
    render_source_evidence_report,
)


def test_source_evidence_report_matches_retained_assets_in_script():
    script_batch = demo_round_outputs()[3]
    packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=1,
                source_anchor="生日宴上，林晚被拖出去，老管家跪下叫大小姐。",
                source_excerpt="林晚在生日宴被顾承赶出，老管家抱着旧木盒跪下叫她大小姐。",
                c1_must_keep_assets=["老管家", "大小姐", "旧木盒"],
                c2_visual_assets=["宴会厅侧门"],
            )
        ]
    )

    report = build_source_evidence_report(
        script_batch,
        episode_source_packets=packets,
    )

    assert report.coverage_score == 100
    assert report.items[0].status == "matched"
    assert report.items[0].source_anchor.startswith("生日宴")
    assert "保留原文必留资产" in report.items[0].adaptation_reason
    assert any("老管家" in line or "大小姐" in line for line in report.items[0].script_evidence)

    markdown = render_source_evidence_report(report)
    assert "Source Evidence Report" in markdown
    assert "EP01" in markdown
    assert "旧木盒" in markdown


def test_source_evidence_report_flags_missing_source_assets():
    script_batch = demo_round_outputs()[3]
    packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=1,
                source_anchor="原文里亲哥哥突然救场。",
                source_excerpt="林晚被赶出时，亲哥哥突然出现。",
                c1_must_keep_assets=["亲哥哥救场"],
            )
        ]
    )

    report = build_source_evidence_report(
        script_batch,
        episode_source_packets=packets,
    )

    assert report.coverage_score == 0
    assert report.items[0].status == "missing"
    assert report.items[0].script_evidence == []
    assert report.missing_items == ["EP01 缺少原文资产：亲哥哥救场"]
    assert "原文证据未落到正片" in report.rewrite_instruction


def test_source_evidence_does_not_block_on_observational_anchor_only():
    packet = EpisodeSourcePacket(
        episode=1,
        source_anchor="林晚在生日宴上被当众羞辱。 -> EP01-EP05",
        source_excerpt="林晚在生日宴上被当众羞辱。",
    )
    script = EpisodeScript(
        episode=1,
        title="身份线推进",
        hook_3s="鉴定报告出来了。",
        main_emotion="反转",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="1-1 日-内-鉴定中心",
                characters=["林晚"],
                lines=[
                    SceneLine(kind="action", text="△中景推近鉴定报告，林晚指尖停在姓名栏。"),
                ],
            )
        ],
        cliffhanger="报告被人抽走。",
        state_update={},
    )

    report = build_source_evidence_report(
        ScriptBatch(episodes=[script]),
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
    )

    assert report.items[0].status == "missing"
    assert report.missing_items == []
    assert report.rewrite_instruction == ""


def test_source_evidence_missing_assets_downgrades_quality_report():
    script_batch = demo_round_outputs()[3]
    packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=1,
                source_anchor="原文里亲哥哥突然救场。",
                source_excerpt="林晚被赶出时，亲哥哥突然出现。",
                c1_must_keep_assets=["亲哥哥救场"],
            )
        ]
    )
    source_evidence_report = build_source_evidence_report(
        script_batch,
        episode_source_packets=packets,
    )
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

    merged = merge_source_evidence_into_quality_report(
        quality_report,
        source_evidence_report,
    )

    assert merged.status == QualityStatus.NEEDS_REWRITE
    assert any(issue.startswith("source_evidence:") for issue in merged.blocking_issues)
    assert "亲哥哥救场" in merged.rewrite_instruction


def test_source_evidence_scores_each_asset_not_only_episode_hit():
    packet = EpisodeSourcePacket(
        episode=1,
        source_anchor="颁奖礼后台羞辱",
        source_excerpt="林挽清被藏在后台，路淮北把手探进她礼服。许念念在台上举起奖杯。",
        c1_must_keep_assets=["路淮北把手探进她礼服", "许念念在台上举起奖杯"],
    )
    script = EpisodeScript(
        episode=1,
        title="后台羞辱",
        hook_3s="别出声。",
        main_emotion="压迫",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="1-1 夜-内-颁奖礼后台",
                characters=["林挽清", "路淮北"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△特写推近路淮北的手探进林挽清礼服腰侧，舞台掌声从门缝灌进来。",
                    ),
                    SceneLine(kind="dialogue", speaker="路淮北", emotion="低声", text="别出声。"),
                ],
            )
        ],
        cliffhanger="别出声。",
        state_update={},
    )

    report = build_source_evidence_report(
        ScriptBatch(episodes=[script]),
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
    )

    assert report.coverage_score == 50
    assert report.items[0].status == "partial"
    assert any("许念念在台上举起奖杯" in item for item in report.missing_items)
    assert len(report.items[0].evidence_spans) == 2
    assert [span.status for span in report.items[0].evidence_spans] == [
        "matched",
        "missing",
    ]


def test_source_evidence_does_not_block_on_visual_methodology_actions():
    packet = EpisodeSourcePacket(
        episode=1,
        source_anchor="颁奖礼后台羞辱",
        source_excerpt="林挽清被藏在后台，路淮北把手探进她礼服。",
        c1_must_keep_assets=["路淮北把手探进她礼服"],
        c2_visual_assets=[
            "将内心OS转为紧迫的呼吸动作与镜头的局部特写，强化被公开处刑的耻辱感"
        ],
    )
    script = EpisodeScript(
        episode=1,
        title="后台羞辱",
        hook_3s="别出声。",
        main_emotion="压迫",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="1-1 夜-内-颁奖礼后台",
                characters=["林挽清", "路淮北"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△特写推近路淮北的手探进林挽清礼服腰侧，林挽清屏住呼吸。",
                    ),
                ],
            )
        ],
        cliffhanger="主持人的声音压过后台。",
        state_update={},
    )

    report = build_source_evidence_report(
        ScriptBatch(episodes=[script]),
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
    )

    assert report.coverage_score == 100
    assert report.missing_items == []
    assert "将内心OS转为" not in "；".join(report.missing_items)
    assert len(report.items[0].evidence_spans) == 1


def test_source_evidence_requires_specific_asset_not_only_character_name():
    packet = EpisodeSourcePacket(
        episode=1,
        source_anchor="许念念早已把解约协议放进包里。",
        source_excerpt="许念念走进办公室，举起提前准备好的解约协议。",
        c1_must_keep_assets=["许念念举起提前准备好的解约协议"],
    )
    script = EpisodeScript(
        episode=1,
        title="办公室对峙",
        hook_3s="门被推开。",
        main_emotion="压迫",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="1-1 日-内-办公室",
                characters=["许念念"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△中景推近许念念低头喝水，桌面没有任何文件。",
                    )
                ],
            )
        ],
        cliffhanger="门外传来脚步声。",
        state_update={},
    )

    report = build_source_evidence_report(
        ScriptBatch(episodes=[script]),
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
    )

    assert report.coverage_score == 0
    assert report.items[0].status == "missing"
    assert report.items[0].script_evidence == []

    script.scenes[0].lines[0].text = "△中景推近许念念从包里抽出解约协议，举到镜头前。"
    matched_report = build_source_evidence_report(
        ScriptBatch(episodes=[script]),
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
    )

    assert matched_report.coverage_score == 100
    assert matched_report.items[0].status == "matched"


def test_source_evidence_records_source_span_script_line_and_reason_per_asset():
    packet = EpisodeSourcePacket(
        episode=1,
        source_anchor="办公室解约",
        source_excerpt=(
            "许念念早已把解约协议放进包里。\n"
            "她走进办公室，举起提前准备好的解约协议。"
        ),
        c1_must_keep_assets=["许念念举起提前准备好的解约协议"],
    )
    script = EpisodeScript(
        episode=1,
        title="办公室对峙",
        hook_3s="门被推开。",
        main_emotion="压迫",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="1-1 日-内-办公室",
                characters=["许念念"],
                lines=[
                    SceneLine(kind="dialogue", speaker="路淮北", emotion="冷", text="你想清楚。"),
                    SceneLine(
                        kind="action",
                        text="△中景推近许念念从包里抽出解约协议，举到镜头前。",
                    ),
                ],
            )
        ],
        cliffhanger="她把笔压在纸上。",
        state_update={},
    )

    report = build_source_evidence_report(
        ScriptBatch(episodes=[script]),
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
    )

    span = report.items[0].evidence_spans[0]
    assert span.asset == "许念念举起提前准备好的解约协议"
    assert span.status == "matched"
    assert span.source_anchor == "办公室解约"
    assert span.source_excerpt == packet.source_excerpt
    assert span.source_line == "她走进办公室，举起提前准备好的解约协议。"
    assert span.source_line_index == 2
    assert span.script_line == "△中景推近许念念从包里抽出解约协议，举到镜头前。"
    assert span.script_line_index == 7
    assert span.adaptation_reason.startswith("保留原文必留资产")

    markdown = render_source_evidence_report(report)
    assert "Source Span Evidence" in markdown
    assert "source L2" in markdown
    assert "script L7" in markdown
