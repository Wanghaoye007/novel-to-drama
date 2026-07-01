import { NextRequest, NextResponse } from "next/server";
import { exportVideoBrief } from "@/lib/engine-runner";
import {
  findTenantProject,
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";
import { recordUsageEvent } from "@/lib/platform-usage";

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const context = await resolvePlatformContext(req);
    const project = await findTenantProject(id, context.tenant.id);
    if (!project) return NextResponse.json({ error: "not found" }, { status: 404 });

    const round = req.nextUrl.searchParams.get("round");
    const paths = await exportVideoBrief(
      id,
      round ? Number.parseInt(round, 10) : undefined
    );
    await recordUsageEvent({
      context,
      eventType: "video_brief_export",
      projectId: id,
      metadata: { round: round ? Number.parseInt(round, 10) : null },
    });
    return NextResponse.json(paths, { headers: platformHeaders(context) });
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    return new Response(error instanceof Error ? error.message : String(error), {
      status: 400,
    });
  }
}
