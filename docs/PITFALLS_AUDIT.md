# 小说转短剧坑点规避检查

来源：最初的 `novel_to_short_drama_pitfalls.md`，共 80 条坑点，核心结论是产品不能做成普通文本改写器，而要做成可持续控剧情、控状态、控投放素材的短剧生产链路。

## 已基本规避

- 产品形态：当前链路已拆成 `source_analysis -> episode_context -> story_bible -> episode_plan/series_structure_plan -> script_batch -> quality_report -> next_round_context`，不是单 prompt 改写。
- Story Bible：由系统自动生成并作为内部约束进入后续脚本生成，MVP 不要求用户确认。
- 轮次生成：每轮默认 5 集，`episode_context` 会自动识别本轮原文映射和目标集数范围。
- 结构化中间态：核心产物均落 JSON，包括分析、Bible、分集规划、脚本、质检、下一轮上下文。
- 爆款基础质检：已有 hook、conflict、cliffhanger、continuity、video_feasibility 评分，并可触发 rewrite/episode repair。
- 短剧脚本密度：脚本模型和本地规则已要求可拍动作、短对白、多镜头、明确 cliffhanger，避免只输出摘要。
- 状态回写：`next_round_context` 已保存 open_hooks、forbidden_reveals、character_knowledge、relationship_changes、prop_states、foreshadowing_ledger。
- 视频化意识：已有 video brief/export 基础，脚本字段里保留画面动作和镜头语言。
- 平台/本地化雏形：已有 localization profile、platform key/API key、delivery package 等平台化基础模块。
- 异步和重试：已有任务队列、worker、retry 入口；本次新增中间产物续跑，失败后不必从头重新跑完整 LLM 链路。

## 部分规避，仍需加强

- 情节资产评分：已提取 viral asset，但名场面/爽点/虐点还缺更明确的数值排序和选用记录。
- 伏笔账本：`foreshadowing_ledger` 已有，但还不是可查询、可关闭、可验证的独立 ledger。
- 谁知道什么：`character_knowledge` 已有，但缺角色级 knowledge diff 和提前泄密检测。
- 分集边界：每轮有上一轮 context，但还缺“上一集结尾改动后，下一集开头自动联动检查/修复”。
- 反转约束：`forbidden_reveals` 已有，但重大反转还未强制绑定前置伏笔。
- 人名称谓：Story Bible 有角色和 speech style，但还缺 alias/称谓许可表。
- 成本/延迟：已支持轮次、异步、缓存续跑、定向修复，但还缺模型分级、token budget 和耗时预测。
- A/B 测试：系统已有 variant 概念，但 Hook A/B、节奏 A/B、平台投放 A/B 还不是一等功能。
- 合规：有风险字段和平台基础，但上传版权、原创化程度、平台审核策略还缺完整产品入口。
- 用户修改理解：目前可以重试/重新生成，但自然语言修改转结构化指令和影响范围分析还未完整实现。

## 尚未完整规避

- 局部修改影响范围分析：修改 EP12 后自动识别影响 EP13/EP18/终局等，当前尚未形成模块。
- Story State 版本回滚：脚本版本、状态快照、计划版本、用户修改历史还未打通。
- RAG 检索：还没有按 episode、character、prop、hook、event_type、open/closed 状态的剧情检索系统。
- 摘要失真防护：下一轮 context 已结构化，但还缺从原文和状态账本重建摘要的机制。
- 完整投放素材：封面标题、前 3 秒字幕、多版本广告 Hook、评论引导、CTA 尚未作为每集标准输出。
- 模板库：真假千金、重生复仇、赘婿逆袭、Billionaire Romance 等类型模板还未产品化。

## 下一阶段优先级

1. 先做边界连续性检查：锁住上一集结尾、下一集开头、open_hooks、forbidden_reveals。
2. 再做 Story State 账本：伏笔、道具、角色知识、称谓、时间线独立建模。
3. 接着做局部修改影响范围：用户改任意一集时，先出 affected episodes，再重算相关计划/状态。
4. 然后做 A/B 与投放包：Hook/标题/封面字/CTA 多版本输出。
5. 最后做模板库和市场策略：按题材、平台、地区沉淀可复用规则。
