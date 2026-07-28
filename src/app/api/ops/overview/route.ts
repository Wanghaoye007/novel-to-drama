import { NextResponse } from "next/server";
import { getOpsOverview } from "@/lib/ops-console";
import { platformHeaders, resolvePlatformContext } from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  try {
    const context = await resolvePlatformContext(req);
    return NextResponse.json(await getOpsOverview(context), {
      headers: { ...platformHeaders(context), "Cache-Control": "no-store" },
    });
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}
