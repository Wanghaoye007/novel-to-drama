import { eq, asc, desc } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { notFound } from "next/navigation";
import Link from "next/link";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { findTenantProject } from "@/lib/platform-context";
import { resolvePlatformPageContext } from "@/lib/platform-page-context";

export const dynamic = "force-dynamic";

export default async function CompletePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { context } = await resolvePlatformPageContext();
  const project = await findTenantProject(id, context.tenant.id);
  if (!project) notFound();

  const episodes = await db.query.episodes.findMany({
    where: eq(schema.episodes.projectId, id),
    orderBy: [asc(schema.episodes.epNum)],
  });

  const greenCount = episodes.filter((e) => e.status === "green").length;
  const redCount = episodes.filter((e) => e.status === "red").length;
  const failedCount = episodes.filter((e) => e.status === "failed").length;
  const latestRound = await db.query.rounds.findFirst({
    where: eq(schema.rounds.projectId, id),
    orderBy: [desc(schema.rounds.roundNum)],
  });
  const roundParam = latestRound ? `?round=${latestRound.roundNum}` : "";

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
            <div className="text-sm text-muted-foreground">红标</div>
            <div className="metric-value text-red-700">{redCount}</div>
          </div>
          <div className="soft-panel">
            <div className="text-sm text-muted-foreground">失败</div>
            <div className="metric-value">{failedCount}</div>
          </div>
        </div>
      </Card>
      <div className="flex gap-2">
        <Button asChild>
          <a href={`/api/projects/${id}/export${roundParam}`}>下载交付包</a>
        </Button>
        <Button asChild variant="outline">
          <Link href={`/projects/${id}/bible`}>系统 Bible</Link>
        </Button>
      </div>
    </section>
  );
}
