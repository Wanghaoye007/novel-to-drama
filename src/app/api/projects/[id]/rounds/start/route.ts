import { NextRequest, NextResponse } from "next/server";
import { desc, eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { startEngineRound } from "@/lib/engine-runner";
import { kickJobWorker } from "@/lib/job-worker";
import {
  findTenantProject,
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";
import { recordUsageEvent } from "@/lib/platform-usage";
import { currentEpisodeFromRoundSummary } from "@/lib/project-controls";

type RoundStartOptions = {
  generationVariant?: string | null;
  repairBudget?: string | null;
  episodesPerRound?: number | string | null;
};

async function readRoundStartOptions(req: NextRequest): Promise<RoundStartOptions> {
  const contentType = req.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) return {};
  try {
    const body = (await req.json()) as RoundStartOptions;
    return {
      generationVariant: body.generationVariant ?? null,
      repairBudget: body.repairBudget ?? null,
      episodesPerRound: body.episodesPerRound ?? null,
    };
  } catch {
    return {};
  }
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const context = await resolvePlatformContext(req);
    const options = await readRoundStartOptions(req);
    const project = await findTenantProject(id, context.tenant.id);
    if (!project) return NextResponse.json({ error: "not found" }, { status: 404 });
    if (project.status === "paused") {
      return NextResponse.json(
        { error: "项目已暂停，继续后才能启动新轮次" },
        { status: 409, headers: platformHeaders(context) }
      );
    }

    const existing = await db.query.rounds.findMany({
      where: eq(schema.rounds.projectId, id),
      orderBy: [desc(schema.rounds.roundNum)],
    });
    const latest = existing[0];
    if (latest && latest.status !== "done") {
      return NextResponse.json(
        {
          error: `第 ${latest.roundNum} 轮仍在${latest.status}`,
          roundNum: latest.roundNum,
        },
        { status: 409, headers: platformHeaders(context) }
      );
    }

    const currentEpisode = currentEpisodeFromRoundSummary(latest?.summaryJson ?? null);
    if (
      project.status === "done" ||
      (currentEpisode != null && currentEpisode >= project.targetEpisodeCount)
    ) {
      await db
        .update(schema.projects)
        .set({ status: "done", updatedAt: new Date() })
        .where(eq(schema.projects.id, id));
      return NextResponse.json(
        {
          error: `目标 ${project.targetEpisodeCount} 集已完成`,
          currentEpisode: currentEpisode ?? project.targetEpisodeCount,
        },
        { status: 409, headers: platformHeaders(context) }
      );
    }

    const roundNum = (latest?.roundNum ?? 0) + 1;
    const job = await startEngineRound(id, roundNum, options);
    kickJobWorker();
    await recordUsageEvent({
      context,
      eventType: "round_start",
      projectId: id,
      jobId: job.jobId,
      metadata: { roundNum, ...options },
    });
    return NextResponse.json(
      { roundNum, jobId: job.jobId, status: "started" },
      { headers: platformHeaders(context) }
    );
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}
