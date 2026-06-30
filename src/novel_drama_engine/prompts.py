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
LOCALIZATION_SYSTEM = "你是短剧本地化编剧。把可拍摄短剧脚本改成本地市场可直接制作和投放的版本。"


def source_parser_user(source_text: str) -> str:
    return f"小说原文：\n{source_text}\n\n提取人物、事件、冲突、可视频化场面、低价值段落和候选 Hook。"


def episode_context_user(
    source_text: str,
    previous_context: BaseModel | None,
    source_analysis: BaseModel,
) -> str:
    return "\n\n".join(
        [
            f"小说原文：\n{source_text}",
            dump_model("previous_context", previous_context),
            dump_model("source_analysis", source_analysis),
            "判断 target_episode_range、story_stage、must_carry_context、forbidden_reveals、adaptation_actions，并给 confidence。",
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
) -> str:
    return "\n\n".join(
        [
            f"小说原文：\n{source_text}",
            dump_model("source_analysis", source_analysis),
            dump_model("episode_context", episode_context),
            dump_model("story_bible", story_bible),
            dump_model("previous_context", previous_context),
            f"rewrite_instruction: {rewrite_instruction}",
            "每集输出 3 秒 Hook、主情绪、watch_reason、场景、cliffhanger、state_update。OS 后必须跟动作或明确决定。",
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


def localization_user(
    round_result: BaseModel,
    locale: str,
    platform: str,
    guidance: str,
) -> str:
    return "\n\n".join(
        [
            dump_model("round_result", round_result),
            f"target_locale: {locale}",
            f"target_platform: {platform}",
            f"guidance: {guidance or 'none'}",
            "输出 LocalizedScriptBatch。保留原剧的核心爽点、信息差、反转和结尾钩子；允许替换称谓、场景细节、口语表达和文化符号，使其适合目标地区和平台。",
            "episodes 必须是可拍摄脚本，不要只给摘要。compliance_notes 写出目标平台或地区可能需要注意的风险。",
        ]
    )
