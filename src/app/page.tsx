import Link from "next/link";
import { desc, eq, inArray } from "drizzle-orm";
import { KeyRound, ShieldCheck } from "lucide-react";
import { db, schema } from "@/db/client";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { resolvePlatformPageContext } from "@/lib/platform-page-context";
import { WorkspaceSessionClient } from "./platform/WorkspaceSessionClient";

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
    <main className="max-w-4xl mx-auto p-8 space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Novel-to-Drama</h1>
          <p className="text-sm text-gray-500">
            {context.tenant.name} · {context.user.email}
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/platform">
            <Button variant="outline">
              <KeyRound className="size-4" />
              平台设置
            </Button>
          </Link>
          <Link href="/quality">
            <Button variant="outline">
              <ShieldCheck className="size-4" />
              内部回归
            </Button>
          </Link>
          <Link href="/projects/new">
            <Button>新建项目</Button>
          </Link>
        </div>
      </header>

      <WorkspaceSessionClient session={session} compact />

      {projects.length === 0 ? (
        <p className="text-gray-500">还没有项目。点上方「新建项目」开始。</p>
      ) : (
        <ul className="space-y-3">
          {projects.map((p) => (
            <li key={p.id}>
              <Link
                href={
                  latestRoundByProject.has(p.id)
                    ? `/projects/${p.id}/rounds/${latestRoundByProject.get(p.id)}`
                    : `/projects/${p.id}/bible`
                }
              >
                <Card className="p-4 hover:bg-gray-50 transition">
                  <div className="flex justify-between items-center">
                    <div>
                      <h2 className="font-medium">{p.name}</h2>
                      <p className="text-sm text-gray-500">
                        目标 {p.targetEpisodeCount} 集 ·{" "}
                        {new Date(p.createdAt).toLocaleString()}
                      </p>
                    </div>
                    <Badge>{p.status}</Badge>
                  </div>
                </Card>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
