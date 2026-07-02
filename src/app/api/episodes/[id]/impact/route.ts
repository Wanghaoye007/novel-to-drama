import { NextResponse } from "next/server";
import { asc, eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { analyzeEpisodeEditImpact } from "@/lib/edit-impact";
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
      context.tenant.id
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
    };
    const roundSummary = round?.summaryJson
      ? (JSON.parse(round.summaryJson) as Parameters<
          typeof analyzeEpisodeEditImpact
        >[0]["roundSummary"])
      : null;

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
