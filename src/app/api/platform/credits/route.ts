import { NextRequest, NextResponse } from "next/server";
import { getBillingOverview } from "@/lib/platform-billing";
import { getCreditOverview } from "@/lib/platform-credits";
import { platformHeaders, resolvePlatformContext } from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";

export async function GET(req: NextRequest) {
  try {
    const context = await resolvePlatformContext(req);
    await getBillingOverview(context);
    return NextResponse.json(await getCreditOverview(context), {
      headers: platformHeaders(context),
    });
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}
