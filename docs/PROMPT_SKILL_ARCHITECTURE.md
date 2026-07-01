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
- 每集必须输出可拍摄正片，而不是剧情摘要、看点说明或营销文案。

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
- `NOVEL_DRAMA_SCRIPT_EPISODE_FIRST=1` 的逐集生成路径，Kimi/Moonshot 默认优先使用；设为 `0` 可回退整批脚本生成做 A/B

推荐 A/B 指标：

- 单集可见字数
- action / dialogue / OS / VO 行数
- 镜头衔接行数
- 内部字段外露次数
- 结尾钩子是否在最后 2 行演出
- 目标集数覆盖率
- 题材模板错配次数
