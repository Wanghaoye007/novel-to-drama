import { NextResponse } from "next/server";
import { asc, eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { optimizeEpisodeScript } from "@/lib/episode-ai-optimize";
import { writeEpisodeTxt } from "@/lib/m6-export";
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

    const project = await findTenantProject(episode.projectId, context.tenant.id);
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
    const [round, bible, episodes] = await Promise.all([
      db.query.rounds.findFirst({
        where: eq(schema.rounds.id, episode.roundId),
      }),
      db.query.bibles.findFirst({
        where: eq(schema.bibles.projectId, episode.projectId),
      }),
      db.query.episodes.findMany({
        where: eq(schema.episodes.projectId, episode.projectId),
        orderBy: [asc(schema.episodes.epNum)],
      }),
    ]);

    const result = await optimizeEpisodeScript({
      project,
      episode,
      bible,
      round,
      episodes,
      instruction: body.instruction,
      llmModel: body.llmModel,
    });

    const now = new Date();
    const reviewJson = JSON.stringify(
      {
        status: "needs_human_review",
        source: "episode_ai_optimize",
        instruction: body.instruction?.trim() || null,
        llmModel: result.llmModel,
        optimizedAt: now.toISOString(),
        note: "AI 定向优化当前集，旧稿为基准；请人工复核前后承接后再确认。",
      },
      null,
      2
    );
    await db
      .update(schema.episodes)
      .set({
        draftMd: result.scriptText,
        scriptTxt: result.scriptText,
        reviewJson,
        retryCount: episode.retryCount + 1,
        status: "red",
        updatedAt: now,
      })
      .where(eq(schema.episodes.id, episode.id));
    await writeEpisodeTxt(project.id, episode.epNum, result.scriptText);

    return NextResponse.json(
      {
        episodeId: episode.id,
        epNum: episode.epNum,
        scriptTxt: result.scriptText,
        status: "needs_human_review",
        llmModel: result.llmModel,
      },
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
