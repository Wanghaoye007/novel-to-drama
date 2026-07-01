import { NextRequest, NextResponse } from "next/server";
import { v4 as uuid } from "uuid";
import { desc } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { normalizeNovel } from "@/lib/m1-normalize";
import { startEngineRound } from "@/lib/engine-runner";

export async function GET() {
  const list = await db.query.projects.findMany({
    orderBy: [desc(schema.projects.createdAt)],
  });
  return NextResponse.json(list);
}

export async function POST(req: NextRequest) {
  const form = await req.formData();
  const name = form.get("name") as string;
  const targetEpStr = form.get("targetEpisodeCount") as string;
  const file = form.get("file") as File;
  if (!name || !file) {
    return NextResponse.json({ error: "missing fields" }, { status: 400 });
  }
  const targetEpisodeCount = parseInt(targetEpStr || "30", 10);

  const buffer = Buffer.from(await file.arrayBuffer());
  const { text, meta } = await normalizeNovel(file.name, buffer);

  const projectId = uuid();
  const now = new Date();

  await db.insert(schema.projects).values({
    id: projectId,
    name,
    pipelineType: "A",
    novelText: text,
    metaJson: JSON.stringify(meta),
    targetEpisodeCount,
    status: "running",
    createdAt: now,
    updatedAt: now,
  });

  await startEngineRound(projectId, 1);

  return NextResponse.json({ id: projectId, roundNum: 1 });
}
