import { NextRequest, NextResponse } from "next/server";
import { createHmac, timingSafeEqual } from "crypto";
import { processPaymentWebhook } from "@/lib/platform-credits";

export const runtime = "nodejs";

function webhookSecret(): string | null {
  const value =
    process.env.PLATFORM_PAYMENT_WEBHOOK_SECRET ??
    process.env.NOVEL_DRAMA_PAYMENT_WEBHOOK_SECRET ??
    "";
  return value.trim() || null;
}

function signatureHeader(req: NextRequest): string | null {
  return (
    req.headers.get("x-novel-drama-signature") ??
    req.headers.get("x-webhook-signature") ??
    req.headers.get("x-signature") ??
    null
  );
}

function normalizeSignature(value: string | null): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  const normalized = trimmed.startsWith("sha256=")
    ? trimmed.slice("sha256=".length)
    : trimmed;
  return /^[a-f0-9]{64}$/i.test(normalized) ? normalized.toLowerCase() : null;
}

function verifyWebhookSignature(req: NextRequest, rawBody: string): boolean {
  const secret = webhookSecret();
  if (!secret) {
    throw new Error("payment webhook secret is not configured; unsigned webhooks are rejected");
  }
  const provided = normalizeSignature(signatureHeader(req));
  if (!provided) {
    throw new Error("missing or invalid payment webhook signature");
  }
  const expected = createHmac("sha256", secret).update(rawBody).digest("hex");
  const providedBuffer = Buffer.from(provided, "hex");
  const expectedBuffer = Buffer.from(expected, "hex");
  if (
    providedBuffer.length !== expectedBuffer.length ||
    !timingSafeEqual(providedBuffer, expectedBuffer)
  ) {
    throw new Error("payment webhook signature mismatch");
  }
  return true;
}

export async function POST(req: NextRequest) {
  const rawBody = await req.text();
  try {
    const body = JSON.parse(rawBody || "{}") as {
      provider?: "mock" | "stripe" | "wechat_pay" | "alipay" | "manual";
      eventType?: string;
      checkoutSessionId?: string;
      externalEventId?: string;
    };
    const signatureVerified = verifyWebhookSignature(req, rawBody);
    return NextResponse.json(
      await processPaymentWebhook({
        ...body,
        signatureVerified,
        raw: {
          ...body,
          signatureVerified,
        },
      })
    );
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 400 }
    );
  }
}
