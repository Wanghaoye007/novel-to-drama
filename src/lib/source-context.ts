export type NovelChapter = {
  index: number;
  title: string;
  text: string;
  summary: string;
  keywords: string[];
};

export type NovelContextOptions = {
  maxChars?: number;
  query?: string | null;
  targetEpisode?: number | null;
  targetEpisodeCount?: number | null;
  stateLedger?: string | null;
};

const DEFAULT_CONTEXT_CHARS = 12000;
const CHAPTER_HEADING =
  /^(?:#{1,6}\s*)?(第\s*[一二三四五六七八九十百千万\d]+\s*[章节回集][^\n]*|Chapter\s+\d+[^\n]*|EPISODE\s+\d+[^\n]*)$/gim;

const STOP_TERMS = new Set([
  "一个",
  "这个",
  "那个",
  "他们",
  "她们",
  "我们",
  "你们",
  "自己",
  "没有",
  "不是",
  "小说",
  "原文",
  "本集",
]);

function clampMaxChars(value: number | undefined): number {
  if (!Number.isFinite(value ?? Number.NaN)) return DEFAULT_CONTEXT_CHARS;
  return Math.max(800, Math.floor(value ?? DEFAULT_CONTEXT_CHARS));
}

function compactWhitespace(value: string): string {
  return value.replace(/[ \t\r]+/g, " ").replace(/\n{3,}/g, "\n\n").trim();
}

function excerpt(value: string, maxChars: number): string {
  const compact = compactWhitespace(value);
  if (compact.length <= maxChars) return compact;
  const headSize = Math.floor(maxChars * 0.55);
  const tailSize = Math.max(120, maxChars - headSize - 8);
  return `${compact.slice(0, headSize)}\n...\n${compact.slice(-tailSize)}`;
}

export function extractKeywords(value: string, limit = 24): string[] {
  const counts = new Map<string, number>();
  for (const match of value.matchAll(/[\u4e00-\u9fff]{2,8}|[a-zA-Z][a-zA-Z0-9_-]{2,}/g)) {
    const token = match[0].toLowerCase();
    if (STOP_TERMS.has(token)) continue;
    counts.set(token, (counts.get(token) ?? 0) + 1);
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || b[0].length - a[0].length)
    .slice(0, limit)
    .map(([token]) => token);
}

function summarizeChapter(text: string): string {
  const sentences = compactWhitespace(text)
    .split(/(?<=[。！？!?；;])\s*/)
    .map((item) => item.trim())
    .filter(Boolean);
  if (sentences.length === 0) return excerpt(text, 180);
  return excerpt([sentences[0], sentences.at(-1)].filter(Boolean).join(" "), 220);
}

function chunkBySize(text: string, chunkSize = 4500): NovelChapter[] {
  const chapters: NovelChapter[] = [];
  for (let start = 0; start < text.length; start += chunkSize) {
    const body = text.slice(start, start + chunkSize);
    const index = chapters.length + 1;
    chapters.push({
      index,
      title: `自动分块 ${index}`,
      text: body,
      summary: summarizeChapter(body),
      keywords: extractKeywords(body),
    });
  }
  return chapters;
}

export function splitNovelIntoChapters(novelText: string): NovelChapter[] {
  const source = compactWhitespace(novelText);
  if (!source) return [];

  const matches = [...source.matchAll(CHAPTER_HEADING)];
  if (matches.length < 2) return chunkBySize(source);

  const chapters: NovelChapter[] = [];
  for (let index = 0; index < matches.length; index += 1) {
    const match = matches[index];
    const next = matches[index + 1];
    const start = match.index ?? 0;
    const end = next?.index ?? source.length;
    const text = source.slice(start, end).trim();
    chapters.push({
      index: chapters.length + 1,
      title: match[1].trim(),
      text,
      summary: summarizeChapter(text),
      keywords: extractKeywords(text),
    });
  }
  return chapters;
}

function scoreChapter(
  chapter: NovelChapter,
  terms: string[],
  mappedChapterIndex: number | null
): number {
  const haystack = `${chapter.title}\n${chapter.keywords.join(" ")}\n${chapter.text}`;
  const termScore = terms.reduce(
    (score, term) => score + (haystack.includes(term) ? Math.max(2, term.length) : 0),
    0
  );
  const mappingScore =
    mappedChapterIndex == null
      ? 0
      : Math.max(0, 8 - Math.abs(chapter.index - mappedChapterIndex) * 2);
  return termScore + mappingScore;
}

function mappedChapterForEpisode(
  chapterCount: number,
  targetEpisode?: number | null,
  targetEpisodeCount?: number | null
): number | null {
  if (!targetEpisode || !targetEpisodeCount || chapterCount === 0) return null;
  const ratio = Math.max(0, Math.min(1, (targetEpisode - 1) / targetEpisodeCount));
  return Math.min(chapterCount, Math.max(1, Math.floor(ratio * chapterCount) + 1));
}

export function buildNovelContext(
  novelText: string,
  options: NovelContextOptions = {}
): string {
  const maxChars = clampMaxChars(options.maxChars);
  const chapters = splitNovelIntoChapters(novelText);
  if (chapters.length === 0) return "";

  const query = compactWhitespace(
    [options.query, options.stateLedger].filter(Boolean).join("\n")
  );
  const terms = extractKeywords(query, 32);
  const mappedChapterIndex = mappedChapterForEpisode(
    chapters.length,
    options.targetEpisode,
    options.targetEpisodeCount
  );
  const scored = chapters
    .map((chapter) => ({
      chapter,
      score: scoreChapter(chapter, terms, mappedChapterIndex),
    }))
    .sort((a, b) => b.score - a.score || a.chapter.index - b.chapter.index);
  const selected = scored
    .slice(0, Math.min(4, Math.max(2, Math.ceil(maxChars / 3500))))
    .map((item) => item.chapter)
    .sort((a, b) => a.index - b.index);

  const summaryLines = chapters.map(
    (chapter) =>
      `- C${chapter.index} ${chapter.title}: ${excerpt(chapter.summary, 120)}`
  );
  const selectedBudget = Math.max(300, Math.floor(maxChars / selected.length) - 120);
  const selectedBlocks = selected.map((chapter) =>
    [
      `## C${chapter.index} ${chapter.title}`,
      `关键词：${chapter.keywords.slice(0, 8).join("、") || "无"}`,
      excerpt(chapter.text, selectedBudget),
    ].join("\n")
  );
  return excerpt(
    [
      "【章节摘要索引】",
      ...summaryLines,
      options.stateLedger ? `\n【状态 Ledger】\n${options.stateLedger}` : "",
      "\n【检索命中的原文片段】",
      ...selectedBlocks,
    ]
      .filter(Boolean)
      .join("\n"),
    maxChars
  );
}
