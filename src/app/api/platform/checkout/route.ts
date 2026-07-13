import { NextRequest, NextResponse } from "next/server";
import { createCreditCheckoutSession } from "@/lib/platform-credits";
import { platformHeaders, resolvePlatformContext } from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";

export async function POST(req: NextRequest) {
  try {
    const context = await resolvePlatformContext(req);
    const body = (await req.json().catch(() => ({}))) as {
      packageSlug?: string;
      provider?: "mock" | "stripe" | "wechat_pay" | "alipay" | "manual";
    };
    if (!body.packageSlug) {
      return NextResponse.json(
        { error: "missing packageSlug" },
        { status: 400 }
      );
    }
    const session = await createCreditCheckoutSession(
      context,
      body.packageSlug,
      body.provider ?? "mock"
    );
    return NextResponse.json(session, {
      status: 201,
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
