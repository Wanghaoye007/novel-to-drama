import { NextRequest, NextResponse } from "next/server";
import { eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { runRound } from "@/lib/round-runner";

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
  });
  const roundNum = existing.length + 1;

  // Fire and forget — worker runs in same Node process, user polls for progress
  runRound(id, roundNum).catch((e) => {
    console.error("[round-runner] failed:", e);
  });

  return NextResponse.json({ roundNum, status: "started" });
}
