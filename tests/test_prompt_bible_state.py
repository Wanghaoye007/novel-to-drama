from novel_drama_engine import prompts
from novel_drama_engine.demo import demo_round_outputs


def test_bible_prompt_locks_system_owned_character_contract():
    source_analysis, episode_context, *_ = demo_round_outputs()

    user_prompt = prompts.bible_user(
        "林晚被赶出生日宴。",
        source_analysis,
        episode_context,
    )

    assert "Story Bible 是系统自动维护的内部状态" in prompts.BIBLE_SYSTEM
    assert "不要请求用户确认" in prompts.BIBLE_SYSTEM
    assert "这是系统自动维护的内部状态，不向用户发起确认" in user_prompt
    assert "基础身份｜强记忆标签｜核心反差｜核心诉求｜终极执念｜戏剧功能" in user_prompt
    assert "2 个 15 字以内示例短句" in user_prompt
    assert "功能性配角只承担一个功能" in user_prompt
    assert "反派必须写直白动机" in user_prompt
    assert "禁止复杂洗白" in user_prompt


def test_state_prompt_preserves_knowledge_layers_and_live_hooks():
    source_analysis, episode_context, story_bible, script_batch, quality_report, previous_context = (
        demo_round_outputs()
    )

    user_prompt = prompts.state_user(
        source_analysis,
        episode_context,
        story_bible,
        script_batch,
        quality_report,
        previous_context,
    )

    assert "不得改写已锁定 Story Bible" in prompts.STATE_SYSTEM
    assert "audience_known（观众已知）" in prompts.STATE_SYSTEM
    assert "protagonist_known（主角已知）" in prompts.STATE_SYSTEM
    assert "villain_known（反派已知）" in prompts.STATE_SYSTEM
    assert "只回写 script_batch 中已经拍出来、说出来、露出来" in user_prompt
    assert "character_knowledge 必须至少按 audience_known（观众已知）" in user_prompt
    assert "protagonist_known（主角已知）" in user_prompt
    assert "villain_known（反派已知）" in user_prompt
    assert "open_hooks 必须来自剧中实际演出的悬念" in user_prompt
    assert "不能写营销看点" in user_prompt
    assert "已经揭示给观众和主角的信息" in user_prompt
    assert "prop_states 必须保留关键道具/证据/伤口/文件" in user_prompt
    assert "foreshadowing_ledger 必须标记每条伏笔是 seeded、paid_off 还是 still_open" in user_prompt
