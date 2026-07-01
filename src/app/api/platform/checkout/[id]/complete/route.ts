import { NextRequest, NextResponse } from "next/server";
import { completeCreditCheckoutSession } from "@/lib/platform-credits";
import { platformHeaders, resolvePlatformContext } from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const context = await resolvePlatformContext(req);
    const { id } = await params;
    const overview = await completeCreditCheckoutSession(context, id);
    return NextResponse.json(overview, {
      headers: platformHeaders(context),
    });
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    return NextResponse.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 400 }
    );
  }
}
