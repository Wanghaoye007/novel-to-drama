import { NextRequest, NextResponse } from "next/server";
import {
  createTenantApiKey,
  listTenantApiKeys,
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";

export async function GET(req: NextRequest) {
  try {
    const context = await resolvePlatformContext(req);
    return NextResponse.json(
      { apiKeys: await listTenantApiKeys(context) },
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
    const body = (await req.json().catch(() => ({}))) as { name?: string };
    const created = await createTenantApiKey(context, body.name ?? "Default key");
    return NextResponse.json(created, {
      status: 201,
      headers: platformHeaders(context),
    });
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}
