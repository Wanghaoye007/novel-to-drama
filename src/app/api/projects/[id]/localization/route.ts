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

export async function GET(req: NextRequest) {
  const context = await resolvePlatformContext(req);
  return NextResponse.json(
    localizationProfiles().map(({ path: _path, ...profile }) => profile),
    { headers: platformHeaders(context) }
  );
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const context = await resolvePlatformContext(req);
  const project = await findTenantProject(id, context.tenant.id);
  if (!project) return NextResponse.json({ error: "not found" }, { status: 404 });

  const round = req.nextUrl.searchParams.get("round");
  const profileId = req.nextUrl.searchParams.get("profile");
  try {
    const profile = resolveLocalizationProfile(profileId);
    const paths = await exportLocalization(
      id,
      profile.path,
      round ? Number.parseInt(round, 10) : undefined,
      profile.id
    );
    return NextResponse.json(paths, { headers: platformHeaders(context) });
  } catch (error) {
    return new Response(error instanceof Error ? error.message : String(error), {
      status: 400,
    });
  }
}
