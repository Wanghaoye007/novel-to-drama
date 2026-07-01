import { NextRequest, NextResponse } from "next/server";
import { desc, eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { startEngineRound } from "@/lib/engine-runner";

export async function POST(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, id),
  });
  if (!project) return NextResponse.json({ error: "not found" }, { status: 404 });

  const existing = await db.query.rounds.findMany({
    where: eq(schema.rounds.projectId, id),
    orderBy: [desc(schema.rounds.roundNum)],
  });
  const roundNum = (existing[0]?.roundNum ?? 0) + 1;

  await startEngineRound(id, roundNum);

  return NextResponse.json({ roundNum, status: "started" });
}
