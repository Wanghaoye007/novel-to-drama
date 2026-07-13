import { NextRequest, NextResponse } from "next/server";
import {
  platformHeaders,
  resolvePlatformContext,
  revokeTenantApiKey,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const context = await resolvePlatformContext(req);
    const { id } = await params;
    const revoked = await revokeTenantApiKey(context, id);
    if (!revoked) {
      return NextResponse.json({ error: "not found" }, { status: 404 });
    }
    return NextResponse.json(
      { ok: true },
      { headers: platformHeaders(context) }
    );
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}
