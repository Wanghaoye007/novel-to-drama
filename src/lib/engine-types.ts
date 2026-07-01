export type QualityStatus =
  | "usable"
  | "needs_rewrite"
  | "context_conflict"
  | "needs_human_review";

export type EngineJobKind = "round_generation" | "quality_samples";
export type EngineJobStatus = "queued" | "running" | "succeeded" | "failed";

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

export interface EngineStoryBible {
  genre: string;
  mainline: string;
  characters: string[];
  relationships: string[];
  speech_styles: Record<string, string>;
  immutable_facts: string[];
  forbidden_changes: string[];
}

export interface EngineEpisodeContext {
  target_episode_range: string;
  story_stage: string;
  source_to_episode_mapping: string[];
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

export interface EngineRoundResult {
  project_id: string;
  round_number: number;
  source_analysis: Record<string, unknown>;
  episode_context: EngineEpisodeContext;
  story_bible: EngineStoryBible;
  script_batch: {
    episodes: EngineEpisode[];
  };
  quality_report: EngineQualityReport;
  next_round_context: EngineNextRoundContext;
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
  target_episode_range?: string | null;
  quality_status?: QualityStatus | null;
  hook_score?: number | null;
  conflict_score?: number | null;
  cliffhanger_score?: number | null;
  continuity_score?: number | null;
  video_feasibility_score?: number | null;
  warnings: string[];
}

export interface QualitySampleResult {
  sample_id: string;
  label: string;
  project_dir: string;
  rounds: QualitySampleRoundReport[];
}

export interface QualitySampleEvaluationReport {
  samples: QualitySampleResult[];
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
    `3秒 Hook：${episode.hook_3s}`,
    `主情绪：${episode.main_emotion}`,
    `消费理由：${episode.watch_reason}`,
    "",
  ];

  for (const scene of episode.scenes) {
    parts.push(scene.heading);
    parts.push(`人物：${scene.characters.join("、")}`);
    parts.push("");
    for (const line of scene.lines) parts.push(renderEngineLine(line));
    parts.push("");
  }

  parts.push(`结尾钩子：${episode.cliffhanger}`);
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

export function renderEpisodeContextMarkdown(context: EngineEpisodeContext): string {
  return [
    `目标集数：${context.target_episode_range}`,
    `剧情阶段：${context.story_stage}`,
    `置信度：${context.confidence}`,
    "",
    "原文到集数映射：",
    ...context.source_to_episode_mapping.map((item) => `- ${item}`),
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
