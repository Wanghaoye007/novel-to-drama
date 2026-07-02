import { NextRequest, NextResponse } from "next/server";
import {
  createMethodologySource,
  listMethodology,
} from "@/lib/methodology";
import {
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";

export async function GET(req: NextRequest) {
  try {
    const context = await resolvePlatformContext(req);
    return NextResponse.json(
      await listMethodology({ tenantId: context.tenant.id }),
      { headers: platformHeaders(context) }
    );
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}

export async function POST(req: NextRequest) {
  try {
    const context = await resolvePlatformContext(req);
    const body = (await req.json().catch(() => ({}))) as {
      title?: string;
      sourceType?: string;
      rawText?: string;
      originPath?: string | null;
    };
    if (!body.title?.trim() || !body.rawText?.trim()) {
      return NextResponse.json(
        { error: "missing title or rawText" },
        { status: 400, headers: platformHeaders(context) }
      );
    }

    const result = await createMethodologySource(
      { tenantId: context.tenant.id },
      {
        title: body.title,
        sourceType: body.sourceType?.trim() || "sop",
        rawText: body.rawText,
        originPath: body.originPath || null,
      }
    );
    return NextResponse.json(result, { headers: platformHeaders(context) });
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    return NextResponse.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 400 }
    );
  }
}
