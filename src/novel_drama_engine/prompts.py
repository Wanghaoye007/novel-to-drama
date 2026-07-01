from __future__ import annotations

from pydantic import BaseModel


def dump_model(name: str, model: BaseModel | None) -> str:
    if model is None:
        return f"{name}: null"
    return f"{name}: {model.model_dump_json(indent=2)}"


SOURCE_PARSER_SYSTEM = "你是短剧小说解析器。只提取短剧生产资产，不写剧情总结。"
EPISODE_CONTEXT_SYSTEM = "你是短剧集数和上下文解析器。判断原文应映射到哪几集，并给出承接约束。"
BIBLE_SYSTEM = "你是短剧 Story Bible 构建器。自动锁定主线、人物、关系和禁止改动项。"
SCRIPT_SYSTEM = "你是爆款竖屏短剧编剧。输出可拍摄、强冲突、短台词、每集留钩的剧本。"
QUALITY_SYSTEM = "你是短剧质检器。检查 Hook、冲突、信息差、连续性、可拍性和参考剧本密度。"
STATE_SYSTEM = "你是短剧状态回写器。把本轮事实、关系、伏笔、道具和下一轮钩子写回状态。"


def source_parser_user(source_text: str) -> str:
    return f"小说原文：\n{source_text}\n\n提取人物、事件、冲突、可视频化场面、低价值段落和候选 Hook。"


def episode_context_user(
    source_text: str,
    previous_context: BaseModel | None,
    source_analysis: BaseModel,
    round_number: int = 1,
    target_episode_count: int | None = None,
    episodes_per_round: int = 5,
) -> str:
    target_text = str(target_episode_count) if target_episode_count else "未指定"
    return "\n\n".join(
        [
            f"小说原文：\n{source_text}",
            f"当前轮次：第 {round_number} 轮",
            f"目标总集数：{target_text}",
            f"本轮目标集数：最多 {episodes_per_round} 集",
            dump_model("previous_context", previous_context),
            dump_model("source_analysis", source_analysis),
            (
                "判断 target_episode_range、story_stage、must_carry_context、"
                "forbidden_reveals、adaptation_actions，并给 confidence。"
                "如果 previous_context 存在，本轮必须从 current_episode + 1 开始，"
                "不得重复已完成集数；如果目标总集数剩余不足 5 集，则只覆盖剩余集数。"
            ),
        ]
    )


def bible_user(
    source_text: str,
    source_analysis: BaseModel,
    episode_context: BaseModel,
) -> str:
    return "\n\n".join(
        [
            f"小说原文：\n{source_text}",
            dump_model("source_analysis", source_analysis),
            dump_model("episode_context", episode_context),
            "生成内部 Story Bible。不要要求用户确认。",
        ]
    )


def script_user(
    source_text: str,
    source_analysis: BaseModel,
    episode_context: BaseModel,
    story_bible: BaseModel,
    previous_context: BaseModel | None,
    rewrite_instruction: str,
    round_number: int = 1,
    target_episode_count: int | None = None,
) -> str:
    target_text = str(target_episode_count) if target_episode_count else "未指定"
    return "\n\n".join(
        [
            f"小说原文：\n{source_text}",
            f"当前轮次：第 {round_number} 轮",
            f"目标总集数：{target_text}",
            dump_model("source_analysis", source_analysis),
            dump_model("episode_context", episode_context),
            dump_model("story_bible", story_bible),
            dump_model("previous_context", previous_context),
            f"rewrite_instruction: {rewrite_instruction}",
            (
                "必须输出 episode_context.target_episode_range 覆盖的全部集数，最多 5 集。"
                "每集仍需填充 3 秒 Hook、主情绪、watch_reason、cliffhanger、state_update，"
                "但这些是系统内部字段，不能在剧本文本里以“3秒 Hook/主情绪/消费理由”单独展示；"
                "必须把 hook 融入第一场的第一组动作、VO/OS 或对白。"
                "每集至少 2 个可拍摄场景。参照标杆短剧密度：每集 800-1700 字，"
                "2-5 场，至少 8 条 △/镜头动作行，至少 16 条对白/OS/VO，"
                "前 8 个 beat 必须爆出危机、羞辱、误会、威胁或强反击，"
                "至少 2 句高压短台词，结尾钩子必须是强疑问、威胁、反转或动作未完成。"
                "OS 后必须紧跟物理动作或明确决定，不能只做心理解释。"
                "对白尽量短，一句只表达一个动作或情绪，不要解释剧情设定。"
                "每条 action 必须写清景别、主体位置、镜头运动、构图/光线、关键道具，"
                "并用切镜、视线匹配、声音先入或道具特写说明镜头衔接，方便后链路 AI 执行。"
                "如果原文是男频穿越/大宋/武大郎/金莲/西门庆类，"
                "必须使用现代认知 OS + 立刻动作 + 轻喜打脸节奏，不能套用真假千金/豪门模板。"
            ),
        ]
    )


def quality_user(
    source_analysis: BaseModel,
    episode_context: BaseModel,
    story_bible: BaseModel,
    script_batch: BaseModel,
    previous_context: BaseModel | None,
) -> str:
    return "\n\n".join(
        [
            dump_model("source_analysis", source_analysis),
            dump_model("episode_context", episode_context),
            dump_model("story_bible", story_bible),
            dump_model("script_batch", script_batch),
            dump_model("previous_context", previous_context),
            (
                "检查是否可用。硬性拒绝以下问题：单集少于 800 字、少于 2 场、"
                "少于 8 条镜头动作、少于 16 条对白/OS/VO、开头 8 个 beat 没有爆冲突、"
                "OS 后没有动作承接、结尾钩子太软、题材模板错配。"
                "如果用户可见剧本文本里把 hook/主情绪/watch_reason 当成独立说明展示，"
                "或 action 缺少景别/运镜/构图/衔接，或对白显著啰嗦，也必须重写。"
                "只要出现任一硬伤，status=needs_rewrite，并在 rewrite_instruction 中逐集说明怎么补足。"
            ),
        ]
    )


def state_user(
    source_analysis: BaseModel,
    episode_context: BaseModel,
    story_bible: BaseModel,
    script_batch: BaseModel,
    quality_report: BaseModel,
    previous_context: BaseModel | None,
) -> str:
    return "\n\n".join(
        [
            dump_model("source_analysis", source_analysis),
            dump_model("episode_context", episode_context),
            dump_model("story_bible", story_bible),
            dump_model("script_batch", script_batch),
            dump_model("quality_report", quality_report),
            dump_model("previous_context", previous_context),
            "生成 next_round_context，保留 open_hooks、forbidden_reveals、character_knowledge、relationship_changes、prop_states、foreshadowing_ledger。",
        ]
    )
