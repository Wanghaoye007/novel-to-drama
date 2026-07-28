import { NextResponse } from "next/server";
import { kickJobWorker } from "@/lib/job-worker";
import {
  OpsConsoleError,
  retryOpsJob,
  toOpsJobActionResult,
} from "@/lib/ops-console";
import { platformHeaders, resolvePlatformContext } from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";

export async function POST(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const context = await resolvePlatformContext(req);
    const { id } = await params;
    const job = await retryOpsJob(context, id);
    kickJobWorker();
    return NextResponse.json(
      { status: "queued", job: toOpsJobActionResult(job) },
      { headers: platformHeaders(context) }
    );
  } catch (error) {
    if (error instanceof OpsConsoleError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}
