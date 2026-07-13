import { NextRequest, NextResponse } from "next/server";
import {
  platformHeaders,
  removeTenantMember,
  resolvePlatformContext,
  updateTenantMemberRole,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const context = await resolvePlatformContext(req);
    const { id } = await params;
    const body = (await req.json().catch(() => ({}))) as { role?: string };
    return NextResponse.json(
      await updateTenantMemberRole(context, id, body.role),
      { headers: platformHeaders(context) }
    );
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    return NextResponse.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 400 }
    );
  }
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const context = await resolvePlatformContext(req);
    const { id } = await params;
    const removed = await removeTenantMember(context, id);
    return NextResponse.json(
      { ok: removed },
      { status: removed ? 200 : 404, headers: platformHeaders(context) }
    );
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    return NextResponse.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 400 }
    );
  }
}
