export type QualityStatus =
  | "usable"
  | "needs_rewrite"
  | "context_conflict"
  | "needs_human_review";

export type EngineJobKind = "round_generation" | "quality_samples";
export type EngineJobStatus = "queued" | "running" | "succeeded" | "failed";
export type EngineProjectStatus =
  | "draft"
  | "bible_ready"
  | "running"
  | "paused"
  | "done"
  | "failed";

export interface EngineJob {
  id: string;
  kind: EngineJobKind;
  status: EngineJobStatus;
  projectId: string | null;
  tenantId: string | null;
  roundId: string | null;
  title: string;
  progress: number;
  message: string | null;
  errorText: string | null;
  payloadJson: string | null;
  resultJson: string | null;
  attempts: number;
  isStale: boolean;
  isQueuedTooLong?: boolean;
  retryable: boolean;
  failureCategory?: string | null;
  statusReason?: string | null;
  operatorHint?: string | null;
  createdAt: string;
  updatedAt: string;
  startedAt: string | null;
  finishedAt: string | null;
}

export interface EngineSceneLine {
  kind: "action" | "dialogue" | "os" | "vo" | "transition";
  text: string;
  speaker?: string | null;
  emotion?: string | null;
}

export interface EngineScene {
  heading: string;
  characters: string[];
  lines: EngineSceneLine[];
}

export interface EngineEpisode {
  episode: number;
  title: string;
  hook_3s: string;
  main_emotion: string;
  watch_reason: string;
  scenes: EngineScene[];
  cliffhanger: string;
  state_update: Record<string, unknown>;
}

export interface EngineQualityReport {
  status: QualityStatus;
  scores: {
    hook: number;
    conflict: number;
    cliffhanger: number;
    continuity: number;
    video_feasibility: number;
  };
  blocking_issues: string[];
  rewrite_instruction: string;
}

export interface EngineLLMUsageMetrics {
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  total_tokens?: number | null;
}

export interface EngineLLMCallMetric {
  stage: string;
  response_model: string;
  duration_ms: number;
  status: string;
  usage?: EngineLLMUsageMetrics | null;
  error?: string | null;
}

export interface EnginePipelineStageMetric {
  name: string;
  duration_ms: number;
  status: string;
  error?: string | null;
}

export interface EngineRuntimeReport {
  generation_variant: string;
  repair_budget: string;
  llm_model?: string | null;
  total_duration_ms: number;
  stages: EnginePipelineStageMetric[];
  llm_calls: EngineLLMCallMetric[];
  methodology_cards?: string[];
}

export interface EngineSourceStrengthProfile {
  conflict_strength: number;
  hook_strength: number;
  character_tag_strength: number;
  emotion_asset_strength: number;
  signature_scene_strength: number;
  visualization_readiness: number;
  overall_level: "strong" | "medium" | "weak";
  recommended_intensity: "light" | "medium" | "heavy";
  reasons: string[];
}

export interface EngineMethodologyCard {
  id: string;
  source_id: string;
  name: string;
  category: string;
  trigger: string;
  generation_rule: string;
  quality_rule: string;
  status: "draft" | "active" | "archived" | "rejected";
  version: number;
}

export interface EngineMethodologyContext {
  source_strength_level: "strong" | "medium" | "weak";
  adaptation_intensity: "light" | "medium" | "heavy";
  cards: EngineMethodologyCard[];
}

export interface EngineMethodologyQualityReport {
  issues: Array<{
    card_id: string;
    card_name: string;
    severity: "advisory" | "blocking";
    episode?: number | null;
    message: string;
    evidence: string[];
  }>;
  rewrite_instruction: string;
}

export interface EngineStoryBible {
  genre: string;
  mainline: string;
  characters: string[];
  relationships: string[];
  speech_styles: Record<string, string>;
  immutable_facts: string[];
  forbidden_changes: string[];
}

export interface EngineEpisodeSourceMapping {
  source: string;
  target_episode?: string | number | null;
  retained_assets?: string[] | string | null;
  adaptation_reason?: string | null;
  information_increment?: string | null;
  adaptation_action?: string | null;
}

export interface EngineEpisodeContext {
  target_episode_range: string;
  story_stage: string;
  source_to_episode_mapping: Array<string | EngineEpisodeSourceMapping>;
  must_carry_context: string[];
  forbidden_reveals: string[];
  adaptation_actions: string[];
  confidence: number;
}

export interface EngineNextRoundContext {
  summary: string;
  current_episode: number;
  open_hooks: string[];
  forbidden_reveals: string[];
  character_knowledge: Record<string, string[]>;
  relationship_changes: string[];
  prop_states: string[];
  foreshadowing_ledger: string[];
}

export interface EngineSourceFidelityReport {
  score: number;
  preserved_original_hook: boolean;
  blocking_warnings: string[];
  advisory_warnings: string[];
}

export interface EngineContinuityAuditReport {
  score: number;
  blocking_warnings: string[];
  advisory_warnings: string[];
  links?: Array<{
    previous_episode: number;
    next_episode: number;
    status: string;
    warnings: string[];
  }>;
}

export interface EngineStoryStateLedger {
  current_episode: number;
  entries: Array<{
    episode?: number | null;
    kind: string;
    key: string;
    value: string;
    status: string;
    source?: string | null;
  }>;
  open_hooks: string[];
  forbidden_reveals: string[];
  character_knowledge: Record<string, string[]>;
  relationship_changes: string[];
  prop_states: string[];
  foreshadowing_ledger: string[];
  blocking_warnings?: string[];
  warnings: string[];
}

export interface EngineAdaptationQualityReport {
  source_fidelity: EngineSourceFidelityReport;
  continuity: EngineContinuityAuditReport;
  story_state_ledger: EngineStoryStateLedger;
  blocking_warnings: string[];
  advisory_warnings: string[];
  rewrite_instruction: string;
}

export interface EngineDramaQualityDimension {
  name:
    | "character_integrity"
    | "conflict_causality"
    | "emotional_progression"
    | "dialogue_naturalness"
    | "source_asset_preservation"
    | "hook_and_cliffhanger";
  score: number;
  status: "passed" | "advisory" | "blocking";
  evidence: string[];
  suggestion: string;
}

export interface EngineDramaQualityComparison {
  baseline_overall_score: number;
  pipeline_overall_score: number;
  delta: number;
  verdict:
    | "pipeline_clearly_better"
    | "pipeline_slightly_better"
    | "tie"
    | "baseline_better";
  reason: string;
}

export interface EngineDramaQualityReport {
  overall_score: number;
  dimensions: EngineDramaQualityDimension[];
  blocking_issues: string[];
  advisory_warnings: string[];
  rewrite_instruction: string;
  baseline_comparison?: EngineDramaQualityComparison | null;
}

export interface EngineEpisodeNoveltyProfile {
  episode: number;
  title: string;
  scene_skeleton: string;
  action_signature: string;
  dialogue_signature: string;
  cliffhanger_signature: string;
}

export interface EngineCrossEpisodeSimilarityIssue {
  episodes: [number, number];
  kind:
    | "overall"
    | "scene_skeleton"
    | "action_chain"
    | "dialogue_pattern"
    | "cliffhanger";
  score: number;
  severity: "blocking" | "advisory";
  evidence: string[];
  suggestion: string;
}

export interface EngineScriptNoveltyReport {
  overall_score: number;
  episode_profiles: EngineEpisodeNoveltyProfile[];
  similarity_issues: EngineCrossEpisodeSimilarityIssue[];
  blocking_issues: string[];
  advisory_warnings: string[];
  rewrite_instruction: string;
}

export interface EngineSourceEvidenceItem {
  episode: number;
  source_anchor: string;
  adaptation_reason: string;
  retained_assets: string[];
  script_evidence: string[];
  evidence_spans?: EngineSourceEvidenceSpan[];
  status: "matched" | "partial" | "missing";
}

export interface EngineSourceEvidenceSpan {
  asset: string;
  source_anchor: string;
  source_excerpt: string;
  source_line?: string | null;
  source_line_index?: number | null;
  script_line?: string | null;
  script_line_index?: number | null;
  adaptation_reason: string;
  status: "matched" | "missing";
}

export interface EngineSourceEvidenceReport {
  coverage_score: number;
  items: EngineSourceEvidenceItem[];
  missing_items: string[];
  rewrite_instruction: string;
}

export interface EngineRoundResult {
  project_id: string;
  round_number: number;
  source_analysis: Record<string, unknown>;
  episode_context: EngineEpisodeContext;
  viral_asset_report?: Record<string, unknown> | null;
  source_strength_profile?: EngineSourceStrengthProfile | null;
  methodology_context?: EngineMethodologyContext | null;
  story_bible: EngineStoryBible;
  series_structure_plan?: Record<string, unknown> | null;
  episode_plan?: Record<string, unknown> | null;
  episode_source_packets?: Record<string, unknown> | null;
  script_batch: {
    episodes: EngineEpisode[];
  };
  quality_report: EngineQualityReport;
  next_round_context: EngineNextRoundContext;
  adaptation_quality_report?: EngineAdaptationQualityReport | null;
  methodology_quality_report?: EngineMethodologyQualityReport | null;
  drama_quality_report?: EngineDramaQualityReport | null;
  script_novelty_report?: EngineScriptNoveltyReport | null;
  source_evidence_report?: EngineSourceEvidenceReport | null;
  story_state_ledger?: EngineStoryStateLedger | null;
  runtime_report?: EngineRuntimeReport | null;
}

export interface DeliveryPreflightReport {
  project_id: string;
  round_number: number;
  target_episode_range: string;
  quality_status: QualityStatus;
  ready: boolean;
  warnings: string[];
  files: Array<{ path: string; bytes: number }>;
}

export interface QualitySampleRoundReport {
  round_number: number;
  generation_variant?: string | null;
  target_episode_range?: string | null;
  quality_status?: QualityStatus | null;
  hook_score?: number | null;
  conflict_score?: number | null;
  cliffhanger_score?: number | null;
  continuity_score?: number | null;
  video_feasibility_score?: number | null;
  source_fidelity_score?: number | null;
  continuity_audit_score?: number | null;
  baseline_overall_score?: number | null;
  pipeline_overall_score?: number | null;
  baseline_delta?: number | null;
  baseline_verdict?:
    | "pipeline_clearly_better"
    | "pipeline_slightly_better"
    | "tie"
    | "baseline_better"
    | null;
  baseline_reason?: string | null;
  source_fidelity_warnings?: string[];
  continuity_warnings?: string[];
  ledger_warnings?: string[];
  warnings: string[];
}

export interface QualitySampleResult {
  sample_id: string;
  label: string;
  variant?: string;
  project_dir: string;
  rounds: QualitySampleRoundReport[];
}

export interface QualitySampleEvaluationReport {
  samples: QualitySampleResult[];
  variants?: string[];
}

export interface QualitySampleEvaluationPayload {
  report: QualitySampleEvaluationReport | null;
  jobs: EngineJob[];
  reportPath: string;
  projectsDir: string;
  samplesPath: string;
  updatedAt: string | null;
  mode: "mock" | "real";
}

export function renderEngineLine(line: EngineSceneLine): string {
  if (line.kind === "action") return line.text;
  if (line.kind === "dialogue") {
    const emotion = line.emotion ? `（${line.emotion}）` : "";
    return `${line.speaker ?? "角色"}${emotion}：${line.text}`;
  }
  if (line.kind === "os") return `${line.speaker ?? "角色"}OS：${line.text}`;
  if (line.kind === "vo") return `${line.speaker ?? "画外"}VO：${line.text}`;
  return line.text;
}

export function renderEngineEpisode(episode: EngineEpisode): string {
  const parts = [
    `第${episode.episode}集 ${episode.title}`,
    "",
  ];

  for (const scene of episode.scenes) {
    parts.push(scene.heading);
    parts.push(`人物：${scene.characters.join("、")}`);
    parts.push("");
    for (const line of scene.lines) parts.push(renderEngineLine(line));
    parts.push("");
  }

  return parts.join("\n").trim();
}

export function qualityAverage(report: EngineQualityReport): number {
  const scores = report.scores;
  return (
    scores.hook +
    scores.conflict +
    scores.cliffhanger +
    scores.continuity +
    scores.video_feasibility
  ) / 5;
}

export function qualityToEpisodeStatus(status: QualityStatus): "green" | "red" {
  return status === "usable" ? "green" : "red";
}

export function renderStoryBibleMarkdown(bible: EngineStoryBible): string {
  const speechStyles = Object.entries(bible.speech_styles).map(
    ([name, style]) => `- ${name}: ${style}`
  );
  return [
    `类型：${bible.genre}`,
    "",
    `主线：${bible.mainline}`,
    "",
    "角色：",
    ...bible.characters.map((item) => `- ${item}`),
    "",
    "关系：",
    ...bible.relationships.map((item) => `- ${item}`),
    "",
    "语言风格：",
    ...speechStyles,
    "",
    "不可变事实：",
    ...bible.immutable_facts.map((item) => `- ${item}`),
    "",
    "禁止改动：",
    ...bible.forbidden_changes.map((item) => `- ${item}`),
  ].join("\n");
}

function renderSourceMapping(item: string | EngineEpisodeSourceMapping): string {
  if (typeof item === "string") return item;
  const parts = [item.source];
  if (item.target_episode != null) parts.push(`目标 ${item.target_episode}`);
  if (item.information_increment) parts.push(`增量：${item.information_increment}`);
  if (item.adaptation_action) parts.push(`动作：${item.adaptation_action}`);
  if (item.adaptation_reason) parts.push(`原因：${item.adaptation_reason}`);
  if (item.retained_assets) {
    const assets = Array.isArray(item.retained_assets)
      ? item.retained_assets.join("、")
      : item.retained_assets;
    parts.push(`保留：${assets}`);
  }
  return parts.join(" | ");
}

export function renderEpisodeContextMarkdown(context: EngineEpisodeContext): string {
  return [
    `目标集数：${context.target_episode_range}`,
    `剧情阶段：${context.story_stage}`,
    `置信度：${context.confidence}`,
    "",
    "原文到集数映射：",
    ...context.source_to_episode_mapping.map((item) => `- ${renderSourceMapping(item)}`),
    "",
    "必须承接：",
    ...context.must_carry_context.map((item) => `- ${item}`),
    "",
    "禁止提前揭露：",
    ...context.forbidden_reveals.map((item) => `- ${item}`),
    "",
    "改编动作：",
    ...context.adaptation_actions.map((item) => `- ${item}`),
  ].join("\n");
}

function jsonPlanningBlock(title: string, value: unknown | null | undefined): string {
  if (!value) return "";
  return [
    "",
    `## ${title}`,
    "",
    "```json",
    JSON.stringify(value, null, 2),
    "```",
  ].join("\n");
}

export function renderInternalPlanningMarkdown(result: EngineRoundResult): string {
  return [
    renderEpisodeContextMarkdown(result.episode_context),
    jsonPlanningBlock("爆款资产报告", result.viral_asset_report),
    jsonPlanningBlock("全剧结构规划", result.series_structure_plan),
    jsonPlanningBlock("单集戏剧设计", result.episode_plan),
    jsonPlanningBlock("逐集原文包", result.episode_source_packets),
    jsonPlanningBlock("改编一致性报告", result.adaptation_quality_report),
    jsonPlanningBlock("故事状态台账", result.story_state_ledger),
  ]
    .filter(Boolean)
    .join("\n");
}
