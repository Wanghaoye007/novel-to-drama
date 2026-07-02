import Link from "next/link";
import { desc, eq, inArray } from "drizzle-orm";
import { ArrowUpRight, FileText, Layers3, PlusCircle } from "lucide-react";
import { db, schema } from "@/db/client";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { resolvePlatformPageContext } from "@/lib/platform-page-context";
import { WorkspaceSessionClient } from "./platform/WorkspaceSessionClient";
import { ProjectCloneButton } from "./ProjectActionsClient";

export const dynamic = "force-dynamic";

export default async function Home() {
  const { context, session } = await resolvePlatformPageContext();
  const projects = await db.query.projects.findMany({
    where: eq(schema.projects.tenantId, context.tenant.id),
    orderBy: [desc(schema.projects.createdAt)],
  });
  const projectIds = projects.map((project) => project.id);
  const rounds = projectIds.length
    ? await db.query.rounds.findMany({
        where: inArray(schema.rounds.projectId, projectIds),
        orderBy: [desc(schema.rounds.roundNum)],
      })
    : [];
  const latestRoundByProject = new Map<string, number>();
  for (const round of rounds) {
    if (!latestRoundByProject.has(round.projectId)) {
      latestRoundByProject.set(round.projectId, round.roundNum);
    }
  }

  return (
    <section className="page-shell">
      <header className="page-header">
        <div>
          <div className="page-kicker">
            {context.tenant.name} · {context.user.email}
          </div>
          <h1 className="page-title">项目工作台</h1>
          <p className="page-description">
            上传小说后，系统自动完成 Story Bible、轮次上下文、分集脚本、交付包和本地化素材。
          </p>
        </div>
        <Link href="/projects/new">
          <Button size="lg">
            <PlusCircle className="size-4" />
            新建改编
          </Button>
        </Link>
      </header>

      <section className="metric-grid">
        <div className="metric-card">
          <div className="metric-label">
            <FileText className="size-4" />
            当前项目
          </div>
          <div className="metric-value">{projects.length}</div>
          <p className="mt-2 text-xs text-muted-foreground">
            当前工作区全部改编项目
          </p>
        </div>
        <div className="metric-card">
          <div className="metric-label">
            <Layers3 className="size-4" />
            已生成轮次
          </div>
          <div className="metric-value">{rounds.length}</div>
          <p className="mt-2 text-xs text-muted-foreground">
            包含运行中、完成和失败任务
          </p>
        </div>
      </section>

      <WorkspaceSessionClient session={session} compact />

      {projects.length === 0 ? (
        <Card className="items-start gap-3 p-8">
          <Badge variant="outline">尚无项目</Badge>
          <div>
            <h2 className="text-xl font-semibold tracking-[-0.01em]">
              从第一本小说开始
            </h2>
            <p className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">
              运营同学只需要上传 txt/docx、填写目标集数，系统会自动启动第 1 轮改编。
            </p>
          </div>
          <Link href="/projects/new">
            <Button>
              <PlusCircle className="size-4" />
              上传小说
            </Button>
          </Link>
        </Card>
      ) : (
        <section className="space-y-3">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold tracking-[-0.01em]">
                最近项目
              </h2>
              <p className="text-sm text-muted-foreground">
                进入项目后可继续下一轮、重试失败任务、导出视频 brief 和本地化包。
              </p>
            </div>
          </div>
          {projects.map((p) => (
            <Card
              key={p.id}
              className="p-5 transition hover:-translate-y-0.5 hover:shadow-[0_22px_50px_rgba(27,27,31,0.1)]"
            >
              <div className="flex items-center justify-between gap-4">
                <Link
                  className="min-w-0 flex-1"
                  href={
                    latestRoundByProject.has(p.id)
                      ? `/projects/${p.id}/rounds/${latestRoundByProject.get(p.id)}`
                      : `/projects/${p.id}/bible`
                  }
                >
                    <div className="min-w-0">
                      <h3 className="truncate text-base font-semibold">
                        {p.name}
                      </h3>
                      <p className="mt-1 text-sm text-muted-foreground">
                        目标 {p.targetEpisodeCount} 集 ·{" "}
                        {new Date(p.createdAt).toLocaleString()}
                      </p>
                    </div>
                </Link>
                <div className="flex items-center gap-3">
                  <Badge>{p.status}</Badge>
                  <ProjectCloneButton projectId={p.id} />
                  <Link
                    href={
                      latestRoundByProject.has(p.id)
                        ? `/projects/${p.id}/rounds/${latestRoundByProject.get(p.id)}`
                        : `/projects/${p.id}/bible`
                    }
                    aria-label={`打开 ${p.name}`}
                  >
                    <ArrowUpRight className="size-4 text-muted-foreground" />
                  </Link>
                </div>
              </div>
            </Card>
          ))}
        </section>
      )}
    </section>
  );
}
