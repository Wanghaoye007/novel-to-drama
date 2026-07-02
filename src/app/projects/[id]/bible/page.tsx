import { eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { notFound } from "next/navigation";
import Link from "next/link";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { findTenantProject } from "@/lib/platform-context";
import { resolvePlatformPageContext } from "@/lib/platform-page-context";
import { BibleClient } from "./BibleClient";

export const dynamic = "force-dynamic";

export default async function BiblePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { context } = await resolvePlatformPageContext();
  const project = await findTenantProject(id, context.tenant.id);
  if (!project) notFound();

  const bible = await db.query.bibles.findFirst({
    where: eq(schema.bibles.projectId, id),
  });
  if (!bible) {
    return (
      <section className="page-shell page-shell-narrow">
        <header>
          <div className="page-kicker">系统生成中</div>
          <h1 className="page-title">{project.name} · 系统 Bible</h1>
        </header>
        <Card className="p-5 text-sm text-muted-foreground">
          系统正在生成第一轮，Bible 会在轮次完成后写入。
        </Card>
        <Link href={`/projects/${id}/rounds/1`}>
          <Button variant="outline">查看第 1 轮</Button>
        </Link>
      </section>
    );
  }
  return <BibleClient project={project} bible={bible} />;
}
