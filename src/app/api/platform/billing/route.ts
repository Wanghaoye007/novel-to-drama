import { NextRequest, NextResponse } from "next/server";
import {
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";
import { getBillingOverview, switchTenantPlan } from "@/lib/platform-billing";

export async function GET(req: NextRequest) {
  try {
    const context = await resolvePlatformContext(req);
    return NextResponse.json(await getBillingOverview(context), {
      headers: platformHeaders(context),
    });
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}

export async function POST(req: NextRequest) {
  try {
    const context = await resolvePlatformContext(req);
    const body = (await req.json().catch(() => ({}))) as { planSlug?: string };
    if (!body.planSlug) {
      return NextResponse.json({ error: "missing planSlug" }, { status: 400 });
    }
    return NextResponse.json(await switchTenantPlan(context, body.planSlug), {
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
