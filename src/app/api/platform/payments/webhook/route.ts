import { NextRequest, NextResponse } from "next/server";
import { processPaymentWebhook } from "@/lib/platform-credits";

export async function POST(req: NextRequest) {
  const body = (await req.json().catch(() => ({}))) as {
    provider?: "mock" | "stripe" | "wechat_pay" | "alipay" | "manual";
    eventType?: string;
    checkoutSessionId?: string;
    externalEventId?: string;
  };
  try {
    return NextResponse.json(
      await processPaymentWebhook({
        ...body,
        raw: body,
      })
    );
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 400 }
    );
  }
}
