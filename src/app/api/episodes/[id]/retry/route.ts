import { NextRequest, NextResponse } from "next/server";

export async function POST(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  return NextResponse.json(
    {
      error: "episode retry is disabled; rerun the next Engine round instead",
      id,
    },
    { status: 410 }
  );
}
