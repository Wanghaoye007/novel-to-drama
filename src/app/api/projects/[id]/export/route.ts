import { NextRequest } from "next/server";
import fs from "fs/promises";
import { exportDeliveryZip } from "@/lib/engine-runner";
import {
  findTenantProject,
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const context = await resolvePlatformContext(_req);
  const project = await findTenantProject(id, context.tenant.id);
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
      ...platformHeaders(context),
      "Content-Type": "application/zip",
      "Content-Disposition": `attachment; filename="${project.name}.zip"`,
    },
  });
}
