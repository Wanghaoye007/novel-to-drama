import { NextResponse } from "next/server";
import { listOpsJobs } from "@/lib/ops-console";
import type { JobKind, JobStatus } from "@/lib/jobs";
import { platformHeaders, resolvePlatformContext } from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";

const statuses = new Set<JobStatus>([
  "queued",
  "running",
  "succeeded",
  "failed",
  "cancelled",
]);
const kinds = new Set<JobKind>([
  "round_generation",
  "quality_samples",
  "delivery_export",
  "video_brief_export",
  "localization_export",
  "episode_optimize",
  "edit_impact",
]);

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  try {
    const context = await resolvePlatformContext(req);
    const url = new URL(req.url);
    const statusValue = url.searchParams.get("status") as JobStatus | null;
    const kindValue = url.searchParams.get("kind") as JobKind | null;
    const limit = Number.parseInt(url.searchParams.get("limit") ?? "50", 10);
    const jobs = await listOpsJobs(context, {
      status: statusValue && statuses.has(statusValue) ? statusValue : undefined,
      kind: kindValue && kinds.has(kindValue) ? kindValue : undefined,
      query: url.searchParams.get("query") ?? undefined,
      limit: Number.isFinite(limit) ? limit : 50,
    });
    return NextResponse.json(
      { jobs },
      { headers: { ...platformHeaders(context), "Cache-Control": "no-store" } }
    );
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}
