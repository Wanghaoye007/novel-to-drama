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
QUALITY_SYSTEM = "你是短剧质检器。检查 Hook、冲突、信息差、连续性、可拍性。"
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
                "每集输出 3 秒 Hook、主情绪、watch_reason、至少 2 个可拍摄场景、"
                "足够支撑 60-90 秒竖屏短剧的短对白/动作、cliffhanger、state_update。"
                "OS 后必须跟动作或明确决定。"
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
            "检查是否可用。若必须重写，status=needs_rewrite 并给 rewrite_instruction。",
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
