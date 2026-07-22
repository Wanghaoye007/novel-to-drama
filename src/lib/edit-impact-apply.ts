import { asc, eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { analyzeEpisodeEditImpact, type EditImpactReport } from "./edit-impact";
import { optimizeEpisodeScript } from "./episode-ai-optimize";
import { writeEpisodeTxt } from "./episode-artifacts";
import type { ManualEditLedgerEntry } from "./manual-edit-context";
import { updateProjectMeta } from "./project-controls";

type ProjectRow = typeof schema.projects.$inferSelect;
type RoundRow = typeof schema.rounds.$inferSelect;
type BibleRow = typeof schema.bibles.$inferSelect;
type EpisodeRow = typeof schema.episodes.$inferSelect;

type Optimizer = typeof optimizeEpisodeScript;

export type AppliedImpactEpisode = {
  id: string;
  epNum: number;
  status: "optimized" | "pending" | "failed";
  message: string;
};

export type AppliedEditImpactResult = {
  report: EditImpactReport;
  applied: boolean;
  continuityInstruction: string | null;
  optimizedEpisodes: AppliedImpactEpisode[];
};

function parseRoundSummary(value?: string | null): Parameters<
  typeof analyzeEpisodeEditImpact
>[0]["roundSummary"] {
  if (!value) return null;
  try {
    return JSON.parse(value) as Parameters<typeof analyzeEpisodeEditImpact>[0]["roundSummary"];
  } catch {
    return null;
  }
}

function lastMeaningfulLines(value: string, count = 4): string[] {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(-count);
}

export function buildContinuityInstruction(
  report: EditImpactReport,
  editedScriptText: string
): string {
  const editedTail = lastMeaningfulLines(editedScriptText).join(" / ");
  const terms = report.touchedTerms.slice(0, 10).join("、") || "本集已修改信息";
  const state = report.impactedState.slice(0, 6).join("；") || "以用户改稿后的当前集为准";
  const firstImpacted = report.impactedEpisodes
    .map((item) => `EP${String(item.epNum).padStart(2, "0")}`)
    .join("、");
  return [
    `用户已修改 EP${String(report.episodeNumber).padStart(2, "0")}，后续剧情必须以修改稿为新基准。`,
    `下一集开头优先承接新结尾：${editedTail || "当前集结尾变化"}`,
    `需要同步校正的人物/道具/剧情点：${terms}。`,
    `全局状态参考：${state}。`,
    firstImpacted
      ? `优先优化 ${firstImpacted} 的开头钩子、上集承接、人物动机和全局剧情点。`
      : "后续轮次生成时必须吸收该人工改稿，不要回到旧稿走向。",
  ].join("\n");
}

function reviewPayload(input: {
  status: string;
  source: string;
  upstreamEpisodeNumber?: number;
  continuityInstruction?: string | null;
  llmModel?: string | null;
  error?: string | null;
}) {
  return JSON.stringify(
    {
      ...input,
      updatedAt: new Date().toISOString(),
    },
    null,
    2
  );
}

async function updateManualEditLedger(
  projectId: string,
  entry: ManualEditLedgerEntry
): Promise<void> {
  await updateProjectMeta(projectId, (meta) => {
    const existingEntries = meta.control?.manualEditLedger?.entries ?? [];
    const entries = [
      ...existingEntries.filter(
        (item) =>
          !(
            item.episodeId === entry.episodeId &&
            item.episodeNumber === entry.episodeNumber
          )
      ),
      entry,
    ].slice(-20);
    return {
      ...meta,
      control: {
        ...(meta.control ?? {}),
        manualEditLedger: { entries },
      },
    };
  });
}

async function orderedProjectEpisodes(projectId: string): Promise<EpisodeRow[]> {
  return db.query.episodes.findMany({
    where: eq(schema.episodes.projectId, projectId),
    orderBy: [asc(schema.episodes.epNum)],
  });
}

export async function applyEpisodeEditImpact({
  project,
  round,
  bible,
  episode,
  episodes,
  editedScriptText,
  optimizeImpacted = false,
  llmModel,
  maxOptimizedEpisodes = 3,
  optimizer = optimizeEpisodeScript,
}: {
  project: ProjectRow;
  round: RoundRow | null | undefined;
  bible: BibleRow | null | undefined;
  episode: EpisodeRow;
  episodes: EpisodeRow[];
  editedScriptText?: string | null;
  optimizeImpacted?: boolean;
  llmModel?: string | null;
  maxOptimizedEpisodes?: number;
  optimizer?: Optimizer;
}): Promise<AppliedEditImpactResult> {
  const roundSummary = parseRoundSummary(round?.summaryJson);
  const report = analyzeEpisodeEditImpact({
    episode,
    episodes,
    roundSummary,
    editedScriptText,
  });
  const edited = editedScriptText ?? episode.scriptTxt ?? "";
  if (!report.changed) {
    return {
      report,
      applied: false,
      continuityInstruction: null,
      optimizedEpisodes: [],
    };
  }

  const now = new Date();
  const continuityInstruction = buildContinuityInstruction(report, edited);
  await db
    .update(schema.episodes)
    .set({
      scriptTxt: edited,
      draftMd: edited,
      status: "red",
      reviewJson: reviewPayload({
        status: "needs_human_review",
        source: "operator_script_edit",
        continuityInstruction,
      }),
      updatedAt: now,
    })
    .where(eq(schema.episodes.id, episode.id));
  await writeEpisodeTxt(project.id, episode.epNum, edited);

  await updateManualEditLedger(project.id, {
    episodeId: episode.id,
    episodeNumber: episode.epNum,
    updatedAt: now.toISOString(),
    changeSummary: report.changeSummary,
    touchedTerms: report.touchedTerms,
    impactedEpisodes: report.impactedEpisodes.map((item) => item.epNum),
    editedTail: lastMeaningfulLines(edited),
    continuityInstruction,
  });

  const optimizedEpisodes: AppliedImpactEpisode[] = [];
  if (optimizeImpacted) {
    let latestEpisodes = episodes.map((item) =>
      item.id === episode.id ? { ...item, scriptTxt: edited, draftMd: edited } : item
    );
    const impactedTargets = report.impactedEpisodes
      .filter((item) => item.hasScript)
      .slice(0, maxOptimizedEpisodes);
    for (const target of impactedTargets) {
      const targetEpisode = latestEpisodes.find((item) => item.id === target.id);
      if (!targetEpisode?.scriptTxt) continue;
      try {
        const optimized = await optimizer({
          project,
          round,
          bible,
          episodes: latestEpisodes,
          episode: targetEpisode,
          llmModel,
          instruction: [
            continuityInstruction,
            `本集被影响原因：${target.reason}`,
            "请只优化本集，重点处理：开头钩子是否承接上集新结尾、人物知情状态是否更新、道具/伏笔/全局剧情点是否一致、台词是否自然。",
            "不要重写成另一条故事线，不要改变用户已经修改过的上一集事实。",
          ].join("\n"),
        });
        await db
          .update(schema.episodes)
          .set({
            scriptTxt: optimized.scriptText,
            draftMd: optimized.scriptText,
            status: "red",
            reviewJson: reviewPayload({
              status: "needs_human_review",
              source: "upstream_user_edit",
              upstreamEpisodeNumber: episode.epNum,
              continuityInstruction,
              llmModel: optimized.llmModel,
            }),
            retryCount: targetEpisode.retryCount + 1,
            updatedAt: new Date(),
          })
          .where(eq(schema.episodes.id, targetEpisode.id));
        await writeEpisodeTxt(project.id, targetEpisode.epNum, optimized.scriptText);
        optimizedEpisodes.push({
          id: targetEpisode.id,
          epNum: targetEpisode.epNum,
          status: "optimized",
          message: "已按用户改稿优化承接",
        });
        latestEpisodes = await orderedProjectEpisodes(project.id);
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        await db
          .update(schema.episodes)
          .set({
            status: "red",
            reviewJson: reviewPayload({
              status: "needs_human_review",
              source: "upstream_user_edit",
              upstreamEpisodeNumber: episode.epNum,
              continuityInstruction,
              error: message,
            }),
            updatedAt: new Date(),
          })
          .where(eq(schema.episodes.id, target.id));
        optimizedEpisodes.push({
          id: target.id,
          epNum: target.epNum,
          status: "failed",
          message,
        });
      }
    }
  }

  return {
    report,
    applied: true,
    continuityInstruction,
    optimizedEpisodes,
  };
}
