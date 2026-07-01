from novel_drama_engine import prompts
from novel_drama_engine.demo import demo_round_outputs


def test_episode_context_prompt_requires_canonical_episode_range(happy_round_outputs):
    source_analysis = happy_round_outputs[0]

    user_prompt = prompts.episode_context_user(
        "林晚被赶出生日宴。",
        None,
        source_analysis,
        round_number=1,
        target_episode_count=30,
    )

    assert "target_episode_range 必须使用 EP 两位格式" in user_prompt
    assert "禁止输出 1-5" in user_prompt


def test_script_prompt_requires_executable_scene_and_shot_contract(happy_round_outputs):
    outputs = demo_round_outputs(include_episode_plan=True)
    source_analysis, episode_context, story_bible, episode_plan = outputs[:4]

    user_prompt = prompts.script_user(
        "武植睁眼看见金莲端药。",
        source_analysis,
        episode_context,
        story_bible,
        None,
        "",
        round_number=1,
        target_episode_count=30,
        episode_plan=episode_plan,
    )

    assert "episode_plan" in user_prompt
    assert "three_pull_beats" in user_prompt
    assert "scene.heading 必须严格写成" in user_prompt
    assert "禁止只写 豪华宴会厅" in user_prompt
    assert "每条 action 必须写清景别" in user_prompt
    assert "每条 action 必须显式包含一个景别词" in user_prompt
    assert "一句不超过 30 个汉字" in user_prompt
    assert "不合格 action 示例" in user_prompt
    assert "消费理由说明" in user_prompt


def test_script_episode_prompt_targets_one_episode(happy_round_outputs):
    outputs = demo_round_outputs(include_episode_plan=True)
    source_analysis, episode_context, story_bible, episode_plan, script_batch = outputs[:5]

    user_prompt = prompts.script_episode_user(
        "武植睁眼看见金莲端药。",
        source_analysis,
        episode_context,
        story_bible,
        None,
        script_batch.episodes[0],
        1,
        "补足镜头动作和短台词。",
        episode_plan=episode_plan,
    )

    assert "只生成第 1 集" in user_prompt
    assert "episode 字段必须等于 1" in user_prompt
    assert "不要输出其他集数" in user_prompt
    assert "1-场次 日/夜-内/外-具体地点" in user_prompt
    assert "无景别、无运镜" in user_prompt


def test_episode_plan_prompt_requires_drama_design(happy_round_outputs):
    source_analysis, episode_context, story_bible = happy_round_outputs[:3]

    user_prompt = prompts.episode_plan_user(
        "林晚被赶出生日宴。",
        source_analysis,
        episode_context,
        story_bible,
        None,
    )

    assert "只做改编设计，不写完整台词剧本" in user_prompt
    assert "三波拉扯" in user_prompt
    assert "假打脸" in user_prompt
    assert "最狠的一句短台词" in user_prompt
