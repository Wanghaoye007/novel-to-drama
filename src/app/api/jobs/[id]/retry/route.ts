import { NextRequest, NextResponse } from "next/server";
import { eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { kickJobWorker } from "@/lib/job-worker";
import {
  findJob,
  isJobRetryable,
  jobToView,
  requeueRetryableJob,
} from "@/lib/jobs";
import {
  findTenantProject,
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";
import { normalizeLlmModel } from "@/lib/llm-model-options";

async function canAccessJob(
  job: NonNullable<Awaited<ReturnType<typeof findJob>>>,
  tenantId: string,
  ownerUserId: string
): Promise<boolean> {
  if (job.projectId) {
    return Boolean(await findTenantProject(job.projectId, tenantId, ownerUserId));
  }
  return Boolean(job.tenantId && job.tenantId === tenantId);
}

async function prepareRetryState(
  job: NonNullable<Awaited<ReturnType<typeof findJob>>>
): Promise<void> {
  if (job.kind !== "round_generation") return;
  if (!job.projectId || !job.roundId) {
    throw new Error("round generation job is missing project or round id");
  }
  const now = new Date();
  await db
    .update(schema.rounds)
    .set({ status: "running", summaryJson: null })
    .where(eq(schema.rounds.id, job.roundId));
  await db
    .update(schema.projects)
    .set({ status: "running", updatedAt: now })
    .where(eq(schema.projects.id, job.projectId));
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const context = await resolvePlatformContext(req);
    const job = await findJob(id);
    if (!job || !(await canAccessJob(job, context.tenant.id, context.user.id))) {
      return NextResponse.json({ error: "not found" }, { status: 404 });
    }
    if (!isJobRetryable(job)) {
      return NextResponse.json(
        {
          error: `只有失败任务或长时间无更新的运行中任务可以重试，当前状态：${job.status}`,
        },
        { status: 409, headers: platformHeaders(context) }
      );
    }

    const body = (await req.json().catch(() => ({}))) as { llmModel?: string | null };
    const payloadPatch =
      job.kind === "round_generation" && body.llmModel
        ? { llmModel: normalizeLlmModel(body.llmModel) }
        : undefined;

    await prepareRetryState(job);
    const retried = await requeueRetryableJob(job.id, { payloadPatch });
    kickJobWorker();

    return NextResponse.json(
      { status: "queued", job: jobToView(retried) },
      { headers: platformHeaders(context) }
    );
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}
