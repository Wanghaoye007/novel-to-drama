import { NextRequest, NextResponse } from "next/server";
import { exportLocalization } from "@/lib/engine-runner";
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
    const project = await findTenantProject(id, context.tenant.id);
    if (!project) return NextResponse.json({ error: "not found" }, { status: 404 });

    const round = req.nextUrl.searchParams.get("round");
    const profileId = req.nextUrl.searchParams.get("profile");
    const profile = resolveLocalizationProfile(profileId);
    const paths = await exportLocalization(
      id,
      profile.path,
      round ? Number.parseInt(round, 10) : undefined,
      profile.id
    );
    await recordUsageEvent({
      context,
      eventType: "localization_export",
      projectId: id,
      metadata: {
        round: round ? Number.parseInt(round, 10) : null,
        profile: profile.id,
      },
    });
    return NextResponse.json(paths, { headers: platformHeaders(context) });
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    return new Response(error instanceof Error ? error.message : String(error), {
      status: 400,
    });
  }
}
