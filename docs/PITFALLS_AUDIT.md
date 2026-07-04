# 小说转短剧坑点规避检查

来源：最初的 `novel_to_short_drama_pitfalls.md`，共 80 条坑点，核心结论是产品不能做成普通文本改写器，而要做成可持续控剧情、控状态、控投放素材的短剧生产链路。

## 已基本规避

- 产品形态：当前链路已拆成 `source_analysis -> episode_context -> story_bible -> episode_plan/series_structure_plan -> script_batch -> quality_report -> next_round_context`，不是单 prompt 改写。
- Story Bible：由系统自动生成并作为内部约束进入后续脚本生成，MVP 不要求用户确认。
- 轮次生成：每轮默认 5 集，`episode_context` 会自动识别本轮原文映射和目标集数范围。
- 结构化中间态：核心产物均落 JSON，包括分析、Bible、分集规划、脚本、质检、下一轮上下文。
- 爆款基础质检：已有 hook、conflict、cliffhanger、continuity、video_feasibility 评分，并可触发 rewrite/episode repair。
- 原文资产保真：prompt 链路已加入 C0/C1/C2/C3/C4 原文资产分级、开场钩子双模式和改编许可边界；本地 `adaptation_quality_report` 已补源文锚点、强钩子、C4 禁止项和禁止提前揭露的确定性检查。
- 短剧脚本密度：脚本模型和本地规则已要求可拍动作、短对白、多镜头、明确 cliffhanger，避免只输出摘要。
- 状态回写：`next_round_context` 已保存 open_hooks、forbidden_reveals、character_knowledge、relationship_changes、prop_states、foreshadowing_ledger；`story_state_ledger` 已作为独立 artifact 写入每轮结果。
- 视频化意识：已有 video brief/export 基础，脚本字段里保留画面动作和镜头语言。
- 平台/本地化雏形：已有 localization profile、platform key/API key、delivery package 等平台化基础模块。
- 异步和重试：已有任务队列、worker、retry 入口；本次新增中间产物续跑，失败后不必从头重新跑完整 LLM 链路。

## 部分规避，仍需加强

- 情节资产评分：已提取 viral asset，但名场面/爽点/虐点还缺更明确的数值排序和选用记录。
- 原文保真自动检测：LLM 质检已要求拦截 C0 改动、C1 丢失和 C4 编造，但本地 deterministic 质检还没有做逐句 source diff 和自动证据定位。
- 伏笔账本：`foreshadowing_ledger` 已有，但还不是可查询、可关闭、可验证的独立 ledger。
- 谁知道什么：`character_knowledge` 已有，但缺角色级 knowledge diff 和提前泄密检测。
- 分集边界：每轮有上一轮 context，但还缺“上一集结尾改动后，下一集开头自动联动检查/修复”。
- 反转约束：`forbidden_reveals` 已有，但重大反转还未强制绑定前置伏笔。
- 人名称谓：Story Bible 有角色和 speech style，但还缺 alias/称谓许可表。
- 成本/延迟：已支持轮次、异步、缓存续跑、定向修复，并在轮次页展示 runtime token、估算成本和最慢阶段；后续仍需模型分级、token budget 和生成前耗时预测。
- A/B 测试：质量样本回归已支持 sample × variant 多策略对比，并在质量页展示源文一致性/承接分；Hook/节奏/平台投放 A/B 仍需进一步产品化。
- 合规：有风险字段和平台基础，但上传版权、原创化程度、平台审核策略还缺完整产品入口。
- 用户修改理解：已有单集编辑影响分析 API 和页面入口，可识别后续受影响集、相关状态项和建议重跑起点；自然语言修改转结构化指令仍需增强。

## 尚未完整规避

- 局部修改影响范围分析：已有 v1，可根据结尾变化、人物/道具/钩子词和 ledger 判断直接后续影响；跨轮远期影响和自动重算计划仍需加强。
- Story State 版本回滚：脚本版本、状态快照、计划版本、用户修改历史还未打通。
- RAG 检索：还没有按 episode、character、prop、hook、event_type、open/closed 状态的剧情检索系统。
- 摘要失真防护：下一轮 context 已结构化，但还缺从原文和状态账本重建摘要的机制。
- 完整投放素材：封面标题、前 3 秒字幕、多版本广告 Hook、评论引导、CTA 尚未作为每集标准输出。
- 模板库：真假千金、重生复仇、赘婿逆袭、Billionaire Romance 等类型模板还未产品化。

## 下一阶段优先级

1. 加强 source fidelity scorer 的证据定位：从“关键词/锚点命中”升级到原文段落 span、脚本证据行和差异解释。
2. 加强 Story State 账本：支持 open/closed 状态、回滚、跨轮查询、角色 knowledge diff。
3. 加强局部修改影响范围：编辑后自动生成结构化修复指令，并可选择从受影响集开始重跑。
4. 做 Hook/标题/封面字/CTA 投放包多版本输出。
5. 做 RAG 检索和摘要失真防护：按 episode、character、prop、hook、event_type 检索状态。
6. 做模板库和市场策略：按题材、平台、地区沉淀可复用规则。
