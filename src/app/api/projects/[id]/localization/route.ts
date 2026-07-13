import { NextRequest, NextResponse } from "next/server";
import { startLocalizationExportJob } from "@/lib/engine-runner";
import { kickJobWorker } from "@/lib/job-worker";
import {
  localizationProfiles,
  resolveLocalizationProfile,
} from "@/lib/localization-profiles";
import {
  findTenantProject,
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";
import { recordUsageEvent } from "@/lib/platform-usage";

function requestUrl(req: NextRequest): URL {
  return req.nextUrl ?? new URL(req.url);
}

export async function GET(req: NextRequest) {
  try {
    const context = await resolvePlatformContext(req);
    return NextResponse.json(
      localizationProfiles().map(({ path: _path, ...profile }) => profile),
      { headers: platformHeaders(context) }
    );
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const context = await resolvePlatformContext(req);
    const project = await findTenantProject(id, context.tenant.id, context.user.id);
    if (!project) return NextResponse.json({ error: "not found" }, { status: 404 });

    const url = requestUrl(req);
    const round = url.searchParams.get("round");
    const roundNumber = round ? Number.parseInt(round, 10) : null;
    const profileId = url.searchParams.get("profile");
    const profile = resolveLocalizationProfile(profileId);
    const job = await startLocalizationExportJob(id, {
      profilePath: profile.path,
      profileId: profile.id,
      roundNumber,
      idempotencyKey:
        req.headers.get("idempotency-key") ??
        req.headers.get("x-idempotency-key") ??
        null,
    });
    kickJobWorker();
    await recordUsageEvent({
      context,
      eventType: "localization_export",
      jobId: job.id,
      projectId: id,
      metadata: {
        round: roundNumber,
        profile: profile.id,
      },
    });
    return NextResponse.json(
      { status: job.status === "succeeded" ? "succeeded" : "queued", jobId: job.id },
      { status: 202, headers: platformHeaders(context) }
    );
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    return new Response(error instanceof Error ? error.message : String(error), {
      status: 400,
    });
  }
}
