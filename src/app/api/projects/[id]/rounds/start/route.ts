import { NextRequest, NextResponse } from "next/server";
import { desc, eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { startEngineRound } from "@/lib/engine-runner";
import { kickJobWorker } from "@/lib/job-worker";
import {
  findTenantProject,
  platformHeaders,
  QuotaError,
  resolvePlatformContext,
} from "@/lib/platform-context";

export async function POST(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const context = await resolvePlatformContext(_req);
  const project = await findTenantProject(id, context.tenant.id);
  if (!project) return NextResponse.json({ error: "not found" }, { status: 404 });

  const existing = await db.query.rounds.findMany({
    where: eq(schema.rounds.projectId, id),
    orderBy: [desc(schema.rounds.roundNum)],
  });
  const roundNum = (existing[0]?.roundNum ?? 0) + 1;

  try {
    const job = await startEngineRound(id, roundNum);
    kickJobWorker();
    return NextResponse.json(
      { roundNum, jobId: job.jobId, status: "started" },
      { headers: platformHeaders(context) }
    );
  } catch (error) {
    if (error instanceof QuotaError) {
      return NextResponse.json(
        { error: error.message, quota: error.quota },
        { status: error.status }
      );
    }
    throw error;
  }
}
