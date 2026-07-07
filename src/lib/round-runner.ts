import { v4 as uuid } from "uuid";
import { eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import {
  adaptEpisode,
  extractEpSummary,
  extractRoundSummary,
  extractEpisodePlan,
  type EpSummary,
  type RoundSummary,
} from "./m3-round";
import { reviewScript } from "./m4-review";
import { formatToAtomicShots } from "./m5-format";
import { writeEpisodeTxt } from "./m6-export";

const EPS_PER_ROUND = 5;

export async function runRound(
  projectId: string,
  roundNum: number
): Promise<{ roundId: string }> {
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, projectId),
  });
  const bible = await db.query.bibles.findFirst({
    where: eq(schema.bibles.projectId, projectId),
  });
  if (!project || !bible) throw new Error("project or bible not found");

  const startEp = (roundNum - 1) * EPS_PER_ROUND + 1;
  const endEp = startEp + EPS_PER_ROUND - 1;
  const epRange = `E${String(startEp).padStart(2, "0")}-E${String(endEp).padStart(2, "0")}`;

  const roundId = uuid();
  const now = new Date();
  await db.insert(schema.rounds).values({
    id: roundId,
    projectId,
    roundNum,
    epRange,
    status: "running",
    createdAt: now,
  });

  const prevRoundSummary: RoundSummary | null = bible.prevRoundSummaryJson
    ? JSON.parse(bible.prevRoundSummaryJson)
    : null;
  const epSummariesInRound: EpSummary[] = [];

  for (let i = 0; i < EPS_PER_ROUND; i++) {
    const epNum = startEp + i;
    const epId = uuid();
    await db.insert(schema.episodes).values({
      id: epId,
      projectId,
      roundId,
      epNum,
      status: "running",
      updatedAt: new Date(),
    });

    try {
      const epPlan = extractEpisodePlan(bible.episodePlanMd ?? "", epNum);
      const draftMd = await adaptEpisode({
        channel: (bible.channel ?? "female") as "male" | "female",
        epNum,
        characters: bible.charactersMd ?? "",
        sixAssets: bible.sixAssetsJson ?? "{}",
        epPlan,
        novelExcerpt: project.novelText,
        prevRoundSummary,
        prevEpSummariesInRound: epSummariesInRound,
      });

      const review = await reviewScript(draftMd);
      const scriptTxt = await formatToAtomicShots(draftMd).catch(() => draftMd);
      await writeEpisodeTxt(projectId, epNum, scriptTxt);

      const epSummary = await extractEpSummary(draftMd);
      epSummariesInRound.push(epSummary);

      await db
        .update(schema.episodes)
        .set({
          draftMd,
          scriptTxt,
          score: review.overall_score,
          reviewJson: JSON.stringify(review),
          epSummaryJson: JSON.stringify(epSummary),
          status: review.status,
          updatedAt: new Date(),
        })
        .where(eq(schema.episodes.id, epId));
    } catch (e) {
      await db
        .update(schema.episodes)
        .set({
          status: "failed",
          reviewJson: JSON.stringify({ error: String(e) }),
          updatedAt: new Date(),
        })
        .where(eq(schema.episodes.id, epId));
    }
  }

  // Aggregate round summary
  let roundSummary: RoundSummary | null = null;
  try {
    if (epSummariesInRound.length > 0) {
      roundSummary = await extractRoundSummary(epSummariesInRound);
    }
  } catch {
    // non-fatal
  }

  await db
    .update(schema.rounds)
    .set({
      summaryJson: roundSummary ? JSON.stringify(roundSummary) : null,
      status: "done",
    })
    .where(eq(schema.rounds.id, roundId));

  if (roundSummary) {
    await db
      .update(schema.bibles)
      .set({
        prevRoundSummaryJson: JSON.stringify(roundSummary),
        updatedAt: new Date(),
      })
      .where(eq(schema.bibles.projectId, projectId));
  }

  return { roundId };
}

export async function retryEpisode(episodeId: string): Promise<void> {
  throw new Error(
    `legacy episode retry is disabled for ${episodeId}; use the Engine round runner repair path instead`
  );
}
