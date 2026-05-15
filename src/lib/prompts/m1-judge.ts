export const M1_JUDGE_PROMPT = `你是短剧改编专家。对给定的小说文本做以下判断，输出 JSON：

1. completeness（完整度）：
   - "complete" 完结作品
   - "ongoing" 连载未完
   - "outline" 大纲或碎片
   - "unknown" 无法判断

2. genre（体裁）：
   - "webnovel" 网络小说原文
   - "adapted-script" 已改编过的剧本
   - "outline" 大纲或人设文档
   - "unknown" 无法判断

3. channelHint（频道粗判）：
   - "male" 男频（信息差打脸/降维碾压/主角主动出击）
   - "female" 女频（共情虐心/反派被惩/护场）
   - "unknown" 不确定

4. anomalies（异常列表，可空数组）：广告位、章节缺失、乱码等

输出格式（严格 JSON，无任何额外文字）：
{
  "completeness": "...",
  "genre": "...",
  "channelHint": "...",
  "anomalies": []
}

小说文本（前 6000 字）：
<<<NOVEL>>>`;

export function buildM1JudgePrompt(novelText: string): string {
  const excerpt = novelText.slice(0, 6000);
  return M1_JUDGE_PROMPT.replace("<<<NOVEL>>>", excerpt);
}
