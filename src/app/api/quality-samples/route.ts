import { NextRequest, NextResponse } from "next/server";
import {
  getQualitySampleEvaluation,
  runQualitySampleEvaluation,
} from "@/lib/engine-runner";

export async function GET() {
  try {
    return NextResponse.json(await getQualitySampleEvaluation());
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 500 }
    );
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = (await req.json().catch(() => ({}))) as { rounds?: number };
    const rounds = Number.isFinite(body.rounds) ? Number(body.rounds) : 2;
    return NextResponse.json(await runQualitySampleEvaluation(rounds));
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 500 }
    );
  }
}
