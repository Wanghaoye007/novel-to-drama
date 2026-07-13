import { NextResponse } from "next/server";
import { asc, eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { analyzeEpisodeEditImpact } from "@/lib/edit-impact";
import { startEditImpactJob } from "@/lib/engine-runner";
import { kickJobWorker } from "@/lib/job-worker";
import {
  findTenantProject,
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";

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

    const [round, episodes] = await Promise.all([
      db.query.rounds.findFirst({
        where: eq(schema.rounds.id, episode.roundId),
      }),
      db.query.episodes.findMany({
        where: eq(schema.episodes.projectId, episode.projectId),
        orderBy: [asc(schema.episodes.epNum)],
      }),
    ]);
    const body = (await req.json().catch(() => ({}))) as {
      editedScriptText?: string | null;
      applyEdit?: boolean | null;
      optimizeDownstream?: boolean | null;
      llmModel?: string | null;
    };
    const roundSummary = round?.summaryJson
      ? (JSON.parse(round.summaryJson) as Parameters<
          typeof analyzeEpisodeEditImpact
        >[0]["roundSummary"])
      : null;

    if (body.applyEdit !== false) {
      const job = await startEditImpactJob(episode.id, {
        editedScriptText: body.editedScriptText,
        optimizeDownstream: body.optimizeDownstream !== false,
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
    }

    return NextResponse.json(
      analyzeEpisodeEditImpact({
        episode,
        episodes,
        roundSummary,
        editedScriptText: body.editedScriptText,
      }),
      { headers: platformHeaders(context) }
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
