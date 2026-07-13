# Prompt Skill Architecture

本项目的改编内核按内部 Skill 包组织，而不是把所有要求塞进一个大 prompt。
每个阶段都是一个可替换、可测试、可 A/B 的生产单元。

## Runtime Spine

固定主线：

```text
source analysis -> viral asset extraction -> episode/context resolver
-> system-owned Story Bible -> series structure -> episode drama plan
-> script generation -> quality gate -> state writeback
```

硬约束：

- Story Bible 由系统自动生成和维护，不走用户确认。
- 第二轮及后续轮次根据原文、目标集数和 previous_context 自动识别集数范围。
- Hook、main_emotion、watch_reason、消费理由只允许作为内部字段，不得出现在用户可见剧本文本里。
- 所有阶段必须遵守“原文资产分级 -> 钩子双模式 -> 改编许可边界”：先保护原文不可改资产，再做爆款化增强。
- 每集必须输出可拍摄正片，而不是剧情摘要、看点说明或营销文案。

## Source Fidelity Contract

每个 user prompt 都会注入通用改编合同，避免“为了爽点改坏原文”：

- C0 不可改事实：人物动机、主动方、因果顺序、关键决定、关系状态、已存在证据。
- C1 必保名场面：高刺激开场、强反差画面、情绪爆点、关键道具、原文金句、公开羞辱/打脸节点。
- C2 可视听化资产：内心戏、长叙述、环境描写、感官细节，可转成特写、OS、动作、音效、镜头遮挡。
- C3 可压缩资产：过渡、寒暄、背景补充、低信息支线，可合并进对白或动作。
- C4 禁止新增：会改变动机、主动方、决策时机、证据来源、人物性格、关系结论或剧情解法的编造内容。

开场钩子使用双模式：

- 原文有强钩子：保护核心张力，做合规视听化，不能删除或降级成普通开场。
- 原文无强钩子：补事实兼容型钩子，只能从 C0/C1/C2 推导，可做结果前置、冲突前置、信息差前置、道具前置、关系错位前置。

改编许可边界：

- 允许：前置、压缩、换场、合并低价值段落、增加镜头细节、补动作衔接、把内心戏转 OS/特写/沉默决定。
- 谨慎允许：补短对白、补反应镜头、补中间动作，但必须服务原文已有情绪或信息。
- 禁止：改变 C0；不得把深思熟虑改成临时起意、把被动承受改成主动索取、把克制决绝改成歇斯底里。

## Stage Contract

每个 stage prompt 必须包含以下结构：

- 岗位：本阶段的专业角色。
- Skill 边界：只消费本阶段输入资产，只产出 schema artifact，不越权。
- 任务：本阶段要完成的唯一目标。
- 专业方法：执行方法和判断顺序。
- 输出纪律：字段、格式、可被下游消费的要求。
- 验收门：输出前自检，不合格就在本阶段自修正。
- 失败模式：必须主动规避的问题。

每个 user prompt 必须包含以下结构：

- Skill 包运行规范
- 输入资产
- 决策顺序
- 执行步骤
- 输出契约
- 专业标准
- 验收门
- 失败修复
- 禁止事项

## Script Quality Gate

当前本地硬门槛：

- 单集 800-1700 字。
- 每集 2-5 场，优先 3 场。
- 每集至少 28 行用户可见 scene line。
- 每集至少 10 条 action。
- 每集至少 18 条 dialogue/os/vo。
- 至少 8 条 action 同时具备可执行景别和镜头运动。
- 至少 3 条 action 具备镜头衔接词。
- action 行必须尽量以 `△景别+运镜` 开头，例如：

```text
△中近景推近女主侧脸，手机屏幕占前景，BGM骤停，切到温铮发白的指节。
```

禁止示例：

```text
△女主站在门口。
△突然有人冲进来。
△众人震惊。
```

## A/B Test Handles

优先从这些位置做 A/B：

- `GenerationVariant.CURRENT_DENSITY`
- `GenerationVariant.DRAMA_ENGINE_FIRST`
- `GenerationVariant.SOP_FULL_STACK`
- `EPISODE_PLAN_SYSTEM` 的戏剧工程强度
- `SCRIPT_SYSTEM` 的镜头密度和结尾钩子规则
- `QUALITY_SYSTEM` 的阻断阈值
- `script_quality.py` 的本地硬门槛
- `script_novelty_report` 的跨集重复/新鲜度硬门槛：场景骨架、动作链、对白句式、结尾钩子不能连续换皮
- `NOVEL_DRAMA_SCRIPT_EPISODE_FIRST=0` 的整轮首稿路径；设为 `1` 可测试逐集生成/失败修复，但要重点检查上下集承接
- `NOVEL_DRAMA_EXPERIMENT_MODE=1` 的无缓存追踪路径；每次 A/B 都要保留 `prompt_trace.json`、`raw_llm_output.jsonl`、`prompt_trace_analysis.md`
- `creative_script.md` vs `shooting_script.md` 的分离产物；前者评戏，后者评 AI 视频执行可拍性，不能混成一个门槛
- `source_evidence_report.md` 的 source span evidence；每个 retained asset 要能追到原文行、脚本行和改写原因，用来判断强原文轻改是否真的执行
- `quality_user` / `state_user` 默认消费 `script_batch_digest`，只给集数摘要、场景骨架、开头/结尾关键行和状态更新；完整剧本文本留在 artifact 与本地确定性 gate，避免 QA/状态回写 prompt 过载
- Story State Ledger 会把 previous_context 的 open hook 和同轮 episode cliffhanger 标为 open/closed：如果下一轮开头或下一集开头已承接则关闭；如果 next_round_context 没带最终钩子，会写 warning，防止下一轮开头丢承接

推荐 A/B 指标：

- 单集可见字数
- action / dialogue / OS / VO 行数
- 镜头衔接行数
- 内部字段外露次数
- 结尾钩子是否在最后 2 行演出
- 目标集数覆盖率
- 题材模板错配次数
- 跨集重复/新鲜度分：相邻或同轮任意两集的场景骨架、动作链、对白句式、结尾钩子相似度
- C0 被改动次数
- C1 天然钩子/名场面丢失次数
- C4 编造动作/道具/狠话次数
- prompt_trace_analysis 的 suspected_failure_stage
- baseline_comparison_report 的 pipeline_vs_direct verdict
