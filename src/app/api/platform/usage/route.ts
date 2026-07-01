import { NextRequest, NextResponse } from "next/server";
import { platformHeaders, resolvePlatformContext } from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";
import { getUsageSummary } from "@/lib/platform-usage";

function parseSince(value: string | null): Date | undefined {
  if (!value) return undefined;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? undefined : date;
}

export async function GET(req: NextRequest) {
  try {
    const context = await resolvePlatformContext(req);
    const since = parseSince(req.nextUrl.searchParams.get("since"));
    return NextResponse.json(await getUsageSummary(context, since), {
      headers: platformHeaders(context),
    });
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}
