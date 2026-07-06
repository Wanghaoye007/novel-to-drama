import { NextRequest, NextResponse } from "next/server";
import {
  getMethodologyCard,
  type MethodologyStatus,
  updateMethodologyCardStatus,
} from "@/lib/methodology";
import {
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";

const statuses = new Set<MethodologyStatus>([
  "draft",
  "active",
  "archived",
  "rejected",
]);

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const context = await resolvePlatformContext(req);
    const { id } = await params;
    const card = await getMethodologyCard({ tenantId: context.tenant.id }, id);
    if (!card) {
      return NextResponse.json(
        { error: "not found" },
        { status: 404, headers: platformHeaders(context) }
      );
    }
    return NextResponse.json(card, { headers: platformHeaders(context) });
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    return NextResponse.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 400 }
    );
  }
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const context = await resolvePlatformContext(req);
    const { id } = await params;
    const body = (await req.json().catch(() => ({}))) as { status?: string };
    if (!body.status || !statuses.has(body.status as MethodologyStatus)) {
      return NextResponse.json(
        { error: "invalid status" },
        { status: 400, headers: platformHeaders(context) }
      );
    }

    const updated = await updateMethodologyCardStatus(
      { tenantId: context.tenant.id },
      id,
      body.status as MethodologyStatus
    );
    if (!updated) {
      return NextResponse.json(
        { error: "not found" },
        { status: 404, headers: platformHeaders(context) }
      );
    }
    return NextResponse.json({ ok: true }, { headers: platformHeaders(context) });
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    return NextResponse.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 400 }
    );
  }
}
