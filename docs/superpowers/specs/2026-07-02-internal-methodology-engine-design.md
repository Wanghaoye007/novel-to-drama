# 内部方法论引擎设计

日期：2026-07-02

## 目标

建立一个平台内部使用的方法论沉淀与调用模块，让团队可以持续灌输短剧改编 SOP、拆剧笔记、标杆案例、平台规则和题材模板。用户不感知这个模块，也不需要选择方法论；用户只会感觉脚本更懂原文、更懂短剧、更少乱改。

这个模块的核心不是训练模型，而是把方法论变成可版本化、可检索、可注入 prompt、可进入质检的内部知识资产。

## 产品边界

用户侧不新增方法论入口。项目创建页、轮次页和交付页不展示“选择方法论”“选择策略包”之类控件。

内部侧新增一个 Methodology workspace，用于：

- 查看已导入的方法论文档。
- 查看系统抽取出的方法卡。
- 查看每张方法卡适用的题材、频道、阶段和触发条件。
- 查看方法卡当前状态、版本、来源和使用效果。
- 查看哪些 prompt 阶段或质量门禁正在使用该方法卡。

## 非目标

第一版不做：

- 不做用户可见的策略选择器。
- 不做自动微调模型。
- 不让新上传的方法论自动全局生效。
- 不做复杂多人审批流。
- 不做可视化知识图谱。
- 不做外部公开方法论市场。

## 核心原则

1. 用户无感知  
   方法论只作为后台能力参与生成和质检，不能增加用户操作成本。

2. 强原文轻改，弱原文重构  
   小说本身如果已有强冲突、强钩子、强反差、强人设和爆款情绪资产，就保护原文，只做视听化和节奏优化。不要为了“短剧化”把原著爆款属性改没。

3. 方法论先隔离再生效  
   新方法论导入后默认为 draft，只能被内部查看和测试。通过回归样本或人工启用后才能变为 active。

4. 方法论必须可追踪  
   每次生成使用了哪些方法卡、影响了哪些 prompt、触发了哪些质检规则，都要写入内部 runtime report。

5. 方法论不能压过原文  
   C0/C1 原文资产优先级高于任何方法论模板。模板只能增强、保护、视听化，不能把强原文套坏。

## 核心概念

### Methodology Source

原始方法论来源，可以是 Markdown、TXT、DOCX、拆剧笔记、标杆剧分析或人工录入内容。

字段：

```json
{
  "id": "method_source_xxx",
  "title": "短剧改编 SOP 总纲",
  "source_type": "sop",
  "raw_text": "",
  "origin_path": "",
  "status": "draft",
  "created_at": "",
  "updated_at": ""
}
```

### Method Card

从方法论来源中抽取出的最小可执行知识单元。方法卡不是摘要，而是后续 prompt 和 QA 能直接消费的规则。

字段：

```json
{
  "id": "method_card_xxx",
  "source_id": "method_source_xxx",
  "name": "强原文轻改规则",
  "category": "source_fidelity",
  "applies_to_channel": ["female", "male", "mixed"],
  "applies_to_genre": ["revenge", "identity", "billionaire", "male_counterattack"],
  "applies_to_stage": ["source_analysis", "episode_plan", "script_generation", "quality_gate"],
  "trigger": "原文已具备强冲突、强钩子、强反差或高情绪名场面",
  "generation_rule": "保留原文主动方、因果顺序、名场面和情绪曲线，只做视听化、压缩和镜头补强。",
  "quality_rule": "如果脚本删除 C1 名场面、改变 C0 主动方或把克制情绪改成歇斯底里，必须 needs_rewrite。",
  "positive_examples": [],
  "negative_examples": [],
  "status": "draft",
  "version": 1
}
```

### Source Strength Profile

每个项目在生成前自动判断原文短剧爆款属性强弱，用于决定改编强度。

字段：

```json
{
  "conflict_strength": 0,
  "hook_strength": 0,
  "character_tag_strength": 0,
  "emotion_asset_strength": 0,
  "signature_scene_strength": 0,
  "visualization_readiness": 0,
  "overall_level": "strong",
  "recommended_intensity": "light",
  "reasons": []
}
```

### Adaptation Intensity

系统内部的改编强度控制器。

| 强度 | 适用原文 | 允许动作 | 禁止动作 |
| --- | --- | --- | --- |
| light | 强爆款原文 | 视听化、镜头补强、短台词化、压缩低价值段落、增强衔接 | 改主动方、改动机、改名场面、编造道具、重排强情绪因果 |
| medium | 中等潜力原文 | 前置冲突、补断点、合并支线、加强信息差、补反应镜头 | 推翻主线、改人物核心欲望、替换原文关键场面 |
| heavy | 弱短剧原文 | 重构场景、补外部冲突、重组段落、建立强钩子 | 无来源地改变 C0 事实；新增内容必须写原因和锚点 |

## 系统流程

```text
内部导入方法论文档
  ↓
Methodology Ingest
  ↓
Method Card Extractor
  ↓
draft 方法卡
  ↓
内部查看 / 回归样本验证 / 手动启用
  ↓
active 方法卡
  ↓
生成任务开始
  ↓
Source Strength Classifier 判断原文强弱
  ↓
Method Retrieval 按频道、题材、阶段和强度检索方法卡
  ↓
Prompt Context Builder 注入相关方法卡
  ↓
Script Generation
  ↓
Quality Gate 使用方法卡质检
  ↓
runtime report 记录方法卡命中和效果
```

## 与现有 pipeline 的关系

当前主链路保持不变：

```text
source_analysis -> viral_asset_report -> episode_context
-> story_bible -> series_structure_plan -> episode_plan
-> script_batch -> quality_report -> state_writeback
```

新增模块挂在三个位置：

1. `source_analysis` 后  
   生成 `source_strength_profile`，判断原文是 strong / medium / weak。

2. 每个 prompt user context 构建前  
   `methodology_retriever` 根据项目题材、频道、阶段和强度返回相关 active 方法卡。

3. `quality_report` 和 `adaptation_quality_report` 前  
   `methodology_quality_gate` 把方法卡中的 quality_rule 转成检查项，尤其强化强原文保真。

## 强原文保护规则

当 `source_strength_profile.overall_level = strong` 且 `recommended_intensity = light` 时，所有阶段必须遵守：

- 不删除原文最强开场钩子，只能合规视听化。
- 不把原文的主动方改成另一方。
- 不把原文预谋决定改成临时起意。
- 不把原文克制、冰冷、决绝的人设改成歇斯底里。
- 不给主角新增原文没有的功利诉求。
- 不用编造动作、道具或狠话替代原文已有情绪资产。
- 不把台上/台下、明处/暗处、光鲜/狼狈这类强反差写平。

强原文的主要优化目标：

- 镜头更清楚。
- 台词更短。
- 情绪特写更足。
- 结尾断点更准。
- 内心戏更可拍。
- AI 后链路更容易执行。

## 方法论状态机

```text
draft -> active -> archived
   ↓
 rejected
```

- `draft`：可查看，可跑测试，不进入默认生产。
- `active`：可被后台检索和生产链路调用。
- `archived`：保留历史，不再调用。
- `rejected`：保留来源和失败原因，避免重复导入。

第一版可以由内部人员手动切换状态。后续再引入自动回归门槛。

## 内部页面

新增内部导航项：`内部方法论`。

页面包含：

1. 方法论来源列表  
   展示标题、来源类型、状态、卡片数、最近更新时间。

2. 方法卡列表  
   支持按频道、题材、阶段、状态、类别筛选。

3. 方法卡详情  
   展示触发条件、生成规则、质检规则、正例、反例、来源段落和版本。

4. 项目命中记录  
   从 runtime report 读取本项目用了哪些方法卡，以及是否触发修复。

这个页面只给内部运营和研发使用，不出现在普通用户流程中。

## 存储设计

第一版沿用现有 SQLite + file artifact 模式。

建议新增表：

- `methodology_sources`
- `methodology_cards`
- `methodology_runs`

建议新增 artifacts：

- `source_strength_profile.json`
- `methodology_context.json`
- `methodology_quality_report.json`

`methodology_context.json` 用于记录某一轮实际注入的 active 方法卡，便于复盘和 A/B。

## Prompt 集成

每个阶段只注入与自己相关的方法卡，避免上下文膨胀。

注入格式：

```text
内部方法论卡：
- 名称：
- 触发条件：
- 本阶段生成规则：
- 本阶段禁止事项：
- 本阶段质检规则：
```

注入数量第一版限制为每阶段最多 5 张卡。排序规则：

1. 强原文保护卡优先。
2. 当前阶段匹配优先。
3. 频道/题材匹配优先。
4. active 版本最新优先。

## 质检集成

方法卡的 `quality_rule` 进入两层质检：

1. 确定性检查  
   能本地判断的规则直接进入 `script_quality.py` 或 `adaptation_quality.py`。

2. LLM 软质检  
   需要语义判断的规则进入 quality prompt，并要求输出具体集数、脚本证据行、原文资产和修复建议。

强原文保护规则必须优先进入确定性或半确定性检查。不能只靠 LLM 自评。

## 成功指标

第一版完成后应能做到：

- 内部可以导入一份方法论文档并生成方法卡。
- 内部可以查看和启用/停用方法卡。
- 生成任务能产出 `source_strength_profile`。
- 强原文会自动进入 light adaptation。
- 弱原文会自动进入 medium/heavy adaptation。
- 轮次 runtime report 能看到命中的方法卡。
- 质量门禁能拦截“强原文被大改导致爆款属性丢失”的问题。

## 验收样例

样例 A：原文已有高刺激开场、公开压迫、身份悬念和强反差。系统应判为 strong/light。脚本必须保留原文强钩子和情绪顺序，只增强镜头与台词密度。

样例 B：原文设定好但铺垫慢、冲突后置。系统应判为 medium/medium。脚本可以前置冲突、合并低价值段落、补结尾断点。

样例 C：原文很短、冲突弱、人物标签不清。系统应判为 weak/heavy。脚本可以补外部冲突和信息差，但所有新增都要写入 adaptation_actions 和 source mapping。

## 实施切分

### P0：设计和数据骨架

- 写入本 spec。
- 定义 MethodologySource、MethodologyCard、SourceStrengthProfile schema。
- 添加本地 sample 方法论文档和方法卡 fixture。

### P1：Source Strength Classifier

- 在 pipeline 中新增 `source_strength_profile` artifact。
- prompt 和本地规则共同判断 strong / medium / weak。
- 将 recommended_intensity 写入后续 prompt context。

### P2：Methodology Ingest

- 支持从 Markdown/TXT 导入方法论来源。
- 抽取方法卡，默认 draft。
- 内部 API 支持列表、详情、状态切换。

### P3：Methodology Retrieval

- 按频道、题材、阶段、强度检索 active 方法卡。
- 每阶段最多注入 5 张。
- 写入 `methodology_context.json`。

### P4：Quality Gate 集成

- 将强原文保护卡接入 deterministic/LLM 质检。
- 强原文被大改时触发 needs_rewrite。
- 修复建议要求回到 C0/C1 原文资产，而不是继续编新爽点。

### P5：内部 UI

- 新增内部方法论页面。
- 展示来源、卡片、状态、命中记录。
- 不暴露给普通用户。

## 风险和控制

- 风险：方法论越灌越多，prompt 变重。  
  控制：每阶段最多注入 5 张卡，按匹配度排序。

- 风险：新方法论污染生产结果。  
  控制：默认 draft，active 才能进入生产。

- 风险：模板压过原文。  
  控制：source_strength_profile + adaptation_intensity 先决定改编力度，C0/C1 优先于方法卡。

- 风险：强原文被误判为弱原文。  
  控制：strong 判断只要多个维度达到高分就倾向 light；宁可少改，不先大改。

- 风险：内部人员看不懂方法卡效果。  
  控制：runtime report 记录方法卡命中、注入阶段、触发的质检问题和修复结果。
