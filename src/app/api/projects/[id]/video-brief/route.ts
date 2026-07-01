import { NextRequest, NextResponse } from "next/server";
import { exportVideoBrief } from "@/lib/engine-runner";
import {
  findTenantProject,
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const context = await resolvePlatformContext(req);
  const project = await findTenantProject(id, context.tenant.id);
  if (!project) return NextResponse.json({ error: "not found" }, { status: 404 });

  const round = req.nextUrl.searchParams.get("round");
  try {
    const paths = await exportVideoBrief(
      id,
      round ? Number.parseInt(round, 10) : undefined
    );
    return NextResponse.json(paths, { headers: platformHeaders(context) });
  } catch (error) {
    return new Response(error instanceof Error ? error.message : String(error), {
      status: 400,
    });
  }
}
