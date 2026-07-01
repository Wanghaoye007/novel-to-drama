import { eq, asc } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { notFound } from "next/navigation";
import { Card } from "@/components/ui/card";

export const dynamic = "force-dynamic";

export default async function CompletePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, id),
  });
  if (!project) notFound();

  const episodes = await db.query.episodes.findMany({
    where: eq(schema.episodes.projectId, id),
    orderBy: [asc(schema.episodes.epNum)],
  });

  const greenCount = episodes.filter((e) => e.status === "green").length;
  const redCount = episodes.filter((e) => e.status === "red").length;
  const failedCount = episodes.filter((e) => e.status === "failed").length;

  return (
    <main className="max-w-4xl mx-auto p-8 space-y-6">
      <h1 className="text-2xl font-bold">{project.name} · 完成</h1>
      <Card className="p-4">
        <p className="text-sm">总集数：{episodes.length}</p>
        <p className="text-sm text-green-600">通过 (绿)：{greenCount}</p>
        <p className="text-sm text-red-600">红标：{redCount}</p>
        <p className="text-sm text-gray-500">失败：{failedCount}</p>
      </Card>
      <a
        href={`/api/projects/${id}/export`}
        className="inline-block px-4 py-2 bg-black text-white rounded font-medium"
      >
        下载项目 zip
      </a>
    </main>
  );
}
