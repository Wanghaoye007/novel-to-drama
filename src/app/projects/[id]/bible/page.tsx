import { eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { notFound } from "next/navigation";
import { BibleClient } from "./BibleClient";

export const dynamic = "force-dynamic";

export default async function BiblePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, id),
  });
  const bible = await db.query.bibles.findFirst({
    where: eq(schema.bibles.projectId, id),
  });
  if (!project || !bible) notFound();
  return <BibleClient project={project} bible={bible} />;
}
