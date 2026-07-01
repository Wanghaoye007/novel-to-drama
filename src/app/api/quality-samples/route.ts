import { NextRequest, NextResponse } from "next/server";
import {
  getQualitySampleEvaluation,
  startQualitySampleEvaluation,
} from "@/lib/engine-runner";
import { kickJobWorker } from "@/lib/job-worker";
import {
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";
import { recordUsageEvent } from "@/lib/platform-usage";

export async function GET(req: NextRequest) {
  try {
    const context = await resolvePlatformContext(req);
    return NextResponse.json(
      await getQualitySampleEvaluation(context.tenant.id),
      { headers: platformHeaders(context) }
    );
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    return NextResponse.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 500 }
    );
  }
}

export async function POST(req: NextRequest) {
  try {
    const context = await resolvePlatformContext(req);
    const body = (await req.json().catch(() => ({}))) as { rounds?: number };
    const rounds = Number.isFinite(body.rounds) ? Number(body.rounds) : 2;
    const payload = await startQualitySampleEvaluation(rounds, context.tenant.id);
    kickJobWorker();
    await recordUsageEvent({
      context,
      eventType: "quality_samples_start",
      metadata: { rounds },
    });
    return NextResponse.json(payload, { headers: platformHeaders(context) });
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    return NextResponse.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 500 }
    );
  }
}
