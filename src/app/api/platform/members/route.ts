import { NextRequest, NextResponse } from "next/server";
import {
  addTenantMember,
  listTenantMembers,
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";

export async function GET(req: NextRequest) {
  try {
    const context = await resolvePlatformContext(req);
    return NextResponse.json(await listTenantMembers(context), {
      headers: platformHeaders(context),
    });
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
      email?: string;
      role?: string;
    };
    if (!body.email) {
      return NextResponse.json({ error: "missing email" }, { status: 400 });
    }
    return NextResponse.json(
      await addTenantMember(context, body.email, body.role),
      { status: 201, headers: platformHeaders(context) }
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
