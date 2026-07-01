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
    const roundNum = (existing[0]?.roundNum ?? 0) + 1;
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
