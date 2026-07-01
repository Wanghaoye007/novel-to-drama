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

type RoundSummary = {
  next_round_context?: {
    current_episode?: number;
  };
};

function currentEpisodeFromSummary(summaryJson: string | null): number | null {
  if (!summaryJson) return null;
  try {
    const summary = JSON.parse(summaryJson) as RoundSummary;
    const current = summary.next_round_context?.current_episode;
    return Number.isFinite(current) ? Number(current) : null;
  } catch {
    return null;
  }
}

export async function POST(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const context = await resolvePlatformContext(_req);
    const project = await findTenantProject(id, context.tenant.id);
    if (!project) return NextResponse.json({ error: "not found" }, { status: 404 });

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

    const currentEpisode = currentEpisodeFromSummary(latest?.summaryJson ?? null);
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
    const job = await startEngineRound(id, roundNum);
    kickJobWorker();
    await recordUsageEvent({
      context,
      eventType: "round_start",
      projectId: id,
      jobId: job.jobId,
      metadata: { roundNum },
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
