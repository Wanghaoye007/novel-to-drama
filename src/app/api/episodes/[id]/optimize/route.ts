import { NextResponse } from "next/server";
import { eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { startEpisodeOptimizeJob } from "@/lib/engine-runner";
import { kickJobWorker } from "@/lib/job-worker";
import {
  findTenantProject,
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";

type OptimizeEpisodeBody = {
  instruction?: string | null;
  llmModel?: string | null;
};

export async function POST(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const context = await resolvePlatformContext(req);
    const episode = await db.query.episodes.findFirst({
      where: eq(schema.episodes.id, id),
    });
    if (!episode) {
      return NextResponse.json({ error: "episode not found" }, { status: 404 });
    }

    const project = await findTenantProject(
      episode.projectId,
      context.tenant.id,
      context.user.id
    );
    if (!project) {
      return NextResponse.json({ error: "not found" }, { status: 404 });
    }
    if (!episode.scriptTxt?.trim()) {
      return NextResponse.json(
        { error: "当前集还没有可优化的脚本" },
        { status: 409, headers: platformHeaders(context) }
      );
    }

    const body = (await req.json().catch(() => ({}))) as OptimizeEpisodeBody;
    const job = await startEpisodeOptimizeJob(episode.id, {
      instruction: body.instruction,
      llmModel: body.llmModel,
      idempotencyKey:
        req.headers.get("idempotency-key") ??
        req.headers.get("x-idempotency-key") ??
        null,
    });
    kickJobWorker();

    return NextResponse.json(
      {
        episodeId: episode.id,
        epNum: episode.epNum,
        jobId: job.id,
        status: "queued",
      },
      { status: 202, headers: platformHeaders(context) }
    );
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    return NextResponse.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 500 }
    );
  }
}
