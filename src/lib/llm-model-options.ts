export const DEFAULT_LLM_MODEL = "bytedance-seed/seed-2.0-mini";

export const llmModelOptions = [
  {
    value: "bytedance-seed/seed-2.0-mini",
    label: "豆包 Seed 2.0 Mini",
    description: "逐集高质量",
  },
  {
    value: "google/gemini-3.5-flash",
    label: "Gemini 3.5F",
    description: "质量优先",
  },
] as const;

export type LlmModelValue = (typeof llmModelOptions)[number]["value"];

const llmModelAliases = new Map<string, LlmModelValue>([
  ["doubao", "bytedance-seed/seed-2.0-mini"],
  ["doubao_seed_2_0_mini", "bytedance-seed/seed-2.0-mini"],
  ["seed2.0mini", "bytedance-seed/seed-2.0-mini"],
  ["seed_2_0_mini", "bytedance-seed/seed-2.0-mini"],
  ["bytedance-seed/seed-2.0-mini", "bytedance-seed/seed-2.0-mini"],
  ["doubao_seed_1_6_flash", "bytedance-seed/seed-2.0-mini"],
  ["seed1.6flash", "bytedance-seed/seed-2.0-mini"],
  ["seed_1_6_flash", "bytedance-seed/seed-2.0-mini"],
  ["bytedance-seed/seed-1.6-flash", "bytedance-seed/seed-2.0-mini"],
  // Seed 2.0 Lite can enter a repeated-whitespace loop for large JSON batches.
  // Existing selections migrate to the JSON-stable Doubao option on retry.
  ["doubao_seed_2_0_lite", "bytedance-seed/seed-2.0-mini"],
  ["seed2.0lite", "bytedance-seed/seed-2.0-mini"],
  ["seed_2_0_lite", "bytedance-seed/seed-2.0-mini"],
  ["bytedance-seed/seed-2.0-lite", "bytedance-seed/seed-2.0-mini"],
  // Existing projects and failed jobs that selected Gemini 3.1 migrate to the
  // new default when they are retried.
  ["gemini3.1f", "bytedance-seed/seed-2.0-mini"],
  ["gemini_3_1_flash", "bytedance-seed/seed-2.0-mini"],
  ["gemini_3_1_flash_lite", "bytedance-seed/seed-2.0-mini"],
  ["google/gemini-3.1-flash-lite", "bytedance-seed/seed-2.0-mini"],
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
