import mammoth from "mammoth";

export interface NovelUploadMeta {
  charCount: number;
  lineCount: number;
  chapterCount: number;
}

export async function parseUpload(
  filename: string,
  buffer: Buffer
): Promise<string> {
  const ext = filename.toLowerCase().split(".").pop();
  if (ext === "txt") return buffer.toString("utf-8");
  if (ext === "docx") {
    const result = await mammoth.extractRawText({ buffer });
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
