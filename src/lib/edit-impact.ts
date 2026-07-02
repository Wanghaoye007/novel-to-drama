type EpisodeLike = {
  id: string;
  epNum: number;
  scriptTxt: string | null;
  epSummaryJson?: string | null;
  roundId: string;
};

type RoundSummaryLike = {
  story_state_ledger?: {
    entries?: Array<{
      episode?: number | null;
      kind?: string;
      key?: string;
      value?: string;
      status?: string;
    }>;
  } | null;
  next_round_context?: {
    open_hooks?: string[];
    forbidden_reveals?: string[];
    prop_states?: string[];
    foreshadowing_ledger?: string[];
  } | null;
};

export type EditImpactEpisode = {
  id: string;
  epNum: number;
  reason: string;
  hasScript: boolean;
};

export type EditImpactReport = {
  episodeId: string;
  episodeNumber: number;
  changed: boolean;
  changeSummary: string;
  touchedTerms: string[];
  impactedEpisodes: EditImpactEpisode[];
  impactedState: string[];
  recommendedAction: string;
  warnings: string[];
};

const COMMON_TERMS = new Set([
  "镜头",
  "特写",
  "中景",
  "近景",
  "全景",
  "推近",
  "切到",
  "切回",
  "画面",
  "声音",
  "人物",
  "夜内",
  "日内",
  "夜外",
  "日外",
]);

function normalizeText(value: string): string {
  return value.replace(/[\s，。！？、；：：“”‘’（）()《》【】\[\]·,.!?;:'"<>-]+/g, "");
}

function terms(value: string): string[] {
  const matches = value.match(/[\u4e00-\u9fffA-Za-z0-9]{2,}/g) ?? [];
  return Array.from(
    new Set(
      matches
        .map((item) => item.trim())
        .filter((item) => item.length >= 2 && !COMMON_TERMS.has(item))
        .slice(0, 80)
    )
  );
}

function lastMeaningfulLines(value: string, count = 4): string[] {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(-count);
}

function parseSummary(value?: string | null): Record<string, unknown> {
  if (!value) return {};
  try {
    return JSON.parse(value) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function textContainsAny(value: string, needles: string[]): boolean {
  const normalized = normalizeText(value);
  return needles.some((needle) => {
    const normalizedNeedle = normalizeText(needle);
    return normalizedNeedle.length >= 2 && normalized.includes(normalizedNeedle);
  });
}

function ledgerEntriesForEpisode(
  roundSummary: RoundSummaryLike | null,
  episodeNumber: number
): string[] {
  const entries = roundSummary?.story_state_ledger?.entries ?? [];
  return entries
    .filter((entry) => entry.episode === episodeNumber)
    .map((entry) =>
      [entry.kind, entry.key, entry.value, entry.status].filter(Boolean).join(": ")
    )
    .filter(Boolean)
    .slice(0, 12);
}

export function analyzeEpisodeEditImpact({
  episode,
  episodes,
  roundSummary,
  editedScriptText,
}: {
  episode: EpisodeLike;
  episodes: EpisodeLike[];
  roundSummary: RoundSummaryLike | null;
  editedScriptText?: string | null;
}): EditImpactReport {
  const original = episode.scriptTxt ?? "";
  const edited = editedScriptText ?? original;
  const changed = normalizeText(original) !== normalizeText(edited);
  const warnings: string[] = [];
  const originalTerms = terms(original);
  const editedTerms = terms(edited);
  const removedTerms = originalTerms.filter((term) => !editedTerms.includes(term));
  const addedTerms = editedTerms.filter((term) => !originalTerms.includes(term));
  const touchedTerms = Array.from(new Set([...removedTerms, ...addedTerms])).slice(0, 24);
  const originalTail = lastMeaningfulLines(original).join("\n");
  const editedTail = lastMeaningfulLines(edited).join("\n");
  const tailChanged = normalizeText(originalTail) !== normalizeText(editedTail);
  const impacted: EditImpactEpisode[] = [];
  const laterEpisodes = episodes
    .filter((item) => item.epNum > episode.epNum)
    .sort((a, b) => a.epNum - b.epNum);

  if (tailChanged && laterEpisodes[0]) {
    impacted.push({
      id: laterEpisodes[0].id,
      epNum: laterEpisodes[0].epNum,
      reason: "上一集结尾/断点变化，需要检查下一集开场承接",
      hasScript: Boolean(laterEpisodes[0].scriptTxt),
    });
  }

  for (const candidate of laterEpisodes) {
    const summary = parseSummary(candidate.epSummaryJson);
    const haystack = [
      candidate.scriptTxt ?? "",
      JSON.stringify(summary),
    ].join("\n");
    if (touchedTerms.length && textContainsAny(haystack, touchedTerms)) {
      if (!impacted.some((item) => item.id === candidate.id)) {
        impacted.push({
          id: candidate.id,
          epNum: candidate.epNum,
          reason: "后续剧集引用了本次编辑涉及的人物/道具/钩子词",
          hasScript: Boolean(candidate.scriptTxt),
        });
      }
    }
  }

  const impactedState = [
    ...ledgerEntriesForEpisode(roundSummary, episode.epNum),
    ...(roundSummary?.next_round_context?.open_hooks ?? []).filter((hook) =>
      textContainsAny(hook, touchedTerms)
    ),
    ...(roundSummary?.next_round_context?.prop_states ?? []).filter((prop) =>
      textContainsAny(prop, touchedTerms)
    ),
    ...(roundSummary?.next_round_context?.foreshadowing_ledger ?? []).filter((item) =>
      textContainsAny(item, touchedTerms)
    ),
  ].slice(0, 18);

  if (edited.length < 600) {
    warnings.push("编辑后字数偏短，可能触发脚本长度质量门禁");
  }
  if (tailChanged && !laterEpisodes[0]) {
    warnings.push("结尾发生变化，但当前没有后续集可自动校验");
  }
  if (!changed) {
    warnings.push("当前文本与数据库版本一致，没有检测到实际编辑");
  }

  const action =
    impacted.length > 0
      ? `建议从第 ${Math.min(...impacted.map((item) => item.epNum))} 集开始重跑或人工承接检查`
      : changed
        ? "只影响当前集，建议人工复核本集质量门禁后交付"
        : "无需重跑";

  const changeSummary = changed
    ? [
        addedTerms.length ? `新增 ${addedTerms.slice(0, 6).join("、")}` : "",
        removedTerms.length ? `移除 ${removedTerms.slice(0, 6).join("、")}` : "",
        tailChanged ? "结尾断点发生变化" : "",
      ]
        .filter(Boolean)
        .join("；") || "文本有改动"
    : "没有检测到改动";

  return {
    episodeId: episode.id,
    episodeNumber: episode.epNum,
    changed,
    changeSummary,
    touchedTerms,
    impactedEpisodes: impacted.slice(0, 12),
    impactedState,
    recommendedAction: action,
    warnings,
  };
}
