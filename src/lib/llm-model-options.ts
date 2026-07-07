export const DEFAULT_LLM_MODEL = "google/gemini-3.1-flash-lite";

export const llmModelOptions = [
  {
    value: "google/gemini-3.1-flash-lite",
    label: "Gemini 3.1F",
    description: "稳定默认",
  },
  {
    value: "google/gemini-3.5-flash",
    label: "Gemini 3.5F",
    description: "质量优先",
  },
] as const;

export type LlmModelValue = (typeof llmModelOptions)[number]["value"];

const llmModelAliases = new Map<string, LlmModelValue>([
  ["gemini3.1f", "google/gemini-3.1-flash-lite"],
  ["gemini_3_1_flash", "google/gemini-3.1-flash-lite"],
  ["gemini_3_1_flash_lite", "google/gemini-3.1-flash-lite"],
  ["google/gemini-3.1-flash-lite", "google/gemini-3.1-flash-lite"],
  ["gemini3.5f", "google/gemini-3.5-flash"],
  ["gemini_3_5_flash", "google/gemini-3.5-flash"],
  ["google/gemini-3.5-flash", "google/gemini-3.5-flash"],
]);

export function normalizeLlmModel(
  value?: string | null,
  fallback?: string | null
): LlmModelValue {
  for (const candidate of [value, fallback, DEFAULT_LLM_MODEL]) {
    const normalized = String(candidate ?? "").trim().toLowerCase();
    const matched = llmModelAliases.get(normalized);
    if (matched) return matched;
  }
  return DEFAULT_LLM_MODEL;
}

export function llmModelLabel(value?: string | null): string {
  const normalized = normalizeLlmModel(value);
  return (
    llmModelOptions.find((option) => option.value === normalized)?.label ??
    normalized
  );
}
