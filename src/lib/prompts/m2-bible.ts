export const M2_CHANNEL_CONFIRM_PROMPT = `你是短剧改编专家。基于以下小说原文和初步判断，给出最终的频道结论。

【初步判断】
{{HINT}}

【小说原文（章节摘要与检索片段）】
{{NOVEL}}

输出严格 JSON：
{
  "channel": "male" 或 "female",
  "reason": "一句话依据"
}`;

export const M2_SIX_ASSETS_PROMPT = `你是短剧改编专家。从以下小说中抽取「六大资产」——改编时必须守住不能改的核心。

频道：{{CHANNEL}}

【小说原文】
{{NOVEL}}

输出严格 JSON：
{
  "protagonist_motivation": "主角核心动机，1-2 句",
  "iconic_scenes": [
    { "name": "场面名", "summary": "1-2 句", "cold_open_candidate": true }
  ],
  "key_lines": ["金句1", "金句2", "..."],
  "emotion_curve": "全季情绪曲线，5-10 个节点串成一句话",
  "relationships": [
    { "from": "角色A", "to": "角色B", "type": "爱/恨/帮/敌/亲", "note": "可选" }
  ],
  "premise": "故事前提/世界观设定，1-2 句"
}`;

export const M2_CHARACTERS_PROMPT = `你是短剧改编专家。为这部短剧的所有主要角色（主角+主要配角，5-8 个）写人物小传。

频道：{{CHANNEL}}
六大资产：
{{SIX_ASSETS}}

【小说原文】
{{NOVEL}}

每个角色按以下 Markdown 模板输出，多个角色用 \n\n--- \n\n 分隔：

### 【角色名】
- 年龄/外貌/标志性特征：
- 身份：主角/反派/配角
- 性格：表面 X，实则 Y
- 经历 → 导致现在的性格/动机：
- 与主角关系 + 关键节点：
- 人物弧光：从 X 变成 Y
- 台词风格 + 2 个示例台词：
- 在剧中功能：压/装/打/爆/拉
{{FEMALE_EXTRA}}

直接输出，不加额外说明。`;

export const M2_EPISODE_PLAN_PROMPT = `你是短剧改编专家。设计本剧的轮次切分和分集大纲。

约束：
- 每轮固定 5 集
- 目标总集数：{{TARGET_EP_COUNT}}
- 频道：{{CHANNEL}}

参考信息：
六大资产：
{{SIX_ASSETS}}

【小说原文】
{{NOVEL}}

输出 Markdown，结构：

## 第 1 轮（E01-E05）
本轮情绪曲线：xxx
本轮钩子方向：xxx

### E01
- 主线事件：
- 情绪标签：
- 钩子方向：

### E02
...（同 E01 结构）

...

## 第 2 轮（E06-E10）
...

直到覆盖所有 {{TARGET_EP_COUNT}} 集。`;

export function fill(template: string, vars: Record<string, string>): string {
  let out = template;
  for (const [k, v] of Object.entries(vars)) {
    out = out.replaceAll(`{{${k}}}`, v);
  }
  return out;
}
