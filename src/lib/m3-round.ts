import { callLLM } from "./anthropic";
import {
  M3_ADAPT_PROMPT,
  M3_EP_SUMMARY_PROMPT,
  M3_ROUND_SUMMARY_PROMPT,
  FEMALE_RULES,
  MALE_RULES,
} from "./prompts/m3-adapt";
import { fill } from "./prompts/m2-bible";

export interface EpSummary {
  character_state_changes: string;
  unresolved_threads: string[];
  hook_direction: string;
}

export interface RoundSummary {
  round_arc: string;
  character_states: string;
  open_threads: string[];
  next_round_hook: string;
}

export interface AdaptEpisodeInput {
  channel: "male" | "female";
  epNum: number;
  characters: string;
  sixAssets: string;
  epPlan: string;
  novelExcerpt: string;
  prevRoundSummary: RoundSummary | null;
  prevEpSummariesInRound: EpSummary[];
}

function buildPrevContext(
  prevRound: RoundSummary | null,
  prevEps: EpSummary[]
): string {
  const parts: string[] = [];
  if (prevRound) {
    parts.push("【上一轮摘要】");
    parts.push(`轮整体：${prevRound.round_arc}`);
    parts.push(`人物状态：${prevRound.character_states}`);
    parts.push(`跨轮伏笔：${prevRound.open_threads.join("；")}`);
    parts.push(`本轮承接：${prevRound.next_round_hook}`);
  }
  if (prevEps.length > 0) {
    parts.push("\n【本轮已跑过的集】");
    prevEps.forEach((s, i) => {
      parts.push(
        `第${i + 1}集：${s.character_state_changes}；未解：${s.unresolved_threads.join("、")}；钩子：${s.hook_direction}`
      );
    });
  }
  if (parts.length === 0) return "（无前情，本集为本剧第 1 集）";
  return parts.join("\n");
}

export async function adaptEpisode(input: AdaptEpisodeInput): Promise<string> {
  const channelRules = input.channel === "female" ? FEMALE_RULES : MALE_RULES;
  const prevContext = buildPrevContext(
    input.prevRoundSummary,
    input.prevEpSummariesInRound
  );
  const prompt = fill(M3_ADAPT_PROMPT, {
    CHANNEL: input.channel === "female" ? "女频" : "男频",
    EP_NUM: String(input.epNum),
    CHARACTERS: input.characters,
    SIX_ASSETS: input.sixAssets,
    PREV_CONTEXT: prevContext,
    EP_PLAN: input.epPlan,
    NOVEL_EXCERPT: input.novelExcerpt.slice(0, 8000),
    CHANNEL_RULES: channelRules,
  });

  return callLLM({
    model: "opus",
    user: prompt,
    maxTokens: 4096,
    temperature: 0.7,
  });
}

export async function extractEpSummary(script: string): Promise<EpSummary> {
  const raw = await callLLM({
    model: "haiku",
    user: fill(M3_EP_SUMMARY_PROMPT, { SCRIPT: script }),
    maxTokens: 512,
    temperature: 0.3,
  });
  const match = raw.match(/\{[\s\S]*\}/);
  if (!match) throw new Error("no JSON in ep summary");
  return JSON.parse(match[0]);
}

export async function extractRoundSummary(
  epSummaries: EpSummary[]
): Promise<RoundSummary> {
  const raw = await callLLM({
    model: "haiku",
    user: fill(M3_ROUND_SUMMARY_PROMPT, {
      EP_SUMMARIES: JSON.stringify(epSummaries, null, 2),
    }),
    maxTokens: 1024,
    temperature: 0.3,
  });
  const match = raw.match(/\{[\s\S]*\}/);
  if (!match) throw new Error("no JSON in round summary");
  return JSON.parse(match[0]);
}

export function extractEpisodePlan(planMd: string, epNum: number): string {
  // Parse out "### E0X" section from full plan
  const regex = new RegExp(
    `###\\s*E${String(epNum).padStart(2, "0")}[\\s\\S]*?(?=###\\s*E\\d|##\\s|$)`,
    ""
  );
  const match = planMd.match(regex);
  return match ? match[0].trim() : `（第 ${epNum} 集在大纲中未找到，请按通用流程改编）`;
}
