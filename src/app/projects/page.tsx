import Link from "next/link";
import { and, desc, eq } from "drizzle-orm";
import {
  ArrowRight,
  Clock3,
  FileText,
  FolderKanban,
  Plus,
  Sparkles,
} from "lucide-react";
import { ProjectCloneButton, ProjectManageButton } from "@/app/ProjectActionsClient";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { db, schema } from "@/db/client";
import { resolvePlatformPageContext } from "@/lib/platform-page-context";

export const dynamic = "force-dynamic";

type ProjectRow = typeof schema.projects.$inferSelect;
type RoundRow = typeof schema.rounds.$inferSelect;
type EpisodeRow = typeof schema.episodes.$inferSelect;

type ProjectListItem = {
  project: ProjectRow;
  latestRound: RoundRow | null;
  episodes: EpisodeRow[];
};

const statusCopy: Record<string, { label: string; tone: "neutral" | "busy" | "done" | "issue" }> = {
  draft: { label: "待启动", tone: "neutral" },
  bible_ready: { label: "Bible 已就绪", tone: "neutral" },
  running: { label: "生成中", tone: "busy" },
  paused: { label: "已暂停", tone: "issue" },
  done: { label: "已完成", tone: "done" },
  failed: { label: "失败", tone: "issue" },
};

function formatDate(value: Date): string {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(value);
}

function projectHref(item: ProjectListItem): string {
  if (item.project.status === "done") return `/projects/${item.project.id}/complete`;
  return `/projects/${item.project.id}/rounds/${item.latestRound?.roundNum ?? 1}`;
}

async function loadProjectItems(
  tenantId: string,
  ownerUserId: string
): Promise<ProjectListItem[]> {
  const projects = await db.query.projects.findMany({
    where: and(
      eq(schema.projects.tenantId, tenantId),
      eq(schema.projects.ownerUserId, ownerUserId)
    ),
    orderBy: [desc(schema.projects.updatedAt)],
  });

  return Promise.all(
    projects.map(async (project) => {
      const [latestRound, episodes] = await Promise.all([
        db.query.rounds.findFirst({
          where: eq(schema.rounds.projectId, project.id),
          orderBy: [desc(schema.rounds.roundNum)],
        }),
        db.query.episodes.findMany({
          where: eq(schema.episodes.projectId, project.id),
          orderBy: [desc(schema.episodes.updatedAt)],
        }),
      ]);
      return { project, latestRound: latestRound ?? null, episodes };
    })
  );
}

export default async function ProjectsPage() {
  const { context, session } = await resolvePlatformPageContext();
  const items = await loadProjectItems(context.tenant.id, context.user.id);
  const runningCount = items.filter((item) => item.project.status === "running").length;
  const doneCount = items.filter((item) => item.project.status === "done").length;
  const reviewCount = items.reduce(
    (total, item) => total + item.episodes.filter((episode) => episode.status === "red").length,
    0
  );

  return (
    <section className="page-shell workspace-shell">
      <header className="workspace-hero">
        <div className="workspace-hero-copy">
          <div className="page-kicker">Ops Workspace · {session.tenantSlug}</div>
          <h1>改编项目工作台</h1>
          <p>
            按项目继续轮次、复核问题、导出成品。这里是运营同学的主入口，已上传和已改编的内容都会回到这里。
          </p>
        </div>
        <Button asChild size="lg">
          <Link href="/projects/new">
            <Plus className="size-4" />
            新建改编
          </Link>
        </Button>
      </header>

      <div className="workspace-metrics" aria-label="项目概览">
        <Card className="workspace-metric-card">
          <FolderKanban className="size-4" />
          <span>全部项目</span>
          <strong>{items.length}</strong>
        </Card>
        <Card className="workspace-metric-card">
          <Sparkles className="size-4" />
          <span>生成中</span>
          <strong>{runningCount}</strong>
        </Card>
        <Card className="workspace-metric-card">
          <FileText className="size-4" />
          <span>待复核集</span>
          <strong>{reviewCount}</strong>
        </Card>
        <Card className="workspace-metric-card">
          <Clock3 className="size-4" />
          <span>已完成</span>
          <strong>{doneCount}</strong>
        </Card>
      </div>

      {items.length === 0 ? (
        <Card className="workspace-empty">
          <div className="workspace-empty-icon">
            <FileText className="size-5" />
          </div>
          <h2>还没有改编项目</h2>
          <p>上传 txt/docx 小说后，系统会自动生成 Story Bible、第 1 轮脚本和质量状态。</p>
          <Button asChild>
            <Link href="/projects/new">
              <Plus className="size-4" />
              创建第一个项目
            </Link>
          </Button>
        </Card>
      ) : (
        <div className="workspace-project-list">
          {items.map((item) => {
            const status = statusCopy[item.project.status] ?? {
              label: item.project.status,
              tone: "neutral" as const,
            };
            const outputCount = item.episodes.filter((episode) => episode.scriptTxt).length;
            const latestScore =
              item.episodes.find((episode) => typeof episode.score === "number")?.score ?? null;
            const failedCount = item.episodes.filter((episode) => episode.status === "failed").length;
            const redCount = item.episodes.filter((episode) => episode.status === "red").length;
            return (
              <Card key={item.project.id} className="workspace-project-card">
                <div className="workspace-project-main">
                  <div className="workspace-project-title-row">
                    <Badge data-tone={status.tone}>{status.label}</Badge>
                    <span>Round {item.latestRound?.roundNum ?? 1}</span>
                    <span>{formatDate(item.project.updatedAt)}</span>
                  </div>
                  <h2>{item.project.name}</h2>
                  <div className="workspace-project-facts">
                    <span>
                      已输出 <b>{outputCount}</b>/{item.project.targetEpisodeCount} 集
                    </span>
                    <span>
                      待复核 <b>{redCount}</b>
                    </span>
                    <span>
                      失败 <b>{failedCount}</b>
                    </span>
                    <span>
                      均分 <b>{latestScore == null ? "-" : latestScore.toFixed(1)}</b>
                    </span>
                  </div>
                </div>
                <div className="workspace-project-actions">
                  <ProjectCloneButton projectId={item.project.id} />
                  <ProjectManageButton
                    projectId={item.project.id}
                    projectName={item.project.name}
                    targetEpisodeCount={item.project.targetEpisodeCount}
                    status={item.project.status}
                    deleteRedirectHref="/projects"
                  />
                  <Button asChild>
                    <Link href={projectHref(item)}>
                      进入项目
                      <ArrowRight className="size-4" />
                    </Link>
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </section>
  );
}
