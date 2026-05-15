import Link from "next/link";
import { desc } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export const dynamic = "force-dynamic";

export default async function Home() {
  const projects = await db.query.projects.findMany({
    orderBy: [desc(schema.projects.createdAt)],
  });

  return (
    <main className="max-w-4xl mx-auto p-8 space-y-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Novel-to-Drama</h1>
        <Link href="/projects/new">
          <Button>新建项目</Button>
        </Link>
      </header>

      {projects.length === 0 ? (
        <p className="text-gray-500">还没有项目。点上方「新建项目」开始。</p>
      ) : (
        <ul className="space-y-3">
          {projects.map((p) => (
            <li key={p.id}>
              <Link href={`/projects/${p.id}/bible`}>
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
