export type ManualEditLedgerEntry = {
  episodeId: string;
  episodeNumber: number;
  updatedAt: string;
  changeSummary: string;
  touchedTerms: string[];
  impactedEpisodes: number[];
  editedTail: string[];
  continuityInstruction: string;
};

type ManualEditMeta = {
  control?: {
    manualEditLedger?: {
      entries?: ManualEditLedgerEntry[];
    };
  };
};

function parseMeta(metaJson: string | null | undefined): ManualEditMeta {
  if (!metaJson) return {};
  try {
    const parsed = JSON.parse(metaJson) as unknown;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed)
      ? (parsed as ManualEditMeta)
      : {};
  } catch {
    return {};
  }
}

export function manualEditContextForEngine(metaJson: string | null | undefined): string | null {
  const entries = parseMeta(metaJson).control?.manualEditLedger?.entries ?? [];
  const latestEntries = entries.slice(-8);
  if (latestEntries.length === 0) return null;
  return [
    "【运营人工改稿承接要求】",
    "以下内容来自运营对已生成剧本的人工修改，是后续改编必须遵守的新事实基准；它不是原始小说正文。",
    ...latestEntries.flatMap((entry) => [
      `- EP${String(entry.episodeNumber).padStart(2, "0")} 已被人工修改：${entry.changeSummary}`,
      `  结尾新事实：${entry.editedTail.join(" / ") || "无"}`,
      `  影响后续集：${entry.impactedEpisodes.length ? entry.impactedEpisodes.map((num) => `EP${String(num).padStart(2, "0")}`).join("、") : "未生成后续集"}`,
      `  后续承接：${entry.continuityInstruction}`,
    ]),
  ].join("\n");
}

export function sourceTextWithManualEditContext(
  sourceText: string,
  metaJson: string | null | undefined
): string {
  const context = manualEditContextForEngine(metaJson);
  if (!context) return sourceText;
  return `${sourceText.trim()}\n\n${context}\n`;
}
