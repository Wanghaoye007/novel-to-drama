from __future__ import annotations

import re

from pydantic import BaseModel

from novel_drama_engine.methodology import render_methodology_context
from novel_drama_engine.models import MethodologyContext


def dump_model(name: str, model: BaseModel | None) -> str:
    if model is None:
        return f"{name}: null"
    return f"{name}: {model.model_dump_json(indent=2)}"


def section(title: str, body: str) -> str:
    return f"【{title}】\n{body.strip()}"


def prompt_block(*parts: str) -> str:
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


def stage_system(
    role: str,
    mission: str,
    method: str,
    output_discipline: str,
    failure_modes: str,
) -> str:
    return prompt_block(
        section("岗位", role),
        section(
            "Skill 边界",
            (
                "本阶段按一个可复用内部 Skill 包运行：只消费本阶段输入资产，只产出 schema 要求的结构化 artifact；"
                "不与用户对话，不增加确认门，不把内部分析字段写进用户可见正片。"
            ),
        ),
        section("任务", mission),
        section("专业方法", method),
        section("输出纪律", output_discipline),
        section(
            "验收门",
            (
                "交付前自检：输入资产已被引用，执行步骤可复现，输出字段满足 schema，"
                "关键结论有原文/上游 artifact 依据，失败模式已被主动规避。"
            ),
        ),
        section("失败模式", failure_modes),
    )


def stage_instruction(
    task: str,
    decision_order: str,
    output_contract: str,
    craft_standard: str,
    forbidden: str,
) -> str:
    return prompt_block(
        section(
            "Skill 包运行规范",
            (
                "这是生产流水线中的一个内部 Skill：先明确输入资产，再按步骤执行，"
                "再按输出契约生成 schema artifact，最后用验收门自检。不等待用户确认，不输出过程解释。"
            ),
        ),
        section("任务", task),
        section(
            "输入资产",
            (
                "只能使用本 prompt 中提供的小说原文、previous_context、source_analysis、"
                "viral_asset_report、episode_context、story_bible、series_structure_plan、"
                "episode_plan、script_batch、quality_report 等资产。缺失资产要在允许范围内保守推断，"
                "不得凭空引入与原文冲突的人物、地点、道具、身份线或平台卖点。"
            ),
        ),
        section("通用改编合同", SOURCE_ADAPTATION_CONTRACT),
        section("决策顺序", decision_order),
        section("执行步骤", decision_order),
        section("输出契约", output_contract),
        section("专业标准", craft_standard),
        section(
            "验收门",
            (
                "输出前逐项检查：是否覆盖目标集数/目标字段；是否有可见动作、证据、道具、信息差或关系变化；"
                "是否避免抽象词和模板串戏；是否能被下一阶段直接消费。任何不满足项都要在本次输出内自修正。"
            ),
        ),
        section(
            "失败修复",
            (
                "如果发现内容太短、缺集、题材错配、镜头不可执行、结尾钩子说明化、内部字段外露、"
                "或信息增量不足，必须直接重写对应字段/集数，不要解释原因，也不要把问题留给用户。"
            ),
        ),
        section("禁止事项", forbidden),
    )


GLOBAL_PROFESSIONAL_FRAME = (
    "本系统采用“题材诊断 -> 爆款资产提纯 -> 集数/上下文解析 -> 系统 Story Bible -> "
    "全剧结构 -> 单集戏剧工程 -> 可拍摄脚本 -> 质量门禁 -> 状态回写”的流水线。"
    "每一阶段都只做自己的专业职责，不能越权写成下一阶段成稿，也不能要求用户确认。"
)

SOURCE_ASSET_TAXONOMY_RULE = (
    "原文资产分级：C0 不可改事实（人物动机、主动方、因果顺序、关键决定、关系状态、已存在证据）；"
    "C1 必保名场面（高刺激开场、强反差画面、情绪爆点、关键道具、原文金句、公开羞辱/打脸节点）；"
    "C2 可视听化资产（内心戏、长叙述、环境描写、感官细节，可转成特写、OS、动作、音效、镜头遮挡）；"
    "C3 可压缩资产（过渡、寒暄、背景补充、低信息支线，可合并进对白或动作）；"
    "C4 禁止新增（会改变动机、主动方、决策时机、证据来源、人物性格、关系结论或剧情解法的编造动作/道具/狠话）。"
)

HOOK_STRATEGY_RULE = (
    "开场钩子双模式：先判断原文是否已有 C1 天然钩子。"
    "原文有强钩子时，必须保护钩子的核心危险、反差、羞辱、误会、身份或证据张力，只能合规视听化，不能删除或降级成普通开场；"
    "遇到敏感/暧昧/暴力/压迫型钩子，用手部、道具、衣料/遮挡、镜头扫过、声音先入、反应特写和空间压迫表达，不把冲突拿掉。"
    "原文无强钩子时，系统必须补一个事实兼容型钩子，可选结果前置、冲突前置、信息差前置、道具前置、关系错位前置、威胁前置；"
    "补钩子只能从 C0/C1/C2 推导，不能凭空制造主角没有的欲望、对手没有的行为、原文不存在且改变因果的证据或道具。"
)

ADAPTATION_LICENSE_RULE = (
    "改编许可边界：允许前置、压缩、换场、合并低价值段落、增加镜头细节、补动作衔接、把内心戏转 OS/特写/沉默决定；"
    "谨慎允许补短对白、补反应镜头、补中间动作，但必须服务原文已有情绪或信息；"
    "禁止改变 C0：不得改变主动方、人物核心动机、核心决定发生时机、因果顺序、关系状态、既有承诺/证据/协议/身份归属；"
    "不得把深思熟虑改成临时起意、把被动承受改成主动索取、把克制决绝改成歇斯底里、把原文强反差改成泛化冲突。"
)

FIDELITY_DRIFT_RULE = (
    "通用跑偏阻断：如果原文是“对手主动承诺/诱导/准备惊喜”，不得改成主角主动索要资源、名分、奖项或好处；"
    "如果原文是“协议/证据/离开决定早已准备”，不得改成现场赌气、临时起意或一怒之下；"
    "如果原文人物是沉默、僵住、克制、冰冷、决绝，不得改成喊口号式宣战或歇斯底里狠话；"
    "如果原文开场含暧昧、危险、被镜头拍到、身体距离、衣料/手部/遮挡等高张力资产，必须合规视听化保留压力，"
    "不能直接删除成普通对话开场。"
)

THREE_THREE_THREE_RHYTHM_RULE = (
    "3-3-3 节奏规则：前 3 秒必须用可见冲突、悬念或反转留人；"
    "每约 30 秒必须有情绪波动、信息增量或剧情推进之一；"
    "每集结尾必须用反转、危机或选择钩子截断，并能被下一集开头承接。"
    "不满足的段落视为水段，必须删除、压缩或改成可拍冲突。"
)

RELATIONSHIP_READABILITY_RULE = (
    "人物关系可读性：任何两个角色第一次同框、关系身份发生反转，或角色使用昵称/姐/哥/嫂子/霍总等熟称时，"
    "必须在同场前 3-5 行用一个可拍动作、称呼回应或短台词交代观众需要知道的表层关系。"
    "如果戏剧点是“认识这个人但不知道真实身份/资源/阵营”，台词必须限定疑问对象，例如"
    "“我知道你是小雅，可你哪来的私人飞机？”“你不是我的助理吗？”"
    "禁止写成先亲密称呼、后又泛问“你到底是谁/我们认识吗”的矛盾表达，"
    "否则观众会看不懂两人到底认不认识。"
    "隐藏身份可以留悬念，但表层关系、角色已知信息和未知层级必须清楚。"
)

CHARACTER_AGENCY_RULE = (
    "人物行动权规则：主角必须按原文情绪资产递进，尤其是受压、震惊、僵住、心碎、克制、清醒、决绝等阶段，"
    "要写成“承受/识别 -> 做决定 -> 采取动作 -> 付代价或反击”的可拍链路；"
    "不得在原文没有重生、预知、马甲、提前布局或明确信息差时，把主角过早写成全知全能式开杀。"
    "支持型角色只能提供选择权、证据、退路、后盾和安全感，不能替主角签字、替主角决定、替主角报仇或一手解决核心冲突；"
    "对手/反派每轮必须有主动设局、反制、施压、毁证、挑拨、封锁或升级动作，不能只写惊慌、陪衬或躲在强者身边。"
)

EVENT_LEDGER_RULE = (
    "全局事件账本：高价值名场面和关键结果必须按“首次兑现 -> 后果承接 -> 反扑升级”推进，"
    "不能在不同集重复写成新的同类事件。亲密关系公开/曝光、不可逆解约/离婚/退婚/辞职、"
    "身份/真相结论公开、权威裁决、机构/法务/舆论清算等一旦首次演出，"
    "后续只能写人物反应、舆论余波、对手反扑、证据推进或代价扩大，不能重新再演一遍。"
    "身份坐实、机构处罚、舆论反转、平台封禁、家族/公司/宗门/朝廷清算必须有可见证据链："
    "证据来源 -> 保存/验证/公证/权威确认 -> 公开或裁决节点 -> 外界反应 -> 对手后果，"
    "禁止一句“资本出手/热搜爆了/权威一句话”直接解决。"
)

SOURCE_ADAPTATION_CONTRACT = prompt_block(
    SOURCE_ASSET_TAXONOMY_RULE,
    HOOK_STRATEGY_RULE,
    ADAPTATION_LICENSE_RULE,
    FIDELITY_DRIFT_RULE,
    THREE_THREE_THREE_RHYTHM_RULE,
    RELATIONSHIP_READABILITY_RULE,
    CHARACTER_AGENCY_RULE,
    EVENT_LEDGER_RULE,
    (
        "所有阶段必须先保护 C0/C1，再做爆款化；爆款化不是编造新因果，而是把原文资产前置、压缩、视听化、节奏化。"
        "如果上游未显式给出分级，本阶段要在本 prompt 内临时完成分级并按分级执行。"
    ),
)

SOURCE_FIDELITY_QUALITY_RULE = (
    "原著保真质检：逐集核对是否删除了 C1 天然钩子、强反差或情绪爆点；"
    "是否把 C0 的主动方、动机、因果顺序、关键决定时机、证据来源改掉；"
    "是否新增 C4 编造道具/动作/狠话并让它改变剧情；"
    "是否让角色说出与 Story Bible 台词风格或原文欲望相反的话。"
    "必须检查人物关系可读性：第一次同框、熟称、身份反转或阵营反转时，观众能否在同场前 3-5 行看懂"
    "他们表层上是否认识、各自知道什么、不知道什么。"
    "如果出现“先叫小雅/姐姐/哥/霍总等熟称，后又泛问你到底是谁/我们认识吗”，"
    "但没有限定是在问真实身份、资源来源或隐藏阵营，必须 needs_rewrite。"
    "必须硬拦通用跑偏：对手主动承诺被改成主角主动索取、预谋决定被改成现场冲动、克制决绝被改成歇斯底里、"
    "暧昧/危险/镜头拍到等高张力开场被删除或降级。"
    "必须检查人物行动权：原文存在受压/震惊/克制递进时，脚本不得过早全知全能式开杀；"
    "支持型角色不得替主角做核心决定；对手/反派不得只惊慌陪衬，必须有可见主动反制。"
    "任一项命中必须 needs_rewrite，rewrite_instruction 要写明回到哪条 C0/C1 资产、删除哪条 C4 编造、如何用镜头补强而不是改因果。"
)

SHOT_LINKAGE_RULE = (
    "镜头衔接硬验收：整集至少 3 条 action 必须原文包含以下任一衔接词："
    "切到、切回、反打、接、视线匹配、声音先入、音效、BGM、道具特写、前景。"
    "不要只写“中近景，人物做事”；要写“中近景推近A，杯子占前景，切到B发白的指节”。"
)

ACTION_LINE_TEMPLATE_RULE = (
    "action 行硬格式：每条 action.text 必须以“△景别+运镜”开头，例如"
    "“△中近景推近女主侧脸，手机屏幕占前景，BGM骤停，切到温铮发白的指节”。"
    "禁止以“△女主/△温铮/△他/△她/△门外/△突然”直接开头。"
)

FINAL_TWO_LINE_RULE = (
    "最后两行硬模板：倒数第 2 行必须是 action，写清景别+运镜+道具/动作+衔接词；"
    "最后 1 行必须是强对白/强 OS/强 VO，或一个动作未完成的道具特写。"
    "最后两行禁止黑屏、转场、画面定格、旁白总结、普通 OS、看点说明或只写情绪。"
)

INFO_INCREMENT_RULE = (
    "信息增量硬验收：每集必须把 SeriesEpisodeOutline.information_increment 和 "
    "EpisodeDramaPlan.audience_information_gap 演成可见事件、证据、关系变化、敌方策略或道具状态。"
    "从第 2 集开始，不能只延续上一集争执，至少新增 1 个观众之前不知道、角色当场不知道或角色误判的信息差。"
)

VISIBLE_SCRIPT_DENSITY_RULE = (
    "正片密度硬验收：本地质检只统计 scene.lines 渲染出来的用户可见正片文本，"
    "不统计 hook_3s、main_emotion、watch_reason、cliffhanger、state_update 或其他 JSON 字段长度。"
    "不能用长 watch_reason、长 state_update、长标题或长 cliffhanger 冒充正片字数。"
    "每集 scenes 必须 2-5 场；每集 scene.lines 合计至少 28 行，其中 action 至少 10 行、"
    "dialogue/os/vo 至少 18 行；单场不要少于 8 行。"
)


def episode_range_contract(episode_context: BaseModel) -> str:
    raw_range = str(getattr(episode_context, "target_episode_range", "") or "")
    match = re.fullmatch(r"EP(\d+)(?:-EP(\d+))?", raw_range.strip())
    if not match:
        return (
            "episodes 数组必须完整覆盖 episode_context.target_episode_range；"
            "不得缺集、跳集、合并集数或只输出摘要。"
        )
    start = int(match.group(1))
    end = int(match.group(2) or match.group(1))
    numbers = list(range(start, end + 1))
    ep_codes = "、".join(f"EP{number:02d}" for number in numbers)
    raw_numbers = "、".join(str(number) for number in numbers)
    return (
        f"episode_context.target_episode_range={raw_range}，episodes 数组必须正好包含 "
        f"{len(numbers)} 个 EpisodeScript，episode 字段必须按顺序等于 {raw_numbers}（即 {ep_codes}）。"
        "不得少集、跳集、重复集、合并多集到一集，也不得输出范围外集数。缺任一集就是失败。"
    )


def source_material_section(
    source_text: str | None,
    *,
    episode_source_packet: BaseModel | None = None,
    episode_source_packets: BaseModel | None = None,
) -> str:
    if episode_source_packet is not None:
        return section(
            "本集原文包",
            prompt_block(
                dump_model("episode_source_packet", episode_source_packet),
                (
                    "脚本阶段只能把 source_excerpt、C0/C1/C2/C3/C4、golden_lines 和 "
                    "handoff_requirement 当作本集原文依据；不得回到全文自由寻找新剧情。"
                ),
            ),
        )
    if episode_source_packets is not None:
        return section(
            "本轮原文包",
            prompt_block(
                dump_model("episode_source_packets", episode_source_packets),
                (
                    "整批脚本阶段必须逐集使用对应 packet，不得跨集挪用原文资产，"
                    "不得把其他 packet 的事件提前写入当前集。"
                ),
            ),
        )
    return f"小说原文：\n{source_text or ''}"


SOURCE_PARSER_SYSTEM = stage_system(
    "你是短剧小说解析器和素材清洗器，负责把原文拆成可拍摄生产资产。",
    (
        "只输出符合 schema 的可拍摄生产资产，不是剧情总结，不写读后感、不写人物小传、"
        "不做用户确认。每个资产都要服务拍摄、剪辑或 AI 视频后链路。"
    ),
    (
        "按“题材模板识别 -> 原文资产 C0-C4 分级 -> 主角欲望/阻力定位 -> 可见动作拆分 -> "
        "道具/场景/强对白提取 -> 低价值段落处理”的顺序工作。candidate_hooks 只能是可见动作、"
        "强对白、道具露出、威胁或反转，不能写成“观众想看什么”的抽象看点。"
    ),
    (
        "优先提取人物关系、场景、道具、可见动作、强对白、威胁、反转和低价值段落处理方式。"
        "每条信息都要能被后续阶段消费。"
    ),
    (
        "题材模板错配是严重错误：男频穿越、大宋、武大郎、金莲、西门庆、经商护妻类不得套"
        "真假千金、豪门宴会或现代豪门继承模板；古言宅斗、真假千金、赘婿战神等也不能混套。"
    ),
)
VIRAL_ASSET_SYSTEM = stage_system(
    "你是网文改爆款竖屏短剧的前置评估器，负责提纯爆款基因而不是写宣传文案。",
    (
        "提纯可被拍出来的强设定、核心困境、名场面、情绪资产、金句和改编风险。"
        "ViralAssetReport 是系统内部生产资产。"
    ),
    (
        "按“频道/题材/爽感诊断 -> 核心困境提炼 -> 原文资产 C0-C4 分级 -> 名场面分级 -> 情绪曲线抽样 -> "
        "风险替换策略”的顺序工作。"
    ),
    (
        "只服务后续 episode_context、Story Bible、SeriesStructurePlan、EpisodeDramaPlan 和脚本生成；"
        "名场面必须能落到人物、地点、动作和后果。"
    ),
    "不能写成用户可见卖点文案、投放文案、封面标题或推荐语，不能把抽象情绪当名场面。",
)
EPISODE_CONTEXT_SYSTEM = stage_system(
    "你是短剧集数和上下文解析器，负责把原文自动路由到本轮集数。",
    (
        "必须根据原文、目标总集数、round_number 和 previous_context 系统自动识别本轮轮次、"
        "本轮对应集数、原文锚点和承接约束；不得让用户确认或选择方向。"
    ),
    (
        "按“读取 previous_context.current_episode -> 计算剩余集数 -> 定义 EP 范围 -> "
        "映射原文事件 -> 写承接/禁止揭示/改编动作”的顺序工作。"
    ),
    (
        "previous_context 存在时，本轮必须从 previous_context.current_episode + 1 开始，只向后推进，"
        "不得重复已完成集数。source_to_episode_mapping 和 adaptation_actions 必须是可执行映射。"
    ),
    "不能泛写“承接上一轮/推进剧情”，不能让男频穿越/大宋/武大郎套真假千金或豪门宴会模板。",
)
BIBLE_SYSTEM = stage_system(
    "你是短剧 Story Bible 构建器，负责维护系统内部人物和世界状态合同。",
    (
        "Story Bible 是系统自动维护的内部状态，用于锁定主线、人设标签、关系、说话方式、"
        "不可改事实和禁区；不要请求用户确认。"
    ),
    (
        "按“C0 不可改事实 -> 人物功能合同 -> 关系张力 -> 台词风格 -> 禁止改动项”的顺序工作。"
    ),
    (
        "人物档案必须可被后续轮次直接执行，不能写成读者分析或等待人工补充。"
        "每个核心角色都要服务戏剧功能和短台词生成。"
    ),
    "不能把功能性配角写成多功能慢热人物，不能给反派复杂洗白，不能提前公开尚未演出的悬念。",
)
SERIES_STRUCTURE_SYSTEM = stage_system(
    "你是爆款竖屏短剧全剧结构设计师，负责把线性小说改造成可连续生产的剧集结构。",
    (
        "把原文重构为全剧节奏、每集信息增量、断点类型、原文锚点和禁水集规则。"
        "SeriesStructurePlan 是后续脚本生成的内部 SOP 环节。"
    ),
    (
        "按“全剧体量 -> 开篇钩子双模式 -> 三层冲突 -> 情绪曲线 -> 小/大高潮节拍 -> "
        "逐集信息增量 -> 断点设计”的顺序工作。"
    ),
    (
        "episode_outlines 必须可直接喂给单集设计和脚本阶段；ending_hook 要能写成最后 2 行的动作、"
        "对白或道具特写。"
        f"{THREE_THREE_THREE_RHYTHM_RULE}"
    ),
    "不写文学梗概，不制造水集，不增加用户确认门，不用“身份悬念推进/观众要看”代替具体断点。",
)
EPISODE_PLAN_SYSTEM = stage_system(
    "你是 EpisodeDramaPlan 戏剧工程师，负责把集纲转成单集戏剧机械图。",
    (
        "只做单集戏剧工程设计，不写正片脚本、分场正文或完整对白。每集必须锁定戏剧引擎、"
        "误认知/真相差、信息差、3 个以上物理动作链、场景动态、至少 2 次情绪转向、"
        "三波拉扯、假打脸、钥匙预埋、最狠短台词和结尾截断。"
    ),
    (
        "按“原文资产分级 -> 主角误认知 -> 行动链 -> 对手反制 -> 假打脸 -> 钥匙预埋 -> "
        "临门截断”的顺序设计。"
        f"{THREE_THREE_THREE_RHYTHM_RULE}"
    ),
    "所有字段都要可执行，并能被 Script 阶段直接改写成镜头、动作和短台词。",
    "不能写“增强爽感/制造悬念/推进剧情”这类抽象词，不能把单集设计写成完整剧本。",
)
SCRIPT_SYSTEM = stage_system(
    "你是爆款竖屏短剧分镜编剧，负责输出可直接拍摄、可交给 AI 视频后链路执行的剧本。",
    (
        "正片必须强冲突开场、短台词、镜头动作详细、镜头衔接清楚、每集留强钩。"
        "Hook、main_emotion、主情绪、watch_reason、消费理由等字段只作为内部元数据，"
        "禁止作为用户可见 scene lines 展示。"
    ),
    (
        "按“原文钩子保护/事实兼容补钩 -> 前三秒可见冲突 -> 三波拉扯 -> 假打脸/钥匙兑现 -> 反派最后一装 -> "
        "动作或证据截断”的顺序写。"
    ),
    (
        "每条 action 都要能指导 AI 视频：景别、运镜、构图/光线、道具、表情、声音/BGM 和切镜衔接缺一不可。"
        "结尾钩子必须在最后一场最后 2 行用动作、对白或道具特写演出。"
        f"{SHOT_LINKAGE_RULE}{FINAL_TWO_LINE_RULE}{INFO_INCREMENT_RULE}"
        f"{THREE_THREE_THREE_RHYTHM_RULE}"
    ),
    "不能写旁白式总结、消费理由说明、观众要看、本集看点、抽象心理或说明式结尾钩子。",
)
QUALITY_SYSTEM = stage_system(
    "你是短剧质检器，负责像制作总监一样判断脚本是否能拍、能留人、能进入后链路。",
    (
        "按竖屏短剧成片标准检查：3 秒留人、冲突密度、信息差、人物一致性、结尾追更、"
        "台词长度、镜头可执行性、镜头衔接和是否外露分析字段。"
    ),
    (
        "按“结构完整性 -> 原文保真 -> 开篇冲突 -> 信息增量 -> 视听可执行 -> 台词效率 -> "
        "结尾追更 -> 连续性/题材一致性”的顺序审核。"
    ),
    (
        "只要不满足可拍摄脚本标准，就必须要求重写；rewrite_instruction 要给逐集、可执行的修复方向。"
        f"{THREE_THREE_THREE_RHYTHM_RULE}"
    ),
    "必须拦截外露分析词、抽象动作、镜头衔接不足、题材模板错配和说明式结尾钩子。",
)
STATE_SYSTEM = stage_system(
    "你是短剧状态回写器，负责把本轮正片演出的事实沉淀为下一轮可继承状态。",
    (
        "只把本轮已经在剧中演出的事实、人物认知、关系变化、伏笔、道具状态和下一轮 open_hooks "
        "写回结构化状态；不得改写已锁定 Story Bible，不得补写未演出的设定。"
    ),
    (
        "按“已演事实 -> 三层认知 -> 关系变化 -> 道具/证据状态 -> 伏笔账本 -> "
        "下一轮 open hooks/forbidden reveals”的顺序回写。"
    ),
    (
        "必须区分 audience_known（观众已知）、protagonist_known（主角已知）、villain_known（反派已知），"
        "防止下一轮重复揭示或错用信息差。"
    ),
    "不能把营销看点写成 open_hook，不能把已揭示信息再次当悬念，不能改写 Story Bible。",
)


def source_parser_user(source_text: str) -> str:
    return prompt_block(
        f"小说原文：\n{source_text}",
        section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
        stage_instruction(
            "提取人物、事件、冲突、可视频化场面、低价值段落和候选 Hook。输出目标是拍摄/剪辑/AI 视频可直接消费的生产资产，不是剧情总结。",
            (
                "先判定题材和主角欲望，再拆事件的主体、动作、对象和后果；随后提取可见场面、"
                "强对白、道具、威胁和反转；最后标记低价值段落的删除、压缩或视听化方式。"
            ),
            (
                "人物要写明身份、关系、可拍标签和当场欲望；事件要拆成主体、动作、对象、"
                "地点/道具/对白和当场后果；冲突要能落到镜头动作或短台词。"
            ),
            (
                "candidate_hooks 必须是可见动作、强对白、道具露出、身份误会、威胁或反转，"
                "能被剪成前三秒画面/声音。必须在可用字段中体现原文资产 C0-C4："
                "C0/C1 写入事件、冲突、候选 hook、道具或强对白；C2/C3 写入低价值段落处理；"
                "C4 写入风险/禁止改动。低价值段落要给出删除、合并、转 OS 或转动作的处理策略。"
            ),
            (
                "不能写成“观众想看什么”“制造悬念”“爽点升级”这类概念句。"
                "题材模板保护：如果原文是男频穿越/大宋/武大郎/金莲/西门庆/经商护妻，"
                "只能围绕现代认知差、误会反转、护妻或经商打脸提取资产，"
                "不得套真假千金、豪门宴会、现代豪门继承模板。"
            ),
        ),
    )


def viral_asset_user(
    source_text: str,
    source_analysis: BaseModel,
    target_episode_count: int | None = None,
) -> str:
    target_text = str(target_episode_count) if target_episode_count else "未指定"
    return prompt_block(
        f"小说原文：\n{source_text}",
        f"目标总集数：{target_text}",
        dump_model("source_analysis", source_analysis),
        section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
        stage_instruction(
            "生成 ViralAssetReport。必须按网文改爆款竖屏短剧 SOP 做前置评估。",
            (
                "先判断频道、题材标签和核心爽感；再提炼反差世界观/强设定、核心困境、主角目标、主冲突；"
                "接着筛出大高潮名场面、小高光节点、金句和情绪曲线；最后写风险替换和删减规则。"
            ),
            (
                "这是系统内部资产，只供后续集数解析、Story Bible、全剧结构、单集设计和脚本生成消费；"
                "不得增加用户确认门。至少保留 3 个大高潮名场面和 5 个小高光节点。"
            ),
            (
                "signature_scenes 和 small_highlights 每一条都必须写成“人物 + 地点 + 可见动作 + 当场后果”，"
                "例如“林晚在宴会厅撕开亲子鉴定，宾客当场倒向她”。signature_scenes 要优先承载 C1 必保名场面；"
                "risk_treatments 必须写清 C0 不可改事实、C4 禁止新增内容，以及无天然钩子时可用的事实兼容型钩子方向。"
                "改编风险必须给替换/合并方案。"
            ),
            (
                "不得写成用户可见卖点文案、平台简介、投放文案或封面标题；不能写成抽象情绪、爽感、主题或观念；"
                "明确禁止题材模板错配，例如男频穿越/大宋不能套真假千金宴会模板。"
                "整条 SOP 全链路服务于后续脚本生成，不要要求用户确认，不要输出用户可见说明。"
            ),
        ),
    )


def episode_context_user(
    source_text: str,
    previous_context: BaseModel | None,
    source_analysis: BaseModel,
    round_number: int = 1,
    target_episode_count: int | None = None,
    episodes_per_round: int = 5,
    viral_asset_report: BaseModel | None = None,
    methodology_context: MethodologyContext | None = None,
) -> str:
    target_text = str(target_episode_count) if target_episode_count else "未指定"
    return prompt_block(
        f"小说原文：\n{source_text}",
        f"当前轮次：第 {round_number} 轮",
        f"目标总集数：{target_text}",
        f"本轮目标集数：最多 {episodes_per_round} 集",
        dump_model("previous_context", previous_context),
        dump_model("source_analysis", source_analysis),
        dump_model("viral_asset_report", viral_asset_report),
        section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
        section("内部方法论", render_methodology_context(methodology_context)),
        stage_instruction(
            "判断 target_episode_range、story_stage、must_carry_context、forbidden_reveals、source_to_episode_mapping、adaptation_actions，并给 confidence。",
            (
                "先读取 previous_context.current_episode，再计算本轮起止集；然后把原文事件映射到 EP，"
                "最后写本轮必须承接、禁止提前揭示和需要改编的动作。"
            ),
            (
                "必须由系统自动识别轮次和本轮范围，不得要求用户确认、不得让用户选择方向。"
                "如果 previous_context 存在，本轮必须从 previous_context.current_episode + 1 开始，"
                "target_episode_range 的起点必须等于这个下一集；不得重复已完成集数，"
                "也不得把已完成集数再次放入 source_to_episode_mapping。"
            ),
            (
                "如果目标总集数剩余不足本轮目标集数，则只覆盖剩余集数。"
                "target_episode_range 必须使用 EP 两位格式，例如 EP01-EP05；"
                "source_to_episode_mapping 必须写成可执行映射：每条包含原文段落/事件、目标 EP、"
                "保留的画面/对白/道具、删改理由、本集承担的信息增量，以及该映射涉及的 C0/C1/C2/C3/C4 分级。"
                "adaptation_actions 必须是可执行动作：提前、合并、删除、视听化、改断点、补信息差；"
                "每条都要标注属于允许改编、谨慎补强还是禁止改动。"
            ),
            (
                "禁止输出 1-5、第1-5集、第一轮 等非标准范围。不能泛泛写“承接上一轮”。"
                "每条 adaptation_actions 都要写明对象、动作、目标集数和预期效果，不能写“增强爽感、推进节奏”。"
                "题材模板保护：男频穿越/大宋/武大郎/金莲/西门庆类必须围绕现代认知差、"
                "误会反转、护妻/经商打脸分配集数，不能套真假千金、豪门宴会模板。"
            ),
        ),
    )


def bible_user(
    source_text: str,
    source_analysis: BaseModel,
    episode_context: BaseModel,
    viral_asset_report: BaseModel | None = None,
    methodology_context: MethodologyContext | None = None,
) -> str:
    return prompt_block(
        f"小说原文：\n{source_text}",
        dump_model("source_analysis", source_analysis),
        dump_model("viral_asset_report", viral_asset_report),
        dump_model("episode_context", episode_context),
        section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
        section("内部方法论", render_methodology_context(methodology_context)),
        stage_instruction(
            "生成内部 Story Bible。不要要求用户确认。",
            (
                "先锁定主线和不可变事实，再为每个主要角色建立人物合同，随后定义关系张力、"
                "短台词风格、戏剧功能、immutable_facts 和 forbidden_changes。"
            ),
            (
                "这是系统自动维护的内部状态，不向用户发起确认、选择或二次补充。"
                "characters 中每个主要人物必须按“姓名｜基础身份｜强记忆标签｜核心反差｜"
                "核心诉求｜终极执念｜戏剧功能”锁定，缺一项就补足。"
            ),
            (
                "speech_styles 中每个主要角色必须写短台词风格，并包含 2 个 15 字以内示例短句；"
                "台词要能指导拍摄，不写文学化长句。戏剧功能只能使用清晰职责，例如压、装、打、暴、发、拉、递证、误导、见证。"
                "immutable_facts 必须吸收 C0 不可改事实；forbidden_changes 必须吸收 C4 禁止新增和禁止改动项，"
                "尤其锁定主动方、核心动机、关键决定时机、关系状态和证据来源。"
            ),
            (
                "功能性配角只承担一个功能，不要写成多功能慢热人物。反派必须写直白动机和当场压迫手段，"
                "禁止复杂洗白、苦衷包装或长篇成长线。immutable_facts 和 forbidden_changes 只锁定不可乱改的已知事实、"
                "关系和禁区，不要把尚未演出的悬念提前公开。"
            ),
        ),
    )


def series_structure_user(
    source_text: str,
    source_analysis: BaseModel,
    episode_context: BaseModel,
    story_bible: BaseModel,
    viral_asset_report: BaseModel,
    previous_context: BaseModel | None,
    target_episode_count: int | None = None,
    methodology_context: MethodologyContext | None = None,
) -> str:
    target_text = str(target_episode_count) if target_episode_count else "未指定"
    return prompt_block(
        f"小说原文：\n{source_text}",
        f"目标总集数：{target_text}",
        dump_model("source_analysis", source_analysis),
        dump_model("viral_asset_report", viral_asset_report),
        dump_model("episode_context", episode_context),
        dump_model("story_bible", story_bible),
        dump_model("previous_context", previous_context),
        section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
        section("内部方法论", render_methodology_context(methodology_context)),
        stage_instruction(
            "生成 SeriesStructurePlan。必须把线性原文重构为可连续生产的全剧集纲。",
            (
                "先确定总集数结构和本轮 target_episode_range，再写 opening_contract、三层冲突、"
                "全局情绪曲线、小/大高潮节拍，最后落到逐集 episode_outlines 和 forbidden_slowdowns。"
            ),
            (
                "这是 SOP 中连接 Story Bible 与后续脚本生成的内部结构层，必须自动完成；"
                "不得新增用户确认门、方向选择门或人工审核节点。target_episode_range 必须等于 episode_context.target_episode_range；"
                "target_episode_count 使用用户目标；如果未指定，也要说明本轮结构依据。"
            ),
            (
                "opening_contract 至少 3 条，覆盖前 3 集的“抛设定 -> 制造困境 -> 主角行动”。"
                "opening_contract 必须显式判断开场钩子双模式：原文有 C1 天然钩子时写保护/视听化方式；"
                "原文无天然钩子时写事实兼容型钩子的来源、前置方式和不改变 C0 的理由。"
                "global_emotion_curve、small_climax_cadence、big_climax_cadence 必须共同约束全剧节奏，"
                "按平均每 3 集一个小高潮、每 8 集一个大高潮规划，不能只写本轮局部剧情。"
                "每集必须有独立信息增量：新增证据、关系变化、身份认知、道具状态、敌我策略或不可逆后果。"
                "character_profiles 必须按身份、标签、反差、诉求、执念、功能、台词风格输出；"
                "conflict_stack 必须包含表层事件冲突、中层情感冲突、深层价值/宿命冲突。"
                "episode_outlines 至少覆盖本轮 target_episode_range 内全部集数，若目标总集数不超过 40，优先覆盖全剧所有集数。"
                "每集必须有核心事件、情绪节点、信息增量、结尾断点类型、具体断点、原文锚点。"
                "ending_hook_type 必须是可执行断点类型，如动作未完成、强台词截断、证据露出、身份将揭未揭、威胁落下、反转前一秒；"
                "source_anchor 必须指向原文具体段落/事件/台词/场面。"
            ),
            (
                "forbidden_slowdowns 明确禁止无冲突过渡、长篇内心、泛化场景、连续水集、换场不换信息、只抒情不推进；"
                "任何 episode_outline 都不能成为水集，不能只重复上一集情绪。"
                "episode_outlines 的 ending_hook 必须是画面/动作/台词级断点，必须能直接被下一步脚本写成最后 2 行；"
                "不能写“观众想看”“身份悬念推进”“等待揭晓”“持续升级”“引发期待”这类概念，不能写“原文相关”。"
                "这是系统内部规划，不向用户请求确认，不输出用户可见说明。"
            ),
        ),
    )


def episode_plan_user(
    source_text: str,
    source_analysis: BaseModel,
    episode_context: BaseModel,
    story_bible: BaseModel,
    previous_context: BaseModel | None,
    viral_asset_report: BaseModel | None = None,
    series_structure_plan: BaseModel | None = None,
    methodology_context: MethodologyContext | None = None,
) -> str:
    return prompt_block(
        f"小说原文：\n{source_text}",
        dump_model("source_analysis", source_analysis),
        dump_model("viral_asset_report", viral_asset_report),
        dump_model("episode_context", episode_context),
        dump_model("story_bible", story_bible),
        dump_model("series_structure_plan", series_structure_plan),
        dump_model("previous_context", previous_context),
        section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
        section("内部方法论", render_methodology_context(methodology_context)),
        stage_instruction(
            "为 episode_context.target_episode_range 内每一集生成 EpisodeDramaPlan。这一步只做戏剧工程设计，不写正片脚本；保留旧约束：只做改编设计，不写完整台词剧本。",
            (
                "逐集按“误认知 -> 主角动作 -> 对手反制 -> 假打脸 -> 钥匙预埋 -> 情绪转向 -> 临门截断”设计。"
                "如果 series_structure_plan 不为空，先找到对应 SeriesEpisodeOutline，再承接 core_event、information_increment、ending_hook_type、source_anchor。"
            ),
            (
                "不要输出分场正文、连续对白、旁白成稿或成片脚本。每集必须按 EpisodeDramaPlan 字段逐项填写："
                "1. episode/title：对应本轮目标集数，标题写成可拍的冲突名；"
                "2. drama_engine：戏剧引擎，写主角基于什么误认知采取什么行动，以及这个行动如何逼出对手反制；"
                "3. protagonist_misbelief 和 truth_gap：误认知/真相差必须成对出现，说明主角以为 A、事实却是 B；"
                "4. physical_action_chain：3 个以上物理动作链，不能只写看/听/想，每一条都必须包含“主体 + 动作 + 对象 + 当场后果”；"
                "5. scene_dynamics：场景动态必须写清人物如何移动、抢夺、躲避、逼近、堵门、亮证、摔物或改换空间位置；"
                "6. emotional_turns：至少 2 次情绪转向，写清从哪种情绪转到哪种情绪，由哪一个动作/证据触发；"
                "7. audience_information_gap：观众知道但角色不知道的信息差，必须能驱动等待、误会或反打；"
                "8. three_pull_beats：三波拉扯必须是第一波压迫、第二波升级、第三波临门截断，每波都要有具体动作和即时后果；"
                "9. false_payoff：至少一次假打脸/期待落空，写清观众以为要赢，但哪一件事让胜利被重置；"
                "10. planted_key：一个早埋晚用的道具、证据、身份钥匙或口头承诺，写明本集怎么埋、后面怎么用；"
                "11. strongest_line：全集最狠的一句短台词，必须有血压感，短于 18 个汉字，不要写成解释句；"
                "12. cliffhanger_design：结尾截断必须停在动作、证据、身份或关系爆点前一秒，逼观众看下一集；"
                "13. source_assets_to_keep：按 C0/C1/C2/C3 写原文必须保留、视听化或压缩的名场面、金句、人物关系或道具；"
                "14. forbidden_shortcuts：必须写 C4 禁止新增/禁止改动，包括不得改变主动方、动机、关键决定时机、证据来源、关系状态；"
                "15. 必须写清本集高价值事件是首次兑现、后果承接还是反扑升级；已兑现的吻戏/曝光/解约/发布会类名场面不得重复演。"
            ),
            (
                "所有 EpisodeDramaPlan 字段都必须是可执行设计；必须能被 Script 阶段直接翻译成镜头、动作、台词、道具和剪辑点。"
                "如果原文无强钩子，本阶段必须在 drama_engine 或 cliffhanger_design 中补事实兼容型钩子；"
                "如果原文已有强钩子，source_assets_to_keep 必须写明保护方式。"
            ),
            (
                "禁止抽象词如“增强爽感”、“制造悬念”、“推进剧情”、“强化冲突”、“情绪拉满”，必须改成谁做什么、对谁做、造成什么当场后果。"
                "不得写成与全剧节奏无关的孤立桥段。保持题材 guard：如果是男频穿越 / 大宋 / 武大郎 / 金莲 / 西门庆类，"
                "drama_engine 必须走现代认知差、轻喜误会反转、护妻/经商打脸，不得套真假千金、豪门认亲、宴会验亲或亲哥哥救场模板。"
            ),
        ),
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
    episode_plan: BaseModel | None = None,
    viral_asset_report: BaseModel | None = None,
    series_structure_plan: BaseModel | None = None,
    methodology_context: MethodologyContext | None = None,
    episode_source_packets: BaseModel | None = None,
) -> str:
    target_text = str(target_episode_count) if target_episode_count else "未指定"
    return prompt_block(
        source_material_section(
            source_text,
            episode_source_packets=episode_source_packets,
        ),
        f"当前轮次：第 {round_number} 轮",
        f"目标总集数：{target_text}",
        section("本轮集数硬清单", episode_range_contract(episode_context)),
        dump_model("source_analysis", source_analysis),
        dump_model("viral_asset_report", viral_asset_report),
        dump_model("episode_context", episode_context),
        dump_model("story_bible", story_bible),
        dump_model("series_structure_plan", series_structure_plan),
        dump_model("episode_plan", episode_plan),
        dump_model("previous_context", previous_context),
        f"rewrite_instruction: {rewrite_instruction}",
        section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
        section("内部方法论", render_methodology_context(methodology_context)),
        stage_instruction(
            "必须输出 episode_context.target_episode_range 覆盖的全部集数，最多 5 集。",
            (
                "逐集先读 EpisodeDramaPlan 和 SeriesEpisodeOutline，确认本集核心事件、信息增量、断点类型和原文锚点；"
                "再按原文资产分级决定“保护 C0/C1、视听化 C2、压缩 C3、删除 C4”，"
                "最后写前三秒可见冲突、三波拉扯、假打脸/钥匙兑现、反派最后一装和结尾截断。"
            ),
            (
                "如果 episode_plan 不为空，必须逐集执行对应 EpisodeDramaPlan：drama_engine 决定本集动作逻辑，"
                "three_pull_beats 决定场景推进，false_payoff/planted_key/cliffhanger_design 必须在剧本中兑现或预埋。"
                "如果 series_structure_plan 不为空，必须逐集执行对应 SeriesEpisodeOutline 的核心事件、信息增量、断点类型和原文锚点；"
                "不能为了写爽点而断开全剧结构。如果 viral_asset_report 不为空，至少保留本轮相关名场面/金句/情绪资产，"
                "并按 risk_treatments 避开敏感设定和慢热支线。"
                "如果原文已有 C1 天然钩子，第一场必须保留其核心张力并合规视听化；"
                "如果原文没有天然钩子，第一场必须补事实兼容型钩子，并在动作/对白里能追溯到 source_anchor 或 C0/C1/C2。"
                "任何新增动作、道具、证据、狠话都必须只补镜头或衔接，不能改变主角欲望、主动方、因果顺序或关键决定时机。"
                "必须执行事件账本：同一高价值名场面不能跨集重复兑现；身份/机构/舆论/权威裁决类结果必须先写清证据来源和流程，再写结果。"
                "episode 字段必须是数字集数；scene.heading 必须严格写成 “集数-场次 日/夜-内/外-具体地点”，例如 1-1 夜-内-武家卧室，"
                "禁止只写 豪华宴会厅、走廊、房间、街上 这类泛化场景头。"
            ),
            (
                "每集仍需填充 3 秒 Hook、主情绪、watch_reason、cliffhanger、state_update，"
                "但这些是系统内部字段，不能在剧本文本里以“3秒 Hook/主情绪/消费理由/观众要看”单独展示；"
                "必须把 hook 融入第一场的第一组动作、VO/OS 或对白。"
                "cliffhanger 字段必须直接填写最后一场最后 4 行里已经演出来的钩子台词或动作，"
                "禁止写成“留下悬念/关于身份的悬念/气氛紧张”等说明句。"
                "Hook/main_emotion/watch_reason/消费理由只允许出现在 EpisodeScript 结构化字段中，"
                "不得出现在任何 scene.lines 的 action/dialogue/os/vo/transition 文本里。"
                "watch_reason 只能写给系统分析，禁止把“观众想看/消费理由/看点”写入任何 scene line。"
                f"{VISIBLE_SCRIPT_DENSITY_RULE}"
                "每集优先 3 个可拍摄场景，最低 2 场。参照标杆短剧密度：每集 800-1700 字，"
                "2-5 场，至少 10 条 △/镜头动作行，至少 18 条对白/OS/VO。"
                "前 8 个 beat 必须爆出危机、羞辱、误会、威胁或强反击，至少 2 句高压短台词，"
                "结尾钩子必须是强疑问、威胁、反转或动作未完成。OS 后必须紧跟物理动作或明确决定，不能只做心理解释。"
                "对白尽量短，一句不超过 22 个汉字，只表达一个动作或情绪；不能用解释型长句、书面复句、价值观总结，长 OS 必须拆成多行。"
                "每条 action 必须写清景别、主体位置、镜头运动、构图/光线、关键道具、人物表情、声音或 BGM 触发点，"
                "并用切镜、反打、视线匹配、声音先入、道具特写或动作接动作说明镜头衔接，方便后链路 AI 执行。"
                "每条 action 必须显式包含一个景别词（全景/中景/中近景/近景/特写/俯拍/仰拍/长焦）"
                "和一个运镜词（推近/拉远/横移/跟拍/摇向/甩向/切到/扫过/快剪/拉焦/环绕/上移/定格/慢镜头）。"
                f"{ACTION_LINE_TEMPLATE_RULE}"
                f"{SHOT_LINKAGE_RULE}"
                f"{INFO_INCREMENT_RULE}"
                "如果一条 action 写不下全部生产信息，就拆成连续 action；不得省略道具、表情、声音/BGM 或镜头衔接。"
                "合格 action 示例：△中近景推近武植侧脸，油灯在画面左上晃动，药碗占前景，他一把压住碗沿，切到金莲发白的指节。"
                "不合格 action 示例：△武植在床上睁开眼。/ △宴会厅内，灯光璀璨，众人震惊。"
            ),
            (
                "不能先写背景介绍。第一场前三行建议为：△强画面动作 -> 反派/危机短台词 -> 主角动作或 OS+动作。"
                "不能把主角写出原文没有的功利诉求、求取目标或歇斯底里狠话；台词风格必须服从 Story Bible 和 C0 人物动机。"
                "不得把预谋决定写成临场冲动，不得把对手主动承诺/欺骗改成主角主动索要，不得用编造道具替代原文证据。"
                "最后一场最后 2 行必须把 cliffhanger 以对白、动作或道具特写演出来，不要只把 cliffhanger 填在字段里，"
                "也不要新增“结尾钩子：/cliffhanger：”说明行。"
                f"{FINAL_TWO_LINE_RULE}"
                "禁止旁白式总结、价值观说明、消费理由说明、观众要看、本集看点、本集钩子等外露分析。"
                "如果原文是男频穿越/大宋/武大郎/金莲/西门庆类，必须使用现代认知 OS + 立刻动作 + 轻喜打脸节奏，"
                "不能套用真假千金/豪门模板。"
            ),
        ),
    )


def script_episode_user(
    source_text: str | None,
    source_analysis: BaseModel,
    episode_context: BaseModel,
    story_bible: BaseModel,
    previous_context: BaseModel | None,
    existing_episode: BaseModel | None,
    episode_number: int,
    rewrite_instruction: str,
    episode_plan: BaseModel | None = None,
    viral_asset_report: BaseModel | None = None,
    series_structure_plan: BaseModel | None = None,
    methodology_context: MethodologyContext | None = None,
    episode_source_packet: BaseModel | None = None,
    previous_episode_handoff: BaseModel | None = None,
) -> str:
    return prompt_block(
        source_material_section(
            source_text,
            episode_source_packet=episode_source_packet,
        ),
        f"只生成第 {episode_number} 集。不要输出其他集数。",
        dump_model("previous_episode_handoff", previous_episode_handoff),
        dump_model("source_analysis", source_analysis),
        dump_model("viral_asset_report", viral_asset_report),
        dump_model("episode_context", episode_context),
        dump_model("story_bible", story_bible),
        dump_model("series_structure_plan", series_structure_plan),
        dump_model("previous_context", previous_context),
        dump_model("existing_episode_to_rewrite", existing_episode),
        dump_model("episode_plan", episode_plan),
        f"rewrite_instruction: {rewrite_instruction}",
        section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
        section("内部方法论", render_methodology_context(methodology_context)),
        stage_instruction(
            f"输出必须是一个 EpisodeScript；episode 字段必须等于 {episode_number}。这是整轮失败后的逐集修复，不要压缩复述 existing_episode，要按可拍摄正片重写。",
            (
                "先定位 existing_episode 的失败点和 rewrite_instruction 的硬伤；再回到本集 EpisodeDramaPlan / "
                "SeriesEpisodeOutline 找核心事件、信息增量、ending_hook_type 和 source_anchor；"
                "随后按 C0/C1/C2/C3/C4 校准可改边界，再重写前三秒冲突、三波拉扯、假打脸/钥匙、最狠短台词、最后 2 行钩子。"
            ),
            (
                "如果 episode_plan 不为空，必须优先执行本集 EpisodeDramaPlan 的 drama_engine、"
                "three_pull_beats、false_payoff、planted_key、strongest_line 和 cliffhanger_design。"
                "如果 series_structure_plan 不为空，必须对齐本集 SeriesEpisodeOutline 的 "
                "core_event、information_increment、ending_hook_type 和 source_anchor。"
                "如果 episode_source_packet 不为空，必须优先使用 packet.source_excerpt 和 C0/C1/C2/C4，"
                "不得从全文或其他集 packet 自由补剧情。"
                "如果 previous_episode_handoff 不为空，第一场前 3-6 行必须照应上一集最后钩子，"
                "不能重开一个无关场面。"
                "逐集修复必须是“回到原文资产 + 补镜头密度”，不能把修复写成新剧情。"
                "若 existing_episode 删除了 C1 天然钩子，要恢复并合规视听化；若原文没有天然钩子，只能补事实兼容型钩子。"
                "必须删除 C4 编造动作/道具/台词，尤其是改变主动方、动机、关键决定时机、证据来源或关系状态的内容。"
                f"scene.heading 必须严格写成 “{episode_number}-场次 日/夜-内/外-具体地点”，例如 {episode_number}-1 夜-内-武家卧室。"
                f"{VISIBLE_SCRIPT_DENSITY_RULE}"
                "本集 900-1500 字，优先 3 场，至少 2 场；至少 10 条 action，至少 18 条 dialogue/os/vo。"
            ),
            (
                "第一场前 8 个 beat 必须有危机、误会、羞辱、威胁或强反击。"
                "每条 action 必须以 △ 开头，并写清景别、主体位置、镜头运动、构图/光线、关键道具、"
                "人物表情、音效/BGM 触发和切镜衔接。每条 action 必须显式包含一个景别词"
                "（全景/中景/中近景/近景/特写/俯拍/仰拍/长焦）和一个运镜词"
                "（推近/拉远/横移/跟拍/摇向/甩向/切到/扫过/快剪/拉焦/环绕/上移/定格/慢镜头）。"
                f"{ACTION_LINE_TEMPLATE_RULE}"
                f"{SHOT_LINKAGE_RULE}"
                f"{INFO_INCREMENT_RULE}"
                "OS 后必须紧跟物理动作或明确决定；对白一句不超过 22 个汉字，只表达一个动作或情绪。"
                "hook_3s/main_emotion/watch_reason 只是内部字段，必须把 hook 融入第一场的动作、OS/VO 或对白。"
                "cliffhanger 字段必须直接填写最后一场最后 4 行里已经演出来的钩子台词或动作，"
                "禁止写成“留下悬念/关于身份的悬念/气氛紧张”等说明句。"
                "Hook/main_emotion/watch_reason/消费理由不得出现在任何 scene line 文本里。"
                "结尾钩子必须是强疑问、威胁、反转或动作未完成，并在最后一场最后 2 行演出来；"
                "最后两行不能是“结尾钩子/看点/消费理由”的说明文字。"
                f"{FINAL_TWO_LINE_RULE}"
            ),
            (
                "禁止写“△ 武植在床上睁开眼”这种无景别、无运镜的动作行。"
                "禁止为了修复烈度而改变 C0，禁止把预谋改成冲动、把被动承受改成主动索取、把克制人物改成歇斯底里。"
                "不能出现“3秒 Hook/主情绪/消费理由/观众要看/本集看点”等外露分析。"
                "不能为了修复字数而加背景介绍、价值观总结、泛场景、空镜拖时或解释型长对白。"
                "不能用黑屏、转场、画面定格、普通 OS 作为最后两行钩子。"
                "如果原文是男频穿越/大宋/武大郎/金莲/西门庆类，修复必须回到现代认知差、轻喜误会反转、"
                "护妻/经商打脸，不能套真假千金、豪门宴会、总裁认亲模板。"
            ),
        ),
    )


def hook_dialogue_polish_user(
    source_text: str | None,
    source_analysis: BaseModel,
    episode_context: BaseModel,
    story_bible: BaseModel,
    previous_context: BaseModel | None,
    existing_episode: BaseModel,
    episode_number: int,
    polish_instruction: str,
    episode_plan: BaseModel | None = None,
    viral_asset_report: BaseModel | None = None,
    series_structure_plan: BaseModel | None = None,
    methodology_context: MethodologyContext | None = None,
    episode_source_packet: BaseModel | None = None,
    previous_episode_handoff: BaseModel | None = None,
) -> str:
    return prompt_block(
        source_material_section(
            source_text,
            episode_source_packet=episode_source_packet,
        ),
        f"只二次编译第 {episode_number} 集的结尾钩子和对白密度。不要输出其他集数。",
        dump_model("previous_episode_handoff", previous_episode_handoff),
        dump_model("source_analysis", source_analysis),
        dump_model("viral_asset_report", viral_asset_report),
        dump_model("episode_context", episode_context),
        dump_model("story_bible", story_bible),
        dump_model("series_structure_plan", series_structure_plan),
        dump_model("previous_context", previous_context),
        dump_model("existing_episode_to_polish", existing_episode),
        dump_model("episode_plan", episode_plan),
        f"polish_instruction: {polish_instruction}",
        section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
        section("内部方法论", render_methodology_context(methodology_context)),
        stage_instruction(
            (
                f"输出必须是一个完整 EpisodeScript；episode 字段必须等于 {episode_number}。"
                "这是结尾钩子/对白密度二次编译，不是整集重写；不要整集重写。"
            ),
            (
                "先读 polish_instruction 的本地缺口；再定位 existing_episode 最后一场最后 8-12 行；"
                "最后只围绕短对白补足、OS 后动作承接、最后两行追更断点做最小改动。"
                "润色前必须核对本集 C0/C1：能增强镜头和短台词，不能改主角动机、主动方、因果顺序、关键决定时机或证据来源。"
            ),
            (
                "除最后 8-12 行、必要短对白/OS/VO 补足、OS 后紧跟动作外，必须保留 existing_episode 的"
                "标题、场景顺序、人物、已合格 action、信息状态和主线事实。"
                "如果 episode_plan / series_structure_plan 提供 cliffhanger_design 或 ending_hook_type，"
                "最后两行必须优先兑现该设计。"
                "如果 episode_source_packet 不为空，所有新增动作/道具/短对白必须可追溯到 packet 的 C0/C1/C2 或本集已出现内容。"
                "如果 previous_episode_handoff 不为空，不得改掉本集开头对上一集钩子的承接。"
                "如果 existing_episode 已正确保留 C1 名场面，不得为了更强钩子替换成无原文依据的新道具/新狠话；"
                "如果结尾要新增道具特写或威胁，只能使用本集已出现或上游已埋的资产。"
            ),
            (
                "结尾必须停在观众最想看下一秒的位置：身份将揭未揭、证据将爆未爆、威胁将落未落、"
                "关键道具亮出但未解释、强问题抛出但未回答。"
                "cliffhanger 字段必须直接填写最后 4 行里已经演出来的钩子台词或动作，"
                "禁止写成“留下悬念/关于真实身份的悬念/气氛紧张”等说明句。"
                f"{ACTION_LINE_TEMPLATE_RULE}{SHOT_LINKAGE_RULE}{FINAL_TWO_LINE_RULE}{INFO_INCREMENT_RULE}"
                "短对白每句只表达一个动作或情绪，不超过 22 个汉字；为补对白密度可以加入 2-6 行短促拉扯，"
                "但不能写成长解释或价值观总结。"
            ),
            (
                "禁止把结尾写成转身离开、我需要时间、明天再说、改天解释、画面冻结、黑屏、背影收束、"
                "普通离场或冲突解决。禁止新增与 Bible 冲突的设定，禁止为了补字数重讲背景。"
                "禁止在润色阶段新增 C4 内容；禁止把克制台词改成歇斯底里宣战，禁止用编造证据制造钩子。"
            ),
        ),
    )


def quality_user(
    source_analysis: BaseModel,
    episode_context: BaseModel,
    story_bible: BaseModel,
    script_batch: BaseModel,
    previous_context: BaseModel | None,
    viral_asset_report: BaseModel | None = None,
    series_structure_plan: BaseModel | None = None,
    episode_plan: BaseModel | None = None,
    methodology_context: MethodologyContext | None = None,
) -> str:
    return prompt_block(
        dump_model("source_analysis", source_analysis),
        dump_model("viral_asset_report", viral_asset_report),
        dump_model("episode_context", episode_context),
        dump_model("story_bible", story_bible),
        dump_model("series_structure_plan", series_structure_plan),
        dump_model("episode_plan", episode_plan),
        dump_model("script_batch", script_batch),
        dump_model("previous_context", previous_context),
        section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
        section("内部方法论", render_methodology_context(methodology_context)),
        stage_instruction(
            "检查 script_batch 是否达到可交付短剧正片标准。只要出现任一硬伤，status=needs_rewrite，并在 rewrite_instruction 中逐集说明怎么补足。",
            (
                "按集检查：结构体量 -> 前 8 beat 冲突 -> EpisodeDramaPlan 执行度 -> "
                "SeriesEpisodeOutline 信息增量 -> C0/C1/C4 原著保真 -> 镜头可执行度 -> 台词效率 -> 最后 2 行追更钩子 -> "
                "状态连续性和题材模板一致性。"
            ),
            (
                "硬性拒绝以下问题：单集少于 800 字、少于 2 场、少于 8 条镜头动作、"
                "少于 16 条对白/OS/VO、开头 8 个 beat 没有爆冲突、"
                "scene.heading 不是 集数-场次 日/夜-内/外-具体地点、OS 后没有动作承接、"
                "结尾钩子太软、题材模板错配。rewrite_instruction 必须指出第几集、哪个硬伤、"
                "应该补哪些场面、镜头、动作、短台词或结尾钩子。"
                f"{SOURCE_FIDELITY_QUALITY_RULE}"
            ),
            (
                "如果 series_structure_plan 不为空，还要检查每集是否有信息增量、是否匹配对应 ending_hook_type、"
                "是否连续水集、是否偏离人物标签和全局节奏。逐集检查最后一场最后 2 行是否把 cliffhanger 演成动作、对白或道具特写；"
                "只在字段里写 cliffhanger、另起说明行或营销看点行都不合格。"
                "cliffhanger 字段必须能在最后一场最后 4 行中找到相同台词或动作；"
                "“留下悬念/关于身份的悬念/气氛紧张”等说明句不合格。"
                "必须检查第一场：原文有 C1 天然钩子但脚本删除/降级，或原文无天然钩子但脚本没有事实兼容型钩子，都不合格。"
                "必须检查人物：台词或动作若改变 Story Bible 中的人物动机、说话方式、关系状态，或把 C0 决策时机改掉，都不合格。"
                "必须检查 action 是否包含景别、运镜、构图/光线、道具、表情、音效/BGM 和镜头衔接；"
                f"{ACTION_LINE_TEMPLATE_RULE}{SHOT_LINKAGE_RULE}{FINAL_TWO_LINE_RULE}{INFO_INCREMENT_RULE}"
                "对白是否超过 22 字、是否解释价值观、是否一行塞多个信息。"
            ),
            (
                "如果用户可见剧本文本里把 hook/主情绪/watch_reason 当成独立说明展示，"
                "或出现“消费理由/观众要看/本集看点”等分析词，或 action 缺少景别/运镜/构图/衔接，"
                "或 action 只是“众人震惊/气氛凝固/他很害怕”这种抽象描述，或对白显著啰嗦，也必须重写。"
                "题材模板错配必须拦截：男频穿越/大宋/武大郎/金莲/西门庆类不得混入"
                "真假千金/豪门宴会/总裁/亲子鉴定/大小姐模板，反向也不得串戏。"
            ),
        ),
    )


def state_user(
    source_analysis: BaseModel,
    episode_context: BaseModel,
    story_bible: BaseModel,
    script_batch: BaseModel,
    quality_report: BaseModel,
    previous_context: BaseModel | None,
    episode_plan: BaseModel | None = None,
    viral_asset_report: BaseModel | None = None,
    series_structure_plan: BaseModel | None = None,
) -> str:
    return prompt_block(
        dump_model("source_analysis", source_analysis),
        dump_model("viral_asset_report", viral_asset_report),
        dump_model("episode_context", episode_context),
        dump_model("story_bible", story_bible),
        dump_model("series_structure_plan", series_structure_plan),
        dump_model("episode_plan", episode_plan),
        dump_model("script_batch", script_batch),
        dump_model("quality_report", quality_report),
        dump_model("previous_context", previous_context),
        section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
        stage_instruction(
            "生成 next_round_context，保留 open_hooks、forbidden_reveals、character_knowledge、relationship_changes、prop_states、foreshadowing_ledger。",
            (
                "先从 script_batch 最后一集向前回看本轮实际演出事实；再分离观众、主角、反派的知识层；"
                "随后记录关系变化、道具/证据状态、已埋/已回收伏笔；最后输出下一轮必须承接的 open_hooks 和 forbidden_reveals。"
            ),
            (
                "只回写 script_batch 中已经拍出来、说出来、露出来或被角色明确发现的内容；"
                "不得改写 story_bible，不得把新设定塞回 Bible，不得把未演出的小说原文当成本轮事实。"
                "character_knowledge 必须至少按 audience_known（观众已知）、protagonist_known（主角已知）、"
                "villain_known（反派已知）三类记录；每条写明谁知道什么、何时知道、哪些人仍不知道，用来维持信息差。"
            ),
            (
                "open_hooks 必须来自剧中实际演出的悬念，例如最后两行的威胁、动作未完成、"
                "道具特写、身份误会或已露出但未解释的证据；不能写营销看点、主题卖点、"
                "观众想看什么，也不能把已经揭示给观众和主角的信息再次列为 hook。"
                "forbidden_reveals 要记录下一轮不能重复揭示、不能提前公开、不能改口的事实。"
                "prop_states 必须保留关键道具/证据/伤口/文件的持有人、可见状态和最后出现位置；"
                "foreshadowing_ledger 必须标记每条伏笔是 seeded、paid_off 还是 still_open，"
                "并说明后续承接集数或禁止乱改的回收方向。"
            ),
            (
                "relationship_changes 只记录本轮已经通过动作或对白发生的关系变化，不写推测。"
                "不得把 quality_report 的问题当成剧情事实；不得把用户看点、平台卖点、主题总结写进 open_hooks；"
                "不得把已经付清的伏笔继续标 still_open，也不得把未出现的道具写入 prop_states。"
            ),
        ),
    )
