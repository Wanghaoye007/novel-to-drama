import { NextResponse } from "next/server";
import { asc, eq } from "drizzle-orm";
import { db, schema } from "@/db/client";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, id),
  });
  if (!project) return NextResponse.json({ error: "not found" }, { status: 404 });

  const bible = await db.query.bibles.findFirst({
    where: eq(schema.bibles.projectId, id),
  });
  const rounds = await db.query.rounds.findMany({
    where: eq(schema.rounds.projectId, id),
    orderBy: [asc(schema.rounds.roundNum)],
  });
  const episodes = await db.query.episodes.findMany({
    where: eq(schema.episodes.projectId, id),
    orderBy: [asc(schema.episodes.epNum)],
  });

  return NextResponse.json({ project, bible, rounds, episodes });
}
