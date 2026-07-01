import { NextRequest, NextResponse } from "next/server";
import { getDeliveryPreflight } from "@/lib/engine-runner";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const round = req.nextUrl.searchParams.get("round");
  try {
    const report = await getDeliveryPreflight(
      id,
      round ? Number.parseInt(round, 10) : undefined
    );
    return NextResponse.json(report);
  } catch (error) {
    return new Response(error instanceof Error ? error.message : String(error), {
      status: 400,
    });
  }
}
