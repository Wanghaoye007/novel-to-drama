import { NextRequest } from "next/server";
import fs from "fs/promises";
import { eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { buildProjectZip, writeBibleMd } from "@/lib/m6-export";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, id),
  });
  const bible = await db.query.bibles.findFirst({
    where: eq(schema.bibles.projectId, id),
  });
  if (!project || !bible) return new Response("not found", { status: 404 });

  await writeBibleMd(
    id,
    bible.charactersMd ?? "",
    bible.episodePlanMd ?? "",
    bible.sixAssetsJson ?? "{}"
  );
  const zipPath = await buildProjectZip(id, project.name);
  const buf = await fs.readFile(zipPath);
  return new Response(new Uint8Array(buf), {
    headers: {
      "Content-Type": "application/zip",
      "Content-Disposition": `attachment; filename="${project.name}.zip"`,
    },
  });
}
