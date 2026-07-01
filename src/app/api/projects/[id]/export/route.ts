import { NextRequest } from "next/server";
import fs from "fs/promises";
import { exportDeliveryZip } from "@/lib/engine-runner";
import {
  findTenantProject,
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";
import { recordUsageEvent } from "@/lib/platform-usage";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
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
    await recordUsageEvent({
      context,
      eventType: "delivery_export",
      projectId: id,
      metadata: {
        round: round ? Number.parseInt(round, 10) : null,
        allowIssues,
      },
    });
    const buf = await fs.readFile(zipPath);
    return new Response(new Uint8Array(buf), {
      headers: {
        ...platformHeaders(context),
        "Content-Type": "application/zip",
        "Content-Disposition": `attachment; filename="${project.name}.zip"`,
      },
    });
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}
