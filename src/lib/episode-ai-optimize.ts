import { normalizeLlmModel } from "./llm-model-options";

type TextProject = {
  name: string;
  novelText: string;
};

type TextEpisode = {
  epNum: number;
  scriptTxt: string | null;
};

type TextBible = {
  charactersMd?: string | null;
  episodePlanMd?: string | null;
  sixAssetsJson?: string | null;
  prevRoundSummaryJson?: string | null;
};

type TextRound = {
  roundNum: number;
  summaryJson?: string | null;
};

export type EpisodeOptimizationPromptInput = {
  project: TextProject;
  episode: TextEpisode;
  bible?: TextBible | null;
  round?: TextRound | null;
  episodes?: TextEpisode[];
  instruction?: string | null;
};

type EpisodeOptimizationInput = EpisodeOptimizationPromptInput & {
  llmModel?: string | null;
};

const MAX_SOURCE_CHARS = 12_000;
const MAX_SCRIPT_CHARS = 6_000;
const MAX_CONTEXT_CHARS = 2_400;

function compactText(value: string | null | undefined, maxChars: number): string {
  const text = (value ?? "").trim();
  if (text.length <= maxChars) return text;
  return `${text.slice(0, Math.floor(maxChars * 0.65))}\n...\n${text.slice(-Math.floor(maxChars * 0.35))}`;
}

function previousAndNextEpisodes(
  episodes: TextEpisode[] | undefined,
  epNum: number
): { previous: TextEpisode | null; next: TextEpisode | null } {
  const ordered = [...(episodes ?? [])].sort((a, b) => a.epNum - b.epNum);
  return {
    previous: [...ordered].reverse().find((item) => item.epNum < epNum) ?? null,
    next: ordered.find((item) => item.epNum > epNum) ?? null,
  };
}

export function buildEpisodeOptimizationPrompt(
  input: EpisodeOptimizationPromptInput
): string {
  const { previous, next } = previousAndNextEpisodes(
    input.episodes,
    input.episode.epNum
  );
  const instruction =
    input.instruction?.trim() ||
    "优化当前集的戏剧张力、镜头细节、情绪递进和口语化台词；不改变已成立的人物动机和前后剧情。";

  return [
    `项目：${input.project.name}`,
    `任务：只优化第 ${input.episode.epNum} 集。`,
    "",
    "硬约束：",
    "1. 当前集旧稿是唯一文本基准，只能在旧稿基础上定向优化，不得改成另一版故事。",
    "2. 只优化当前集，不生成其他集，不改动前一集结尾和后一集开头已经成立的事实。",
    "3. 根据修改意见修复戏剧问题：人物动机、情绪递进、对白口吻、镜头呈现、爽点/虐点落点。",
    "4. 保留当前剧本的集标题和可拍摄脚本格式；不要输出解释、评分、JSON 以外内容。",
    "5. 如需增强镜头，只补充可拍的动作、表情、道具、视线、剪辑衔接；不要堆砌空泛景别术语。",
    "",
    `修改意见：${instruction}`,
    "",
    "Story Bible / 系统资产：",
    `人物小传：\n${compactText(input.bible?.charactersMd, MAX_CONTEXT_CHARS) || "无"}`,
    `分集规划：\n${compactText(input.bible?.episodePlanMd, MAX_CONTEXT_CHARS) || "无"}`,
    `核心资产：\n${compactText(input.bible?.sixAssetsJson, MAX_CONTEXT_CHARS) || "无"}`,
    `前情台账：\n${compactText(input.bible?.prevRoundSummaryJson, MAX_CONTEXT_CHARS) || "无"}`,
    `当前轮摘要：\n${compactText(input.round?.summaryJson, MAX_CONTEXT_CHARS) || "无"}`,
    "",
    "前后集承接：",
    `上一集：\n${compactText(previous?.scriptTxt, MAX_CONTEXT_CHARS) || "无"}`,
    `下一集：\n${compactText(next?.scriptTxt, MAX_CONTEXT_CHARS) || "无"}`,
    "",
    "原文参考：",
    compactText(input.project.novelText, MAX_SOURCE_CHARS) || "无",
    "",
    "当前集旧稿：",
    compactText(input.episode.scriptTxt, MAX_SCRIPT_CHARS) || "无",
    "",
    '输出 JSON：{"scriptText":"优化后的完整第 N 集脚本"}',
  ].join("\n");
}

function extractJsonObject(raw: string): unknown {
  const text = raw.trim().replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/i, "");
  try {
    return JSON.parse(text);
  } catch {
    const start = text.indexOf("{");
    const end = text.lastIndexOf("}");
    if (start === -1 || end <= start) throw new Error("模型没有返回 JSON 对象");
    return JSON.parse(text.slice(start, end + 1));
  }
}

export function parseEpisodeOptimizationResponse(raw: string): string {
  const parsed = extractJsonObject(raw) as { scriptText?: unknown };
  if (typeof parsed.scriptText !== "string" || !parsed.scriptText.trim()) {
    throw new Error("模型返回缺少 scriptText");
  }
  return parsed.scriptText.trim();
}

export async function optimizeEpisodeScript(
  input: EpisodeOptimizationInput
): Promise<{ scriptText: string; llmModel: string }> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    throw new Error("OPENAI_API_KEY is not set");
  }

  const llmModel = normalizeLlmModel(input.llmModel, process.env.OPENAI_MODEL);
  const baseUrl = (process.env.OPENAI_BASE_URL ?? "https://api.openai.com/v1").replace(
    /\/$/,
    ""
  );
  const res = await fetch(`${baseUrl}/chat/completions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: llmModel,
      messages: [
        {
          role: "system",
          content:
            "你是小说改短剧的定向改稿编辑。你的目标不是重写，而是在当前集旧稿上修出更强戏剧张力、更清晰镜头、更自然台词和更顺的前后承接。",
        },
        {
          role: "user",
          content: buildEpisodeOptimizationPrompt(input),
        },
      ],
      temperature: 0.35,
      response_format: { type: "json_object" },
    }),
  });

  const raw = await res.text();
  if (!res.ok) {
    throw new Error(`LLM optimize failed (${res.status}): ${raw.slice(0, 1000)}`);
  }
  const payload = JSON.parse(raw) as {
    choices?: Array<{ message?: { content?: string | null } }>;
  };
  const content = payload.choices?.[0]?.message?.content;
  if (!content) throw new Error("LLM optimize returned empty content");
  return {
    scriptText: parseEpisodeOptimizationResponse(content),
    llmModel,
  };
}
