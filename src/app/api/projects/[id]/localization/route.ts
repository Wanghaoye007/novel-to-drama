import path from "path";
import { NextRequest, NextResponse } from "next/server";
import { exportLocalization } from "@/lib/engine-runner";

function resolveProfilePath(profileId: string | null): string {
  const safeProfile = profileId || "us_tiktok";
  if (safeProfile !== "us_tiktok") {
    throw new Error(`unsupported localization profile: ${safeProfile}`);
  }
  return path.join(process.cwd(), "examples", "localization_profiles", "us_tiktok.json");
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const round = req.nextUrl.searchParams.get("round");
  const profile = req.nextUrl.searchParams.get("profile");
  try {
    const paths = await exportLocalization(
      id,
      resolveProfilePath(profile),
      round ? Number.parseInt(round, 10) : undefined,
      profile || "us_tiktok"
    );
    return NextResponse.json(paths);
  } catch (error) {
    return new Response(error instanceof Error ? error.message : String(error), {
      status: 400,
    });
  }
}
