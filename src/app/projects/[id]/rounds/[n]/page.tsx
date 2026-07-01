import { eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { notFound } from "next/navigation";
import { RoundClient } from "./RoundClient";

export const dynamic = "force-dynamic";

export default async function RoundPage({
  params,
}: {
  params: Promise<{ id: string; n: string }>;
}) {
  const { id, n } = await params;
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, id),
  });
  if (!project) notFound();
  return (
    <RoundClient
      projectId={id}
      roundNum={parseInt(n)}
      project={project}
    />
  );
}
