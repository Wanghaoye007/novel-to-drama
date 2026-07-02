import { NextRequest, NextResponse } from "next/server";
import { v4 as uuid } from "uuid";
import { db, schema } from "@/db/client";
import { startEngineRound } from "@/lib/engine-runner";
import { kickJobWorker } from "@/lib/job-worker";
import {
  assertProjectQuota,
  assertTenantJobQuota,
  findTenantProject,
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";
import { recordUsageEvent } from "@/lib/platform-usage";
import { parseProjectMeta, serializeProjectMeta } from "@/lib/project-controls";

type CloneBody = {
  name?: string | null;
  generationVariant?: string | null;
  repairBudget?: string | null;
};

async function readBody(req: NextRequest): Promise<CloneBody> {
  try {
    return (await req.json()) as CloneBody;
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
    await assertProjectQuota(context);
    await assertTenantJobQuota(context.tenant.id);

    const source = await findTenantProject(id, context.tenant.id);
    if (!source) return NextResponse.json({ error: "not found" }, { status: 404 });

    const body = await readBody(req);
    const projectId = uuid();
    const now = new Date();
    const sourceMeta = parseProjectMeta(source.metaJson);
    const metaJson = serializeProjectMeta({
      ...sourceMeta,
      clonedFromProjectId: source.id,
      clonedAt: now.toISOString(),
      control: {
        ...(sourceMeta.control ?? {}),
        runAll: {
          ...(sourceMeta.control?.runAll ?? {}),
          enabled: false,
        },
      },
    });

    await db.insert(schema.projects).values({
      id: projectId,
      tenantId: context.tenant.id,
      ownerUserId: context.user.id,
      name: body.name?.trim() || `${source.name} copy`,
      pipelineType: source.pipelineType,
      novelText: source.novelText,
      metaJson,
      targetLanguage: source.targetLanguage,
      targetEpisodeCount: source.targetEpisodeCount,
      status: "running",
      createdAt: now,
      updatedAt: now,
    });

    const job = await startEngineRound(projectId, 1, {
      generationVariant: body.generationVariant,
      repairBudget: body.repairBudget,
    });
    kickJobWorker();
    await recordUsageEvent({
      context,
      eventType: "project_create",
      projectId,
      jobId: job.jobId,
      metadata: {
        clonedFromProjectId: source.id,
        roundNum: 1,
        targetEpisodeCount: source.targetEpisodeCount,
        generationVariant: body.generationVariant,
        repairBudget: body.repairBudget,
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
