import mammoth from "mammoth";
import { callLLM, LLMCallError } from "./anthropic";
import { buildM1JudgePrompt } from "./prompts/m1-judge";

export interface NovelMeta {
  charCount: number;
  lineCount: number;
  chapterCount: number;
  completeness: "complete" | "ongoing" | "outline" | "unknown";
  genre: "webnovel" | "adapted-script" | "outline" | "unknown";
  channelHint: "male" | "female" | "unknown";
  anomalies: string[];
}

export async function parseUpload(
  filename: string,
  buffer: Buffer
): Promise<string> {
  const ext = filename.toLowerCase().split(".").pop();
  if (ext === "txt") {
    return buffer.toString("utf-8");
  }
  if (ext === "docx") {
    const result = await mammoth.extractRawText({ buffer });
    return result.value;
  }
  throw new Error(`Unsupported file type: .${ext}`);
}

export function extractRuleBasedMeta(
  novelText: string
): Pick<NovelMeta, "charCount" | "lineCount" | "chapterCount"> {
  const charCount = novelText.length;
  const lineCount = novelText.split("\n").length;
  const chapterMatches = novelText.match(
    /第[\d零一二三四五六七八九十百千]+[章回节]/g
  );
  const chapterCount = chapterMatches?.length ?? 0;
  return { charCount, lineCount, chapterCount };
}

export async function judgeNovel(
  novelText: string
): Promise<
  Pick<NovelMeta, "completeness" | "genre" | "channelHint" | "anomalies">
> {
  if (!process.env.ANTHROPIC_API_KEY) {
    return {
      completeness: "unknown",
      genre: "unknown",
      channelHint: "unknown",
      anomalies: ["llm_judge_skipped"],
    };
  }

  try {
    const raw = await callLLM({
      model: "sonnet",
      user: buildM1JudgePrompt(novelText),
      maxTokens: 512,
      temperature: 0.2,
    });
    const jsonMatch = raw.match(/\{[\s\S]*\}/);
    if (!jsonMatch) throw new Error("no JSON in response");
    return JSON.parse(jsonMatch[0]);
  } catch (e) {
    if (e instanceof LLMCallError) {
      return {
        completeness: "unknown",
        genre: "unknown",
        channelHint: "unknown",
        anomalies: ["llm_judge_failed"],
      };
    }
    throw e;
  }
}

export async function normalizeNovel(
  filename: string,
  buffer: Buffer
): Promise<{ text: string; meta: NovelMeta }> {
  const text = await parseUpload(filename, buffer);
  const ruleMeta = extractRuleBasedMeta(text);
  const llmMeta = await judgeNovel(text);
  return {
    text,
    meta: { ...ruleMeta, ...llmMeta },
  };
}
