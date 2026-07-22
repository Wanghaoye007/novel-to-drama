import { eq, asc, desc } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { notFound } from "next/navigation";
import { Card } from "@/components/ui/card";
import { findTenantProject } from "@/lib/platform-context";
import { resolvePlatformPageContext } from "@/lib/platform-page-context";
import { CompleteActions } from "./CompleteActions";

export const dynamic = "force-dynamic";

type EpisodeRow = typeof schema.episodes.$inferSelect;
type RoundRow = typeof schema.rounds.$inferSelect;

function uniqueStableEpisodes(
  episodes: EpisodeRow[],
  rounds: RoundRow[]
): EpisodeRow[] {
  const roundNumberById = new Map(rounds.map((round) => [round.id, round.roundNum]));
  const stableByEpisode = new Map<number, EpisodeRow>();
  const orderedEpisodes = [...episodes].sort((a, b) => {
    if (a.epNum !== b.epNum) return a.epNum - b.epNum;
    return (roundNumberById.get(a.roundId) ?? 0) - (roundNumberById.get(b.roundId) ?? 0);
  });
  for (const episode of orderedEpisodes) {
    const current = stableByEpisode.get(episode.epNum);
    if (!current || (!current.scriptTxt && episode.scriptTxt)) {
      stableByEpisode.set(episode.epNum, episode);
    }
  }
  return [...stableByEpisode.values()].sort((a, b) => a.epNum - b.epNum);
}

function parseEpisodeReviewStatus(episode: EpisodeRow): string | null {
  if (!episode.reviewJson) return null;
  try {
    const review = JSON.parse(episode.reviewJson) as { status?: string | null };
    return review.status ?? null;
  } catch {
    return null;
  }
}

function episodeStatusLabel(episode: EpisodeRow): string {
  const reviewStatus = parseEpisodeReviewStatus(episode);
  if (episode.status === "green") return "通过";
  if (episode.status === "red" && reviewStatus === "needs_human_review") return "待复核";
  if (episode.status === "red" && reviewStatus === "needs_rewrite") return "需重写";
  if (episode.status === "red" && reviewStatus === "context_conflict") {
    return "上下文冲突";
  }
  if (episode.status === "red") return "需修";
  if (episode.status === "running") return "生成中";
  if (episode.status === "pending") return "等待";
  if (episode.status === "failed") return "失败";
  return episode.status;
}

export default async function CompletePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { context } = await resolvePlatformPageContext();
  const project = await findTenantProject(id, context.tenant.id, context.user.id);
  if (!project) notFound();

  const rounds = await db.query.rounds.findMany({
    where: eq(schema.rounds.projectId, id),
    orderBy: [desc(schema.rounds.roundNum)],
  });
  const rawEpisodes = await db.query.episodes.findMany({
    where: eq(schema.episodes.projectId, id),
    orderBy: [asc(schema.episodes.epNum)],
  });
  const episodes = uniqueStableEpisodes(rawEpisodes, rounds);
  const greenCount = episodes.filter((e) => e.status === "green").length;
  const reviewCount = episodes.filter(
    (e) => e.status === "red" && parseEpisodeReviewStatus(e) === "needs_human_review"
  ).length;
  const redCount = episodes.filter(
    (e) => e.status === "red" && parseEpisodeReviewStatus(e) !== "needs_human_review"
  ).length;
  const failedCount = episodes.filter((e) => e.status === "failed").length;
  const latestRound = rounds[0] ?? null;
  const deliveryExportHref = latestRound
    ? `/api/projects/${id}/export?round=${latestRound.roundNum}&allowIssues=1`
    : `/api/projects/${id}/export?allowIssues=1`;

  return (
    <section className="page-shell">
      <header>
        <div className="page-kicker">交付包已准备</div>
        <h1 className="page-title">{project.name} · 完成</h1>
        <p className="page-description">
          下载交付包后可进入视频 brief、本地化和后续投放制作流程。
        </p>
      </header>
      <Card className="p-5">
        <div className="metric-grid">
          <div className="soft-panel">
            <div className="text-sm text-muted-foreground">总集数</div>
            <div className="metric-value">{episodes.length}</div>
          </div>
          <div className="soft-panel">
            <div className="text-sm text-muted-foreground">通过</div>
            <div className="metric-value text-emerald-700">{greenCount}</div>
          </div>
          <div className="soft-panel">
            <div className="text-sm text-muted-foreground">待复核</div>
            <div className="metric-value text-amber-700">{reviewCount}</div>
          </div>
          <div className="soft-panel">
            <div className="text-sm text-muted-foreground">需修/失败</div>
            <div className="metric-value text-red-700">{redCount + failedCount}</div>
          </div>
        </div>
      </Card>
      <CompleteActions
        projectId={id}
        projectName={project.name}
        latestRoundNum={latestRound?.roundNum ?? 1}
        deliveryExportHref={deliveryExportHref}
      />
      <Card className="complete-script-card">
        <div className="complete-script-head">
          <div>
            <div className="page-kicker">全集脚本</div>
            <h2>按集输出</h2>
          </div>
          <span>
            {episodes.length}/{project.targetEpisodeCount} 集
          </span>
        </div>
        {episodes.length === 0 ? (
          <div className="round-empty">暂无可展示脚本</div>
        ) : (
          <div className="complete-episode-list">
            {episodes.map((episode, index) => (
              <details
                key={episode.id}
                className="complete-episode-item"
                open={index === 0}
              >
                <summary>
                  <b>E{String(episode.epNum).padStart(2, "0")}</b>
                  <span>{episodeStatusLabel(episode)}</span>
                </summary>
                {episode.scriptTxt ? (
                  <pre className="round-script-reader complete-script-reader">{episode.scriptTxt}</pre>
                ) : (
                  <div className="round-empty">本集暂无正文</div>
                )}
              </details>
            ))}
          </div>
        )}
      </Card>
    </section>
  );
}
