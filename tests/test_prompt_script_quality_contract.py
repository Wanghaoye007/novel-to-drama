from novel_drama_engine import prompts
from novel_drama_engine.demo import demo_round_outputs
from novel_drama_engine.models import EpisodeScript, Scene, SceneLine
from novel_drama_engine.script_quality import episode_quality_warnings


def test_script_and_quality_prompts_lock_user_visible_script_contract():
    outputs = demo_round_outputs(include_episode_plan=True, target_episode_count=30)
    source_analysis, episode_context, story_bible, episode_plan, script_batch = outputs[:5]

    script_prompt = prompts.script_user(
        "武植睁眼看见金莲端药。",
        source_analysis,
        episode_context,
        story_bible,
        None,
        "",
        target_episode_count=30,
        episode_plan=episode_plan,
    )
    episode_prompt = prompts.script_episode_user(
        "武植睁眼看见金莲端药。",
        source_analysis,
        episode_context,
        story_bible,
        None,
        script_batch.episodes[0],
        1,
        "补足镜头动作。",
        episode_plan=episode_plan,
    )
    hook_dialogue_prompt = prompts.hook_dialogue_polish_user(
        "武植睁眼看见金莲端药。",
        source_analysis,
        episode_context,
        story_bible,
        None,
        script_batch.episodes[0],
        1,
        "结尾钩子太软。",
        episode_plan=episode_plan,
    )
    quality_prompt = prompts.quality_user(
        source_analysis,
        episode_context,
        story_bible,
        script_batch,
        None,
        episode_plan=episode_plan,
    )

    assert "Hook/main_emotion/watch_reason/消费理由只允许出现在 EpisodeScript 结构化字段中" in script_prompt
    assert "episode 字段必须按顺序等于 1、2、3、4、5" in script_prompt
    assert "首稿不按 action/对白/镜头数量凑行" in script_prompt
    assert "cliffhanger 字段必须直接填写最后一场最后 4 行里已经演出来的钩子台词或动作" in script_prompt
    assert "不得出现在任何 scene.lines 的 action/dialogue/os/vo/transition 文本里" in script_prompt
    assert "景别、主体位置、镜头运动、构图/光线、关键道具、人物表情" not in script_prompt
    assert "最后一场最后 2 行必须把 cliffhanger" in script_prompt
    assert "镜头衔接硬验收" not in script_prompt
    assert "最后两行硬模板" not in script_prompt
    assert "信息增量硬验收" in script_prompt
    assert "action 每行只写一个可见动作节拍，不超过 32 个字符" in script_prompt
    assert "dialogue/os/vo 每行只说一个意思，不超过 22 个字符" in script_prompt
    assert "从第 2 集开始，不能只延续上一集争执" in script_prompt
    assert "action 行硬格式" not in script_prompt
    assert "Hook/main_emotion/watch_reason/消费理由不得出现在任何 scene line 文本里" in episode_prompt
    assert "action 每行只写一个可见动作节拍，不超过 32 个字符" in episode_prompt
    assert "dialogue/os/vo 每行只说一个意思，不超过 22 个字符" in episode_prompt
    assert "cliffhanger 字段必须直接填写最后一场最后 4 行里已经演出来的钩子台词或动作" in episode_prompt
    assert "action 行硬格式" not in episode_prompt
    assert "最后两行不能是“结尾钩子/看点/消费理由”的说明文字" in episode_prompt
    assert "不能用黑屏、转场、画面定格、普通 OS 作为最后两行钩子" in episode_prompt
    assert "开场/结尾钩子与对白密度二次编译" in hook_dialogue_prompt
    assert "不要整集重写" in hook_dialogue_prompt
    assert "最后 8-12 行" in hook_dialogue_prompt
    assert "转身离开、我需要时间、明天再说" in hook_dialogue_prompt
    assert "cliffhanger 字段必须直接填写最后 4 行里已经演出来的钩子台词或动作" in hook_dialogue_prompt
    assert "action 行硬格式" not in hook_dialogue_prompt
    assert "本地确定性质检已经负责逐行硬指标" in quality_prompt
    assert "不要凭摘要声称逐行检查了每条 action 或每句对白" in quality_prompt
    assert "只基于 script_batch_digest 可见内容判断" in quality_prompt
    assert '"episode_plan":' not in quality_prompt
    assert "不得因为 drama_engine、protagonist_misbelief" in quality_prompt
    assert "戏剧质量、跨集连续性、人物动机、原著保真和题材模板一致性" in quality_prompt
    assert "cliffhanger 字段必须能在摘要中的 tail_lines 里找到可见承接" in quality_prompt
    assert "action 行硬格式" not in quality_prompt
    assert "镜头衔接硬验收" not in quality_prompt
    assert "最后两行硬模板" not in quality_prompt
    assert "必须检查 action 是否包含景别" not in quality_prompt
    assert "对白是否超过 22 字" not in quality_prompt
    assert "题材模板错配必须拦截" in quality_prompt
    assert "真假千金/豪门宴会/总裁/亲子鉴定/大小姐模板" in quality_prompt


def test_local_quality_rejects_internal_metadata_leak_and_template_mismatch():
    episode = EpisodeScript(
        episode=1,
        title="模板串戏",
        hook_3s="药碗递到嘴边！",
        main_emotion="惊险",
        watch_reason="系统内部看点。",
        scenes=[
            Scene(
                heading="1-1 夜-内-武家卧室",
                characters=["武植", "金莲"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△中景推近武植，Hook：观众要看他在豪门宴会厅反杀。",
                    ),
                    SceneLine(kind="dialogue", speaker="武植", emotion="惊", text="谁敢逼我喝？"),
                    SceneLine(kind="dialogue", speaker="金莲", emotion="慌", text="大郎，你先醒醒！"),
                ],
            )
        ],
        cliffhanger="谁敢逼我喝？",
        state_update={},
    )

    warnings = episode_quality_warnings(episode)
    assert any("exposes hook/watch_reason analysis" in warning for warning in warnings)
    assert any("genre template mismatch" in warning for warning in warnings)


def test_local_quality_rejects_summary_lines_and_unperformed_final_hook():
    episode = EpisodeScript(
        episode=1,
        title="说明式结尾",
        hook_3s="把门锁上！",
        main_emotion="压迫",
        watch_reason="系统内部看点。",
        scenes=[
            Scene(
                heading="1-1 夜-内-林家走廊",
                characters=["林晚", "顾承"],
                lines=[
                    SceneLine(kind="action", text="△中景推近林晚背影，走廊灯光压暗。"),
                    SceneLine(
                        kind="dialogue",
                        speaker="林晚",
                        emotion="坚定",
                        text="因为我们每个人都应该明白真正的尊严不是别人给的。",
                    ),
                    SceneLine(kind="dialogue", speaker="顾承", emotion="冷", text="走吧。"),
                    SceneLine(kind="dialogue", speaker="林晚", emotion="平", text="明天再说。"),
                ],
            )
        ],
        cliffhanger="把门锁上！",
        state_update={},
    )

    warnings = episode_quality_warnings(episode)
    shooting_warnings = episode_quality_warnings(episode, strict_shooting=True)

    assert any("explanatory/value-summary voiced lines" in warning for warning in warnings)
    assert any("cliffhanger is not performed in the final scene last 2 lines" in warning for warning in warnings)
    assert not any("lacks shot-to-shot linkage" in warning for warning in warnings)
    assert any("lacks shot-to-shot linkage" in warning for warning in shooting_warnings)
