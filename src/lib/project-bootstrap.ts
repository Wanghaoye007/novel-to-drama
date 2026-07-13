import { and, desc, eq } from "drizzle-orm";
import { v4 as uuid } from "uuid";
import { db, schema } from "@/db/client";
import {
  episodesPerRound,
  generationVariant,
  repairBudget,
  selectedLlmModel,
  type RoundGenerationOptions,
} from "./engine-runner";
import { llmModelLabel } from "./llm-model-options";

type ProjectBootstrapInput = {
  tenantId: string;
  ownerUserId: string;
  name: string;
  novelText: string;
  meta: unknown;
  targetEpisodeCount: number;
  idempotencyKey?: string | null;
  options?: RoundGenerationOptions;
};

export type ProjectBootstrapResult = {
  projectId: string;
  roundId: string;
  roundNum: number;
  jobId: string;
  reused: boolean;
};

function storedProjectCreationKey(value?: string | null): string | null {
  const normalized = value?.trim();
  return normalized ? `project-create:${normalized}` : null;
}

export function findProjectCreationByIdempotency({
  tenantId,
  ownerUserId,
  idempotencyKey,
}: {
  tenantId: string;
  ownerUserId: string;
  idempotencyKey?: string | null;
}): ProjectBootstrapResult | null {
  const storedKey = storedProjectCreationKey(idempotencyKey);
  if (!storedKey) return null;
  const job = db
    .select()
    .from(schema.jobs)
    .where(
      and(
        eq(schema.jobs.tenantId, tenantId),
        eq(schema.jobs.kind, "round_generation"),
        eq(schema.jobs.idempotencyKey, storedKey)
      )
    )
    .orderBy(desc(schema.jobs.createdAt))
    .get();
  if (!job?.projectId || !job.roundId) return null;
  const project = db
    .select({ id: schema.projects.id })
    .from(schema.projects)
    .where(
      and(
        eq(schema.projects.id, job.projectId),
        eq(schema.projects.tenantId, tenantId),
        eq(schema.projects.ownerUserId, ownerUserId)
      )
    )
    .get();
  if (!project) return null;
  const round = db
    .select({ roundNum: schema.rounds.roundNum })
    .from(schema.rounds)
    .where(eq(schema.rounds.id, job.roundId))
    .get();
  return {
    projectId: project.id,
    roundId: job.roundId,
    roundNum: round?.roundNum ?? 1,
    jobId: job.id,
    reused: true,
  };
}

export function createProjectWithInitialJob(
  input: ProjectBootstrapInput
): ProjectBootstrapResult {
  const options = input.options ?? {};
  const selectedGenerationVariant = generationVariant(options.generationVariant);
  const selectedRepairBudget = repairBudget(options.repairBudget);
  const selectedEpisodesPerRound = episodesPerRound(options.episodesPerRound);
  const selectedModel = selectedLlmModel(options.llmModel);
  const storedKey =
    storedProjectCreationKey(input.idempotencyKey) ?? `project-create:${uuid()}`;

  return db.transaction((tx) => {
    const existing = tx
      .select()
      .from(schema.jobs)
      .where(
        and(
          eq(schema.jobs.tenantId, input.tenantId),
          eq(schema.jobs.kind, "round_generation"),
          eq(schema.jobs.idempotencyKey, storedKey)
        )
      )
      .orderBy(desc(schema.jobs.createdAt))
      .get();
    if (existing?.projectId && existing.roundId) {
      const project = tx
        .select({ id: schema.projects.id })
        .from(schema.projects)
        .where(
          and(
            eq(schema.projects.id, existing.projectId),
            eq(schema.projects.tenantId, input.tenantId),
            eq(schema.projects.ownerUserId, input.ownerUserId)
          )
        )
        .get();
      if (project) {
        const round = tx
          .select({ roundNum: schema.rounds.roundNum })
          .from(schema.rounds)
          .where(eq(schema.rounds.id, existing.roundId))
          .get();
        return {
          projectId: project.id,
          roundId: existing.roundId,
          roundNum: round?.roundNum ?? 1,
          jobId: existing.id,
          reused: true,
        };
      }
      throw new Error("idempotency key belongs to another project owner");
    }

    const now = new Date();
    const projectId = uuid();
    const roundId = uuid();
    const jobId = uuid();
    tx.insert(schema.projects)
      .values({
        id: projectId,
        tenantId: input.tenantId,
        ownerUserId: input.ownerUserId,
        name: input.name,
        pipelineType: "A",
        novelText: input.novelText,
        metaJson: JSON.stringify(input.meta),
        targetEpisodeCount: input.targetEpisodeCount,
        status: "running",
        createdAt: now,
        updatedAt: now,
      })
      .run();
    tx.insert(schema.rounds)
      .values({
        id: roundId,
        projectId,
        roundNum: 1,
        epRange: `EP01-EP${String(
          Math.min(selectedEpisodesPerRound, input.targetEpisodeCount)
        ).padStart(2, "0")}`,
        summaryJson: null,
        status: "running",
        createdAt: now,
      })
      .run();
    tx.insert(schema.jobs)
      .values({
        id: jobId,
        kind: "round_generation",
        status: "queued",
        projectId,
        tenantId: input.tenantId,
        roundId,
        title: `${input.name} · 第 1 轮 · ${selectedEpisodesPerRound}集`,
        progress: 0,
        message: `等待 worker 执行 · ${selectedGenerationVariant}/${selectedRepairBudget}/${selectedEpisodesPerRound}集 · ${llmModelLabel(selectedModel)}`,
        payloadJson: JSON.stringify({
          projectId,
          roundId,
          roundNumber: 1,
          generationVariant: selectedGenerationVariant,
          repairBudget: selectedRepairBudget,
          episodesPerRound: selectedEpisodesPerRound,
          llmModel: selectedModel,
        }),
        idempotencyKey: storedKey,
        attempts: 0,
        createdAt: now,
        updatedAt: now,
      })
      .run();

    return {
      projectId,
      roundId,
      roundNum: 1,
      jobId,
      reused: false,
    };
  });
}
