import { callLLM } from "./anthropic";
import {
  M2_CHANNEL_CONFIRM_PROMPT,
  M2_SIX_ASSETS_PROMPT,
  M2_CHARACTERS_PROMPT,
  M2_EPISODE_PLAN_PROMPT,
  fill,
} from "./prompts/m2-bible";
import type { NovelMeta } from "./m1-normalize";

export interface SixAssets {
  protagonist_motivation: string;
  iconic_scenes: { name: string; summary: string; cold_open_candidate: boolean }[];
  key_lines: string[];
  emotion_curve: string;
  relationships: { from: string; to: string; type: string; note?: string }[];
  premise: string;
}

export interface BibleDraft {
  channel: "male" | "female";
  sixAssets: SixAssets;
  charactersMd: string;
  episodePlanMd: string;
}

function extractJson<T>(raw: string): T {
  const match = raw.match(/\{[\s\S]*\}/);
  if (!match) throw new Error("no JSON in response");
  return JSON.parse(match[0]) as T;
}

export async function generateBible(
  novelText: string,
  meta: NovelMeta,
  targetEpisodeCount: number
): Promise<BibleDraft> {
  const novelExcerpt = novelText.slice(0, 15000);

  // 1. Channel confirm
  const channelRaw = await callLLM({
    model: "sonnet",
    user: fill(M2_CHANNEL_CONFIRM_PROMPT, {
      HINT: meta.channelHint,
      NOVEL: novelExcerpt,
    }),
    maxTokens: 256,
    temperature: 0.2,
  });
  const { channel } = extractJson<{ channel: "male" | "female" }>(channelRaw);

  // 2. Six assets
  const sixAssetsRaw = await callLLM({
    model: "sonnet",
    user: fill(M2_SIX_ASSETS_PROMPT, {
      CHANNEL: channel,
      NOVEL: novelExcerpt,
    }),
    maxTokens: 2048,
    temperature: 0.4,
  });
  const sixAssets = extractJson<SixAssets>(sixAssetsRaw);

  // 3. Characters
  const femaleExtra =
    channel === "female"
      ? "\n【女频额外要求】每个会背叛/劝忍的角色，必须写明：为什么他的背叛特别痛——具体的关系背景。"
      : "";
  const charactersMd = await callLLM({
    model: "sonnet",
    user: fill(M2_CHARACTERS_PROMPT, {
      CHANNEL: channel,
      SIX_ASSETS: JSON.stringify(sixAssets, null, 2),
      NOVEL: novelExcerpt,
      FEMALE_EXTRA: femaleExtra,
    }),
    maxTokens: 4096,
    temperature: 0.5,
  });

  // 4. Episode plan
  const episodePlanMd = await callLLM({
    model: "sonnet",
    user: fill(M2_EPISODE_PLAN_PROMPT, {
      TARGET_EP_COUNT: String(targetEpisodeCount),
      CHANNEL: channel,
      SIX_ASSETS: JSON.stringify(sixAssets, null, 2),
      NOVEL: novelExcerpt,
    }),
    maxTokens: 6000,
    temperature: 0.5,
  });

  return { channel, sixAssets, charactersMd, episodePlanMd };
}
