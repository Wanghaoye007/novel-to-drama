import { NextRequest } from "next/server";
import fs from "fs/promises";
import { eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { exportDeliveryZip } from "@/lib/engine-runner";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, id),
  });
  if (!project) return new Response("not found", { status: 404 });

  const round = _req.nextUrl.searchParams.get("round");
  const allowIssues = _req.nextUrl.searchParams.get("allowIssues") === "1";
  const zipPath = await exportDeliveryZip(
    id,
    round ? Number.parseInt(round, 10) : undefined,
    allowIssues
  );
  const buf = await fs.readFile(zipPath);
  return new Response(new Uint8Array(buf), {
    headers: {
      "Content-Type": "application/zip",
      "Content-Disposition": `attachment; filename="${project.name}.zip"`,
    },
  });
}
