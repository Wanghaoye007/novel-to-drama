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
    source_evidence_quality_issues,
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
                source_evidence_assets=["亲哥哥救场"],
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


def test_missing_source_evidence_becomes_structured_unscoped_hard_issue():
    script_batch = demo_round_outputs()[3]
    report = build_source_evidence_report(
        script_batch,
        episode_source_packets=EpisodeSourcePackets(
            packets=[
                EpisodeSourcePacket(
                    episode=1,
                    source_anchor="原文里亲哥哥突然救场。",
                    source_excerpt="林晚被赶出时，亲哥哥突然出现。",
                    c1_must_keep_assets=["亲哥哥救场"],
                    source_evidence_assets=["亲哥哥救场"],
                )
            ]
        ),
    )

    issues = source_evidence_quality_issues(report)

    assert len(issues) == 1
    assert issues[0].code == "MISSING_REQUIRED_FACT"
    assert issues[0].severity == "hard"
    assert issues[0].episode == 1
    assert issues[0].scene_id is None
    assert issues[0].evidence == ["亲哥哥救场"]


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
    assert source_evidence_quality_issues(report) == []


def test_source_evidence_does_not_promote_c1_inference_to_blocking_contract():
    packet = EpisodeSourcePacket(
        episode=1,
        source_anchor="EP01 当前集原文",
        source_excerpt="宴会公开羞辱。林晚被保安推到门口。",
        c1_must_keep_assets=["宴会公开羞辱"],
        source_evidence_assets=[],
    )
    script = EpisodeScript(
        episode=1,
        title="被赶出生日宴",
        hook_3s="滚出去。",
        main_emotion="压迫",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="1-1 夜-内-宴会厅",
                characters=["林晚"],
                lines=[
                    SceneLine(kind="action", text="△中景林晚被保安推到门口。"),
                ],
            )
        ],
        cliffhanger="门外脚步声逼近。",
        state_update={},
    )

    report = build_source_evidence_report(
        ScriptBatch(episodes=[script]),
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
    )

    assert report.items[0].evidence_spans[0].asset == "宴会公开羞辱"
    assert report.items[0].evidence_spans[0].status == "script_missing"
    assert report.items[0].status == "missing"
    assert report.missing_items == []
    assert report.rewrite_instruction == ""
    assert source_evidence_quality_issues(report) == []


def test_source_evidence_missing_assets_downgrades_quality_report():
    script_batch = demo_round_outputs()[3]
    packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=1,
                source_anchor="原文里亲哥哥突然救场。",
                source_excerpt="林晚被赶出时，亲哥哥突然出现。",
                c1_must_keep_assets=["亲哥哥救场"],
                source_evidence_assets=["亲哥哥救场"],
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
        source_evidence_assets=["路淮北把手探进她礼服", "许念念在台上举起奖杯"],
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
        "script_missing",
    ]


def test_source_evidence_skips_packets_without_current_episode_script():
    script = EpisodeScript(
        episode=1,
        title="颁奖台下",
        hook_3s="别出声。",
        main_emotion="羞辱",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="1-1 夜-内-颁奖礼后台",
                characters=["林挽清", "路淮北"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△特写推近路淮北手部压迫林挽清，门缝外掌声涌进来。",
                    )
                ],
            )
        ],
        cliffhanger="主持人的声音压过门缝。",
        state_update={},
    )
    packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=8,
                source_anchor="雪地烟火激吻，照片随后被公开。",
                source_excerpt="雪地烟火下两人接吻，照片被公开。",
                source_evidence_assets=["雪地烟火激吻", "照片被公开"],
            )
        ]
    )

    report = build_source_evidence_report(
        ScriptBatch(episodes=[script]),
        episode_source_packets=packets,
    )

    assert report.coverage_score == 100
    assert report.items == []
    assert report.missing_items == []
    assert report.rewrite_instruction == ""


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
        source_evidence_assets=["许念念举起提前准备好的解约协议"],
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


def test_source_evidence_marks_unverified_upstream_asset_without_blocking_script():
    packet = EpisodeSourcePacket(
        episode=1,
        source_anchor="办公室对峙",
        source_excerpt="林挽清推门进来，只把手机扣在桌上。",
        c1_must_keep_assets=["提前准备好的解约协议"],
    )
    script = EpisodeScript(
        episode=1,
        title="办公室解约",
        hook_3s="门被推开。",
        main_emotion="决裂",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="1-1 日-内-办公室",
                characters=["林挽清"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△中景推近林挽清把提前准备好的解约协议拍到桌上。",
                    )
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
    assert span.script_line is not None
    assert span.source_line is None
    assert span.status == "source_missing"
    assert report.items[0].status == "source_unverified"
    assert report.coverage_score == 0
    assert report.missing_items == []
    assert report.rewrite_instruction == ""


def test_source_evidence_matches_abstract_asset_by_concrete_visual_tokens():
    packet = EpisodeSourcePacket(
        episode=4,
        source_anchor="EP04 当前集原文",
        source_excerpt="他微微俯身将粉色围裙系在我腰间，靠近的瞬间，我能看到他凸起的喉结。",
        c1_must_keep_assets=["粉色围裙的情感关联"],
        source_evidence_assets=["粉色围裙的情感关联"],
    )
    script = EpisodeScript(
        episode=4,
        title="粉色围裙",
        hook_3s="他靠近了。",
        main_emotion="暧昧",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="4-1 日-内-霍家厨房",
                characters=["林挽清", "霍庭琛"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△特写推近霍庭琛将粉色围裙绕过她颈后系紧，喉结压进前景光里。",
                    ),
                    SceneLine(kind="dialogue", speaker="霍庭琛", text="饿了？"),
                ],
            )
        ],
        cliffhanger="他递来小兔子蛋糕。",
        state_update={},
    )

    report = build_source_evidence_report(
        ScriptBatch(episodes=[script]),
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
    )

    assert report.coverage_score == 100
    assert report.missing_items == []
    assert report.items[0].status == "matched"


def test_source_evidence_ignores_planning_words_in_visual_asset():
    packet = EpisodeSourcePacket(
        episode=2,
        source_anchor="EP02 当前集原文",
        source_excerpt=(
            "私人飞机平稳升空。林挽清穿着价格昂贵的裙子和拖鞋，"
            "手边的红酒轻轻晃动。"
        ),
        c1_must_keep_assets=["私人飞机内部的昂贵细节镜头"],
        source_evidence_assets=["私人飞机内部的昂贵细节镜头"],
    )
    script = EpisodeScript(
        episode=2,
        title="私人飞机",
        hook_3s="飞机已经升空。",
        main_emotion="清醒",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="2-1 日-内-私人飞机客舱",
                characters=["林挽清"],
                lines=[
                    SceneLine(
                        kind="action",
                        text=(
                            "△中景横移私人飞机客舱，林挽清身上的高定裙摆掠过真皮座椅，"
                            "桌边红酒随气流轻晃。"
                        ),
                    ),
                ],
            )
        ],
        cliffhanger="她关掉手机。",
        state_update={},
    )

    report = build_source_evidence_report(
        ScriptBatch(episodes=[script]),
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
    )

    assert report.items[0].status == "matched"
    assert report.missing_items == []


def test_source_evidence_ignores_scene_and_action_planning_suffixes():
    packet = EpisodeSourcePacket(
        episode=5,
        source_anchor="EP05 当前集原文",
        source_excerpt="霍庭琛递来草莓，我低头就着他的手吃下。",
        c1_must_keep_assets=["含草莓的动作场景特写"],
        source_evidence_assets=["含草莓的动作场景特写"],
    )
    script = EpisodeScript(
        episode=5,
        title="草莓",
        hook_3s="她含住草莓。",
        main_emotion="暧昧",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="5-1 日-内-别墅客厅",
                characters=["林挽清", "霍庭琛"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△近景推近，林挽清就着霍庭琛的手含住鲜红草莓。",
                    ),
                ],
            )
        ],
        cliffhanger="她含住草莓。",
        state_update={},
    )

    report = build_source_evidence_report(
        ScriptBatch(episodes=[script]),
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
    )

    assert report.items[0].status == "matched"
    assert report.missing_items == []


def test_source_evidence_matches_shout_synonyms():
    packet = EpisodeSourcePacket(
        episode=5,
        source_anchor="EP05 当前集原文",
        source_excerpt="路淮北突然暴怒，在电话那头嘶吼。",
        c1_must_keep_assets=["路淮北暴怒的嘶吼"],
        source_evidence_assets=["路淮北暴怒的嘶吼"],
    )
    script = EpisodeScript(
        episode=5,
        title="暴怒来电",
        hook_3s="怒吼炸开听筒。",
        main_emotion="压迫",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="5-1 日-内-别墅客厅",
                characters=["林挽清", "路淮北"],
                lines=[
                    SceneLine(
                        kind="vo",
                        speaker="路淮北",
                        emotion="暴怒",
                        text="怒吼突然炸开听筒：你跟谁在一起！",
                    ),
                ],
            )
        ],
        cliffhanger="你跟谁在一起！",
        state_update={},
    )

    report = build_source_evidence_report(
        ScriptBatch(episodes=[script]),
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
    )

    assert report.items[0].status == "matched"
    assert report.missing_items == []


def test_source_evidence_matches_action_and_emotion_across_adjacent_lines():
    packet = EpisodeSourcePacket(
        episode=5,
        source_anchor="EP05 当前集原文",
        source_excerpt=(
            "草莓的香味盖掉奶油的腻，我干脆利落地挂断电话。\n"
            "我看了眼站在面前走神的男人，尴尬地抿唇解释。"
        ),
        c1_must_keep_assets=["挂断电话后的尴尬场景"],
        source_evidence_assets=["挂断电话后的尴尬场景"],
    )
    script = EpisodeScript(
        episode=5,
        title="草莓乌龙",
        hook_3s="她就着他的手吃下草莓。",
        main_emotion="决绝与暧昧",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="5-1 日-内-瑞士别墅客厅",
                characters=["林挽清", "霍庭琛"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△近景定镜，林挽清挂断电话，把手机扔进沙发。",
                    ),
                    SceneLine(
                        kind="action",
                        text="△特写推近，她撞进霍庭琛含笑的眼底，脸颊发烫，抿紧嘴唇。",
                    ),
                    SceneLine(
                        kind="dialogue",
                        speaker="林挽清",
                        emotion="尴尬",
                        text="抱歉，刚才是我下意识的。",
                    ),
                ],
            )
        ],
        cliffhanger="他指了指她的唇角。",
        state_update={},
    )

    report = build_source_evidence_report(
        ScriptBatch(episodes=[script]),
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
    )

    assert report.items[0].status == "matched"
    assert report.missing_items == []


def test_source_evidence_matches_asset_across_adjacent_script_lines():
    packet = EpisodeSourcePacket(
        episode=1,
        source_anchor="颁奖礼",
        source_excerpt="主持人宣布许念念获奖，灯光聚焦到她身上。",
        c1_must_keep_assets=["主持人宣布名字的瞬间灯光聚焦"],
        source_evidence_assets=["主持人宣布名字的瞬间灯光聚焦"],
    )
    script = EpisodeScript(
        episode=1,
        title="颁奖礼",
        hook_3s="获奖的是她。",
        main_emotion="羞辱",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="1-1 夜-内-颁奖礼现场",
                characters=["主持人", "许念念"],
                lines=[
                    SceneLine(kind="dialogue", speaker="主持人", text="今晚获得影后的是……许念念。"),
                    SceneLine(
                        kind="action",
                        text="△中景定镜推向颁奖台，聚光灯汇聚在许念念的礼服上。",
                    ),
                ],
            )
        ],
        cliffhanger="许念念站到光里。",
        state_update={},
    )

    report = build_source_evidence_report(
        ScriptBatch(episodes=[script]),
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
    )

    assert report.coverage_score == 100
    assert report.missing_items == []
    assert "主持人" in report.items[0].script_evidence[0]


def test_source_evidence_matches_long_descriptive_asset_by_role_action_emotion():
    packet = EpisodeSourcePacket(
        episode=4,
        source_anchor="厨房初见",
        source_excerpt="见我没开口，霍庭琛又靠近半步，语气染上几分疑惑。",
        c1_must_keep_assets=["见我没开口，霍庭琛又靠近半步，语气染上几分疑惑"],
        source_evidence_assets=["见我没开口，霍庭琛又靠近半步，语气染上几分疑惑"],
    )
    script = EpisodeScript(
        episode=4,
        title="厨房初见",
        hook_3s="他靠近了。",
        main_emotion="暧昧",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="4-1 日-内-度假木屋客厅",
                characters=["林挽清", "霍庭琛"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△中景横移，林挽清静立，霍庭琛侧身步入，清冽气息随之靠近。",
                    ),
                    SceneLine(kind="dialogue", speaker="霍庭琛", emotion="疑惑", text="小雅是不是给你惹麻烦了？"),
                ],
            )
        ],
        cliffhanger="他又近半步。",
        state_update={},
    )

    report = build_source_evidence_report(
        ScriptBatch(episodes=[script]),
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
    )

    assert report.coverage_score == 100
    assert report.missing_items == []
    assert report.items[0].status == "matched"


def test_source_evidence_empty_placeholder_packet_is_not_full_coverage():
    packet = EpisodeSourcePacket(
        episode=1,
        source_anchor="EP01 当前集原文",
        source_excerpt="林挽清站在后台，听见台上掌声。",
        source_evidence_assets=[],
    )
    script = EpisodeScript(
        episode=1,
        title="后台",
        hook_3s="别出声。",
        main_emotion="羞辱",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="1-1 夜-内-后台",
                characters=["林挽清"],
                lines=[
                    SceneLine(kind="action", text="△中景推近林挽清低头站在后台。"),
                ],
            )
        ],
        cliffhanger="掌声压过她的呼吸。",
        state_update={},
    )

    report = build_source_evidence_report(
        ScriptBatch(episodes=[script]),
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
    )

    assert report.items[0].status == "missing"
    assert report.items[0].evidence_spans == []
    assert report.coverage_score == 0
    assert report.missing_items == []
