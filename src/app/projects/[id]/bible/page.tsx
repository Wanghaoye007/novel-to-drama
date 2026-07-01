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
      <main className="max-w-3xl mx-auto p-8 space-y-4">
        <h1 className="text-2xl font-bold">{project.name} · 系统 Bible</h1>
        <Card className="p-4 text-sm text-gray-600">
          系统正在生成第一轮，Bible 会在轮次完成后写入。
        </Card>
        <Link href={`/projects/${id}/rounds/1`}>
          <Button variant="outline">查看第 1 轮</Button>
        </Link>
      </main>
    );
  }
  return <BibleClient project={project} bible={bible} />;
}
