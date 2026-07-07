from novel_drama_engine.quality_text import (
    dedupe_quality_items,
    filter_quality_text_for_episode,
    merge_rewrite_instructions,
)


def test_merge_rewrite_instructions_dedupes_and_filters_positive_advice():
    instruction = merge_rewrite_instructions(
        [
            "方法论阻断：本素材被判定为强原文，只允许轻改。具体问题：强原文轻改失败：脚本疑似命中方法论反例：把原文预谋解约改成现场赌气解约。",
            "The provided scripts accurately map to the source material. No blocking issues detected. Ensure that when filming, emphasize props.",
            "方法论阻断：本素材被判定为强原文，只允许轻改。具体问题：强原文轻改失败：脚本疑似命中方法论反例：把原文预谋解约改成现场赌气解约。",
            "source_asset_preservation：恢复原文强冲突、关键情绪和不可改事实。",
            "source_asset_preservation：恢复原文强冲突、关键情绪和不可改事实。",
        ],
        blocking=True,
    )

    assert instruction.count("方法论阻断") == 1
    assert instruction.count("source_asset_preservation") == 1
    assert "No blocking issues detected" not in instruction
    assert "Ensure that when filming" not in instruction


def test_dedupe_quality_items_removes_repeated_blocking_issues():
    items = dedupe_quality_items(
        [
            "source anchor not evidenced in script: 晚会昏暗氛围",
            "source anchor not evidenced in script：晚会昏暗氛围",
            "EP01 too short: 664 chars, expected >= 800",
        ]
    )

    assert items == [
        "source anchor not evidenced in script: 晚会昏暗氛围",
        "EP01 too short: 664 chars, expected >= 800",
    ]


def test_filter_quality_text_for_episode_keeps_only_target_episode_and_global_rules():
    text = (
        "方法论阻断：本素材被判定为强原文，只允许轻改；"
        "EP01 too short: 664 chars, expected >= 800；"
        "EP02 has non-shooting scene headings: 2-1 白-内-林挽清公寓；"
        "source_evidence: EP05 缺少原文资产：雪地烟火激吻；"
        "source_asset_preservation：恢复原文强冲突、关键情绪和不可改事实。"
    )

    scoped = filter_quality_text_for_episode(text, 1)

    assert "方法论阻断" in scoped
    assert "EP01 too short" in scoped
    assert "source_asset_preservation" in scoped
    assert "EP02" not in scoped
    assert "EP05" not in scoped
    assert "雪地烟火激吻" not in scoped
