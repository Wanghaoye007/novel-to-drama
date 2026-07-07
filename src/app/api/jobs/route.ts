import { NextRequest, NextResponse } from "next/server";
import { listJobViews, type JobKind } from "@/lib/jobs";
import {
  findTenantProject,
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";

const jobKinds: JobKind[] = [
  "round_generation",
  "quality_samples",
  "delivery_export",
  "video_brief_export",
  "localization_export",
];

function parseKind(value: string | null): JobKind | undefined {
  if (!value) return undefined;
  return jobKinds.includes(value as JobKind) ? (value as JobKind) : undefined;
}

function requestUrl(req: NextRequest): URL {
  return req.nextUrl ?? new URL(req.url);
}

export async function GET(req: NextRequest) {
  try {
    const context = await resolvePlatformContext(req);
    const url = requestUrl(req);
    const projectId = url.searchParams.get("projectId") ?? undefined;
    if (
      projectId &&
      !(await findTenantProject(projectId, context.tenant.id, context.user.id))
    ) {
      return NextResponse.json({ error: "not found" }, { status: 404 });
    }
    const kind = parseKind(url.searchParams.get("kind"));
    const limitRaw = url.searchParams.get("limit");
    const limit = limitRaw ? Number.parseInt(limitRaw, 10) : 20;
    return NextResponse.json(
      await listJobViews({
        tenantId: context.tenant.id,
        ownerUserId: context.user.id,
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
