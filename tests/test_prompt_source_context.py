from pydantic import BaseModel

from novel_drama_engine import prompts


class MinimalSourceAnalysis(BaseModel):
    characters: list[str]
    conflicts: list[str]
    candidate_hooks: list[str]


class MinimalPreviousContext(BaseModel):
    summary: str
    current_episode: int
    open_hooks: list[str]


def test_source_parser_prompt_requires_shootable_assets_not_summary():
    user_prompt = prompts.source_parser_user("武植醒来，金莲端着药站在床前。")
    combined_prompt = prompts.SOURCE_PARSER_SYSTEM + user_prompt

    assert "可拍摄生产资产" in combined_prompt
    assert "不是剧情总结" in combined_prompt
    assert "不写人物小传" in combined_prompt
    assert "主体、动作、对象" in user_prompt
    assert "地点/道具/对白和当场后果" in user_prompt
    assert "candidate_hooks 只能是可见动作、强对白、道具露出、威胁或反转" in combined_prompt
    assert "能被剪成前三秒画面/声音" in user_prompt
    assert "不能写成“观众想看什么”" in combined_prompt


def test_source_parser_prompt_blocks_wrong_genre_template():
    user_prompt = prompts.source_parser_user("大宋年间，武大郎忽然有了现代经商记忆。")
    combined_prompt = prompts.SOURCE_PARSER_SYSTEM + user_prompt

    assert "男频穿越" in combined_prompt
    assert "大宋" in combined_prompt
    assert "武大郎" in combined_prompt
    assert "不得套真假千金、豪门宴会、现代豪门继承模板" in user_prompt


def test_episode_context_prompt_requires_automatic_next_episode_range():
    source_analysis = MinimalSourceAnalysis(
        characters=["武植", "金莲"],
        conflicts=["西门庆逼近，武植用现代认知反制"],
        candidate_hooks=["金莲把药碗摔在地上"],
    )
    previous_context = MinimalPreviousContext(
        summary="EP05 结束：武植识破药碗问题。",
        current_episode=5,
        open_hooks=["西门庆带人堵门"],
    )

    user_prompt = prompts.episode_context_user(
        "武植醒来，发现自己穿到大宋。",
        previous_context,
        source_analysis,
        round_number=2,
        target_episode_count=30,
        episodes_per_round=5,
    )
    combined_prompt = prompts.EPISODE_CONTEXT_SYSTEM + user_prompt

    assert "系统自动识别本轮轮次" in combined_prompt
    assert "不得要求用户确认" in user_prompt
    assert "不得让用户选择方向" in combined_prompt
    assert "previous_context.current_episode + 1" in combined_prompt
    assert '"current_episode": 5' in user_prompt
    assert "target_episode_range 的起点必须等于这个下一集" in user_prompt
    assert "不得重复已完成集数" in combined_prompt
    assert "不得把已完成集数再次放入 source_to_episode_mapping" in user_prompt


def test_episode_context_prompt_requires_executable_mapping_and_actions():
    source_analysis = MinimalSourceAnalysis(
        characters=["武植"],
        conflicts=["武植经商打脸街坊"],
        candidate_hooks=["武植当众掀开账本"],
    )

    user_prompt = prompts.episode_context_user(
        "武植拿出账本，反算酒楼亏空。",
        None,
        source_analysis,
        target_episode_count=24,
    )
    combined_prompt = prompts.EPISODE_CONTEXT_SYSTEM + user_prompt

    assert "source_to_episode_mapping 必须写成可执行映射" in user_prompt
    assert "原文段落/事件、目标 EP" in user_prompt
    assert "保留的画面/对白/道具" in user_prompt
    assert "本集承担的信息增量" in user_prompt
    assert "adaptation_actions 必须是可执行动作" in combined_prompt
    assert "对象、动作、目标集数和预期效果" in user_prompt
    assert "不能写“增强爽感、推进节奏”" in user_prompt
    assert "不能套真假千金、豪门宴会模板" in combined_prompt
