import { NextResponse } from "next/server";
import { getOpsJobDetail, OpsConsoleError } from "@/lib/ops-console";
import { platformHeaders, resolvePlatformContext } from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";

export const dynamic = "force-dynamic";

export async function GET(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const context = await resolvePlatformContext(req);
    const { id } = await params;
    return NextResponse.json(await getOpsJobDetail(context, id), {
      headers: { ...platformHeaders(context), "Cache-Control": "no-store" },
    });
  } catch (error) {
    if (error instanceof OpsConsoleError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}
