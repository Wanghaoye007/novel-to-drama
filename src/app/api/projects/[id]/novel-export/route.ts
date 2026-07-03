import { NextRequest } from "next/server";
import { asc, desc, eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import {
  buildEpisodeWordDocument,
  attachmentDisposition,
  formatEpisodesAsEpisodeText,
  sanitizeExportFilename,
  type ExportEpisode,
} from "@/lib/script-export";
import {
  findTenantProject,
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";
import { recordUsageEvent } from "@/lib/platform-usage";

export const dynamic = "force-dynamic";

type EpisodeRow = typeof schema.episodes.$inferSelect;
type RoundRow = typeof schema.rounds.$inferSelect;

function uniqueLatestEpisodes(
  episodes: EpisodeRow[],
  rounds: RoundRow[]
): ExportEpisode[] {
  const roundNumberById = new Map(rounds.map((round) => [round.id, round.roundNum]));
  const latestByEpisode = new Map<number, EpisodeRow>();
  for (const episode of episodes) {
    const current = latestByEpisode.get(episode.epNum);
    const episodeRound = roundNumberById.get(episode.roundId) ?? 0;
    const currentRound = current ? (roundNumberById.get(current.roundId) ?? 0) : -1;
    if (!current || episodeRound >= currentRound) {
      latestByEpisode.set(episode.epNum, episode);
    }
  }
  return [...latestByEpisode.values()]
    .sort((a, b) => a.epNum - b.epNum)
    .map((episode) => ({
      epNum: episode.epNum,
      scriptTxt: episode.scriptTxt,
    }));
}

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const context = await resolvePlatformContext(req);
    const project = await findTenantProject(id, context.tenant.id);
    if (!project) return new Response("not found", { status: 404 });

    const format = req.nextUrl.searchParams.get("format") ?? "txt";
    if (!["txt", "word", "docx"].includes(format)) {
      return Response.json(
        { error: "format must be txt, word, or docx" },
        { status: 400, headers: platformHeaders(context) }
      );
    }

    const rounds = await db.query.rounds.findMany({
      where: eq(schema.rounds.projectId, id),
      orderBy: [desc(schema.rounds.roundNum)],
    });
    const rawEpisodes = await db.query.episodes.findMany({
      where: eq(schema.episodes.projectId, id),
      orderBy: [asc(schema.episodes.epNum)],
    });
    const episodes = uniqueLatestEpisodes(rawEpisodes, rounds);
    const body = formatEpisodesAsEpisodeText(episodes);
    const safeName = sanitizeExportFilename(project.name);
    const isWord = format === "word" || format === "docx";

    await recordUsageEvent({
      context,
      eventType: isWord ? "episode_word_export" : "episode_txt_export",
      projectId: id,
      metadata: {
        format: isWord ? "docx" : "txt",
        episodes: episodes.length,
      },
    });

    if (isWord) {
      const docx = await buildEpisodeWordDocument(project.name, body);
      const filename = `${safeName}.docx`;
      return new Response(new Uint8Array(docx), {
        headers: {
          ...platformHeaders(context),
          "Content-Type":
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
          "Content-Disposition": attachmentDisposition(filename),
        },
      });
    }

    const filename = `${safeName}.txt`;
    return new Response(body, {
      headers: {
        ...platformHeaders(context),
        "Content-Type": "text/plain; charset=utf-8",
        "Content-Disposition": attachmentDisposition(filename),
      },
    });
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}
