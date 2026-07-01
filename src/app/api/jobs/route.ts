import { NextRequest, NextResponse } from "next/server";
import { listJobViews, type JobKind } from "@/lib/jobs";
import { platformHeaders, resolvePlatformContext } from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";

const jobKinds: JobKind[] = ["round_generation", "quality_samples"];

function parseKind(value: string | null): JobKind | undefined {
  if (!value) return undefined;
  return jobKinds.includes(value as JobKind) ? (value as JobKind) : undefined;
}

export async function GET(req: NextRequest) {
  try {
    const context = await resolvePlatformContext(req);
    const projectId = req.nextUrl.searchParams.get("projectId") ?? undefined;
    const kind = parseKind(req.nextUrl.searchParams.get("kind"));
    const limitRaw = req.nextUrl.searchParams.get("limit");
    const limit = limitRaw ? Number.parseInt(limitRaw, 10) : 20;
    return NextResponse.json(
      await listJobViews({
        tenantId: context.tenant.id,
        projectId,
        kind,
        limit,
      }),
      { headers: platformHeaders(context) }
    );
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}
