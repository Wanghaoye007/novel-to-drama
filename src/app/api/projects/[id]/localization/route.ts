import { NextRequest, NextResponse } from "next/server";
import { exportLocalization } from "@/lib/engine-runner";
import {
  localizationProfiles,
  resolveLocalizationProfile,
} from "@/lib/localization-profiles";

export async function GET() {
  return NextResponse.json(
    localizationProfiles().map(({ path: _path, ...profile }) => profile)
  );
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
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
    return NextResponse.json(paths);
  } catch (error) {
    return new Response(error instanceof Error ? error.message : String(error), {
      status: 400,
    });
  }
}
