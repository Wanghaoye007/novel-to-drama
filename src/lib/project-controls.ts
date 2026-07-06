import { desc, eq } from "drizzle-orm";
import { db, schema } from "@/db/client";

type ProjectRow = typeof schema.projects.$inferSelect;

export type RunAllSettings = {
  enabled: boolean;
  generationVariant?: string | null;
  repairBudget?: string | null;
  requestedAt?: string;
  pausedAt?: string;
  pausedReason?: string | null;
  pausedRound?: number | null;
  pausedQualityStatus?: string | null;
  pausedRewriteInstruction?: string | null;
};

export type ProjectControlMeta = Record<string, unknown> & {
  control?: {
    runAll?: RunAllSettings;
  };
  clonedFromProjectId?: string;
  archivedAt?: string | null;
  archivedReason?: string | null;
};

type RoundSummary = {
  next_round_context?: {
    current_episode?: number;
  };
};

export function parseProjectMeta(metaJson: string | null): ProjectControlMeta {
  if (!metaJson) return {};
  try {
    const parsed = JSON.parse(metaJson) as unknown;
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as ProjectControlMeta;
    }
  } catch {
    return {};
  }
  return {};
}

export function serializeProjectMeta(meta: ProjectControlMeta): string {
  return JSON.stringify(meta, null, 2);
}

export function projectRunAllSettings(project: ProjectRow): RunAllSettings {
  const meta = parseProjectMeta(project.metaJson);
  const settings = meta.control?.runAll;
  return {
    enabled: settings?.enabled === true,
    generationVariant: settings?.generationVariant ?? null,
    repairBudget: settings?.repairBudget ?? null,
    requestedAt: settings?.requestedAt,
  };
}

export function projectArchivedAt(project: Pick<ProjectRow, "metaJson">): string | null {
  const meta = parseProjectMeta(project.metaJson);
  return typeof meta.archivedAt === "string" && meta.archivedAt
    ? meta.archivedAt
    : null;
}

export function isProjectArchived(project: Pick<ProjectRow, "metaJson">): boolean {
  return Boolean(projectArchivedAt(project));
}

export async function updateProjectMeta(
  projectId: string,
  updater: (meta: ProjectControlMeta) => ProjectControlMeta
): Promise<ProjectControlMeta> {
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, projectId),
  });
  if (!project) throw new Error("project not found");
  const nextMeta = updater(parseProjectMeta(project.metaJson));
  await db
    .update(schema.projects)
    .set({ metaJson: serializeProjectMeta(nextMeta), updatedAt: new Date() })
    .where(eq(schema.projects.id, projectId));
  return nextMeta;
}

export function currentEpisodeFromRoundSummary(summaryJson: string | null): number | null {
  if (!summaryJson) return null;
  try {
    const summary = JSON.parse(summaryJson) as RoundSummary;
    const current = summary.next_round_context?.current_episode;
    return Number.isFinite(current) ? Number(current) : null;
  } catch {
    return null;
  }
}

export async function latestRoundForProject(projectId: string) {
  const rounds = await db.query.rounds.findMany({
    where: eq(schema.rounds.projectId, projectId),
    orderBy: [desc(schema.rounds.roundNum)],
    limit: 1,
  });
  return rounds[0] ?? null;
}

export async function projectNeedsNextRound(project: ProjectRow): Promise<boolean> {
  if (project.status === "paused" || project.status === "done" || project.status === "failed") {
    return false;
  }
  const latest = await latestRoundForProject(project.id);
  if (latest && latest.status !== "done") return false;
  const currentEpisode = currentEpisodeFromRoundSummary(latest?.summaryJson ?? null);
  return currentEpisode == null || currentEpisode < project.targetEpisodeCount;
}
