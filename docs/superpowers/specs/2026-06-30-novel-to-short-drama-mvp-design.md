# 小说转爆款短剧脚本 MVP 设计

日期：2026-06-30

## 目标

做一个按轮次工作的小说转短剧脚本引擎：

> 输入小说原文和可选上下文，系统自动识别原文对应短剧集数与剧情阶段，内部维护 Story Bible 和 Story State，每轮输出 1-3 集可用短剧脚本，并自动回写下一轮上下文。

MVP 的核心不是开放平台，也不是视频生成，而是验证一件事：

> 系统能否稳定把小说片段改成有强 Hook、有独立冲突、有信息差、有 cliffhanger、可拍摄的短剧脚本。

## 默认产品假设

- 初始目标：中文小说转中文竖屏短剧脚本。
- 初始风格：抖音女频/男频通用短剧逻辑，强冲突、快节奏、短台词、每集留钩。
- 初始输入：用户粘贴或上传小说文本。
- 初始输出：当前轮次对应的 1-3 集完整脚本，以及下一轮上下文。
- 用户不需要确认 Story Bible。
- 用户不需要选择改编方向。
- 用户不需要理解内部 JSON。

## 非目标

MVP 不做这些：

- 不做完整 SaaS 平台。
- 不做账号、支付、团队协作。
- 不做多语言本地化。
- 不做 TikTok / JP / SEA 市场迁移。
- 不做 AI 视频生成。
- 不做封面图生成。
- 不做投放素材包。
- 不一次性生成 50 集完整脚本。
- 不让用户审核 Story Bible。
- 不让用户手动选择模板。
- 不做复杂自然语言编辑器。

这些都可以是后续版本，但不进入第一版。

## 用户流程

```text
用户输入小说原文
  ↓
系统解析原文
  ↓
系统自动识别对应短剧集数和上下文
  ↓
系统生成内部 Story Bible
  ↓
系统生成本轮 1-3 集短剧脚本
  ↓
系统质检脚本
  ↓
系统回写 Story State
  ↓
用户看到脚本和简短质检结论
```

用户默认只看到：

1. 本轮对应集数，例如 `EP01-EP03`。
2. 每集完整脚本。
3. 简短质量结论：`可用`、`需重写`、`上下文冲突`。
4. 下一轮生成入口。

## 核心轮次

### Round 1: Source Parser

职责：

- 识别人物、事件、地点、时间、关键道具。
- 提取冲突、羞辱、误会、反转、爽点、虐点。
- 找出可视频化场面。
- 删除或压缩低冲突叙事。

输出内部结构：`source_analysis`

关键字段：

```json
{
  "characters": [],
  "events": [],
  "conflicts": [],
  "visual_moments": [],
  "low_value_passages": [],
  "candidate_hooks": []
}
```

### Round 2: Episode Context Resolver

这是 MVP 的核心。

职责：

- 判断当前原文适合改成第几集到第几集。
- 判断当前剧情阶段。
- 判断哪些上下文必须承接。
- 判断哪些秘密不能提前释放。
- 判断哪些事件要保留、压缩、提前或后置。

输出内部结构：`episode_context`

关键字段：

```json
{
  "target_episode_range": "EP01-EP03",
  "story_stage": "opening_pressure",
  "source_to_episode_mapping": [],
  "must_carry_context": [],
  "forbidden_reveals": [],
  "adaptation_actions": []
}
```

`story_stage` 使用固定枚举：

- `opening_pressure`
- `identity_hook`
- `first_counterattack`
- `misunderstanding_escalation`
- `midpoint_reversal`
- `truth_near_reveal`
- `public_reveal`
- `final_reckoning`

### Round 3: Internal Bible Builder

职责：

- 自动生成全剧内部 Story Bible。
- 固定主线、角色、关系、语言风格、世界边界。
- 记录禁止自作主张新增的重大设定。

用户默认不看、不确认、不编辑。

输出内部结构：`story_bible`

关键字段：

```json
{
  "genre": "",
  "mainline": "",
  "characters": [],
  "relationships": [],
  "speech_styles": {},
  "immutable_facts": [],
  "forbidden_changes": []
}
```

### Round 4: Script Batch Generator

职责：

- 每轮生成 1-3 集完整短剧脚本。
- 每集必须有前 3 秒 Hook。
- 每集必须有独立冲突。
- 每集必须有主情绪。
- 每集结尾必须有 cliffhanger。
- 台词必须短、狠、口语化。
- 动作必须可拍摄。

单集输出结构：

```json
{
  "episode": 1,
  "title": "",
  "hook_3s": "",
  "main_emotion": "",
  "watch_reason": "",
  "scenes": [],
  "cliffhanger": "",
  "state_update": {}
}
```

脚本渲染格式：

```text
第1集 [标题]

1-1 日/夜 内/外 地点
人物：角色A、角色B

△可拍摄动作。
角色名（情绪）：短台词。
角色名OS：内心独白。
△OS 后必须跟物理动作或明确决定。
```

### Round 5: Continuity + Boom Check

职责：

- 检查是否违背 Story Bible。
- 检查人物是否知道了不该知道的信息。
- 检查是否提前泄露秘密。
- 检查是否重复上一轮事件。
- 检查前 3 秒 Hook 是否足够强。
- 检查本集是否有独立冲突。
- 检查 cliffhanger 是否有效。
- 检查台词是否太小说化。
- 检查是否可视频化。

质检输出只给用户简短结论，完整报告内部保存。

```json
{
  "status": "usable",
  "scores": {
    "hook": 8,
    "conflict": 9,
    "cliffhanger": 8,
    "continuity": 10,
    "video_feasibility": 8
  },
  "blocking_issues": [],
  "rewrite_instruction": ""
}
```

如果 `status` 是 `needs_rewrite`，系统自动重写一次。

### Round 6: State Writeback

职责：

- 写回本轮发生的事件。
- 更新人物关系。
- 更新谁知道什么。
- 更新伏笔状态。
- 更新道具状态。
- 写入下一轮接续点。

输出结构：`next_round_context`

```json
{
  "summary": "",
  "current_episode": 3,
  "open_hooks": [],
  "forbidden_reveals": [],
  "character_knowledge": {},
  "relationship_changes": [],
  "prop_states": [],
  "foreshadowing_ledger": []
}
```

## 数据边界

MVP 不需要一开始建复杂数据库。第一版可以用项目级 JSON 文件或数据库 JSONB 存储中间态。

最少需要保存：

- `source_analysis`
- `episode_context`
- `story_bible`
- `episode_scripts`
- `quality_reports`
- `story_state_snapshots`

必须支持版本号：

```json
{
  "project_id": "",
  "round_number": 1,
  "state_version": 1,
  "created_at": ""
}
```

## 失败处理

必须显式处理这些失败：

- 输入文本为空：提示用户补充小说原文。
- 输入文本太短：仍可生成，但标记上下文不足。
- JSON 输出非法：自动修复或重试。
- 缺少必填字段：自动补齐或重试。
- 无法判断对应集数：默认从下一集继续，并在内部标记低置信度。
- 质检失败：自动重写一次。
- 第二次质检仍失败：返回脚本草稿，同时标记 `需人工检查`。

## 验证标准

MVP 做完后，用 5 段不同小说片段测试：

1. 女频豪门羞辱。
2. 真假千金。
3. 追妻火葬场。
4. 男频逆袭打脸。
5. 穿越/重生开局。

每段至少跑 2 轮。

通过标准：

- 系统能稳定识别目标集数范围。
- 每集都有前 3 秒 Hook。
- 每集都有独立冲突。
- 每集结尾有 cliffhanger。
- 角色知识状态不乱。
- 没有提前揭露核心秘密。
- 脚本可按短剧格式直接阅读和分配制作。

## 后续版本

V1 之后再考虑：

- 展示并编辑 Story Bible。
- 用户自然语言修改。
- 影响范围分析。
- 50 集大纲。
- 分镜列表。
- 封面标题。
- TikTok 英文本地化。
- 视频 Prompt。
- 多项目管理。
- SaaS 账号和计费。

## 当前推荐

先实现一个内部 Web/CLI 原型，而不是完整平台。

第一版交付物：

```text
输入：小说原文 + 可选 next_round_context
输出：本轮 1-3 集短剧脚本 + 简短质检结论 + next_round_context
```

这就是 MVP。
