import mammoth from "mammoth";

export interface NovelUploadMeta {
  charCount: number;
  lineCount: number;
  chapterCount: number;
}

export class NovelUploadLimitError extends Error {
  status = 413;
}

function positiveEnvLimit(name: string, fallback: number): number {
  const value = Number.parseInt(process.env[name] ?? "", 10);
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

export function assertUploadSizeLimit(size: number): void {
  const limit = positiveEnvLimit("NOVEL_DRAMA_MAX_UPLOAD_BYTES", 20 * 1024 * 1024);
  if (!Number.isFinite(size) || size < 0 || size > limit) {
    throw new NovelUploadLimitError(`upload exceeds ${limit} bytes`);
  }
}

export function assertNovelTextLimit(text: string): void {
  const limit = positiveEnvLimit("NOVEL_DRAMA_MAX_NOVEL_CHARS", 2_000_000);
  if (text.length > limit) {
    throw new NovelUploadLimitError(`novel exceeds ${limit} characters`);
  }
}

export async function parseUpload(
  filename: string,
  buffer: Buffer
): Promise<string> {
  assertUploadSizeLimit(buffer.length);
  const ext = filename.toLowerCase().split(".").pop();
  if (ext === "txt") {
    const text = buffer.toString("utf-8");
    assertNovelTextLimit(text);
    return text;
  }
  if (ext === "docx") {
    const result = await mammoth.extractRawText({ buffer });
    assertNovelTextLimit(result.value);
    return result.value;
  }
  throw new Error(`Unsupported file type: .${ext}`);
}

export function extractRuleBasedMeta(novelText: string): NovelUploadMeta {
  const chapterMatches = novelText.match(
    /第[\d零一二三四五六七八九十百千]+[章回节]/g
  );
  return {
    charCount: novelText.length,
    lineCount: novelText.split("\n").length,
    chapterCount: chapterMatches?.length ?? 0,
  };
}
