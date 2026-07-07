import { NextRequest, NextResponse } from "next/server";
import { v4 as uuid } from "uuid";
import { desc, eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { normalizeNovel } from "@/lib/m1-normalize";
import { startEngineRound } from "@/lib/engine-runner";
import { kickJobWorker } from "@/lib/job-worker";
import {
  assertProjectQuota,
  assertTenantJobQuota,
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";
import { recordUsageEvent } from "@/lib/platform-usage";

export async function GET(req: NextRequest) {
  try {
    const context = await resolvePlatformContext(req);
    const list = await db.query.projects.findMany({
      where: eq(schema.projects.tenantId, context.tenant.id),
      orderBy: [desc(schema.projects.createdAt)],
    });
    return NextResponse.json(list, { headers: platformHeaders(context) });
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}

export async function POST(req: NextRequest) {
  try {
    const context = await resolvePlatformContext(req);
    await assertProjectQuota(context);
    await assertTenantJobQuota(context.tenant.id);
    const form = await req.formData();
    const name = form.get("name") as string;
    const targetEpStr = form.get("targetEpisodeCount") as string;
    const generationVariant = form.get("generationVariant") as string | null;
    const repairBudget = form.get("repairBudget") as string | null;
    const episodesPerRound = form.get("episodesPerRound") as string | null;
    const llmModel = form.get("llmModel") as string | null;
    const file = form.get("file") as File;
    if (!name || !file) {
      return NextResponse.json({ error: "missing fields" }, { status: 400 });
    }
    const targetEpisodeCount = parseInt(targetEpStr || "30", 10);

    const buffer = Buffer.from(await file.arrayBuffer());
    const { text, meta } = await normalizeNovel(file.name, buffer);

    const projectId = uuid();
    const now = new Date();

    await db.insert(schema.projects).values({
      id: projectId,
      tenantId: context.tenant.id,
      ownerUserId: context.user.id,
      name,
      pipelineType: "A",
      novelText: text,
      metaJson: JSON.stringify(meta),
      targetEpisodeCount,
      status: "running",
      createdAt: now,
      updatedAt: now,
    });

    const job = await startEngineRound(projectId, 1, {
      generationVariant,
      repairBudget,
      episodesPerRound,
      llmModel,
    });
    kickJobWorker();
    await recordUsageEvent({
      context,
      eventType: "project_create",
      projectId,
      jobId: job.jobId,
      metadata: {
        roundNum: 1,
        targetEpisodeCount,
        generationVariant,
        repairBudget,
        episodesPerRound,
        llmModel,
      },
    });

    return NextResponse.json(
      { id: projectId, roundNum: 1, jobId: job.jobId },
      { headers: platformHeaders(context) }
    );
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}
