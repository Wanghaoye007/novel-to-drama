import { NextRequest, NextResponse } from "next/server";
import { and, desc, eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { extractRuleBasedMeta, parseUpload } from "@/lib/novel-upload";
import { kickJobWorker } from "@/lib/job-worker";
import {
  createProjectWithInitialJob,
  findProjectCreationByIdempotency,
} from "@/lib/project-bootstrap";
import {
  assertProjectQuota,
  assertTenantJobQuota,
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";
import { recordUsageEvent } from "@/lib/platform-usage";

function projectListItem(project: typeof schema.projects.$inferSelect) {
  const { novelText: _novelText, ...safeProject } = project;
  return {
    ...safeProject,
    novelCharCount: project.novelText.length,
  };
}

export async function GET(req: NextRequest) {
  try {
    const context = await resolvePlatformContext(req);
    const list = await db.query.projects.findMany({
      where: and(
        eq(schema.projects.tenantId, context.tenant.id),
        eq(schema.projects.ownerUserId, context.user.id)
      ),
      orderBy: [desc(schema.projects.createdAt)],
    });
    return NextResponse.json(list.map(projectListItem), {
      headers: platformHeaders(context),
    });
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}

export async function POST(req: NextRequest) {
  try {
    const context = await resolvePlatformContext(req);
    const idempotencyKey =
      req.headers.get("idempotency-key") ??
      req.headers.get("x-idempotency-key") ??
      null;
    const replay = findProjectCreationByIdempotency({
      tenantId: context.tenant.id,
      ownerUserId: context.user.id,
      idempotencyKey,
    });
    if (replay) {
      return NextResponse.json(
        { id: replay.projectId, roundNum: replay.roundNum, jobId: replay.jobId },
        { status: 202, headers: platformHeaders(context) }
      );
    }
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
    if (
      !Number.isInteger(targetEpisodeCount) ||
      targetEpisodeCount < 1 ||
      targetEpisodeCount > 100
    ) {
      return NextResponse.json(
        { error: "targetEpisodeCount must be between 1 and 100" },
        { status: 400, headers: platformHeaders(context) }
      );
    }

    const buffer = Buffer.from(await file.arrayBuffer());
    const text = await parseUpload(file.name, buffer);
    if (!text.trim()) {
      return NextResponse.json(
        { error: "novel is empty" },
        { status: 400, headers: platformHeaders(context) }
      );
    }
    const meta = {
      ...extractRuleBasedMeta(text),
      completeness: "unknown" as const,
      genre: "unknown" as const,
      channelHint: "unknown" as const,
      anomalies: ["llm_judge_deferred_to_engine"],
    };

    const created = createProjectWithInitialJob({
      tenantId: context.tenant.id,
      ownerUserId: context.user.id,
      name,
      novelText: text,
      meta,
      targetEpisodeCount,
      idempotencyKey,
      options: {
        generationVariant,
        repairBudget,
        episodesPerRound,
        llmModel,
      },
    });
    kickJobWorker();
    if (!created.reused) {
      await recordUsageEvent({
        context,
        eventType: "project_create",
        projectId: created.projectId,
        jobId: created.jobId,
        metadata: {
          roundNum: 1,
          targetEpisodeCount,
          generationVariant,
          repairBudget,
          episodesPerRound,
          llmModel,
        },
      });
    }

    return NextResponse.json(
      { id: created.projectId, roundNum: 1, jobId: created.jobId },
      { status: 202, headers: platformHeaders(context) }
    );
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}
