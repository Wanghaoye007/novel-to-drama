import { NextRequest, NextResponse } from "next/server";
import { exportVideoBrief } from "@/lib/engine-runner";

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const round = req.nextUrl.searchParams.get("round");
  try {
    const paths = await exportVideoBrief(
      id,
      round ? Number.parseInt(round, 10) : undefined
    );
    return NextResponse.json(paths);
  } catch (error) {
    return new Response(error instanceof Error ? error.message : String(error), {
      status: 400,
    });
  }
}
