import { NextRequest, NextResponse } from "next/server";
import {
  normalizePlatformSessionInput,
  platformHeaders,
  platformSessionCookieNames,
  resolvePlatformContext,
  resolvePlatformContextFromInput,
} from "@/lib/platform-context";

const cookieOptions = {
  httpOnly: true,
  sameSite: "lax" as const,
  path: "/",
  maxAge: 60 * 60 * 24 * 180,
};

function sessionPayload(context: Awaited<ReturnType<typeof resolvePlatformContext>>) {
  return {
    user: {
      id: context.user.id,
      email: context.user.email,
    },
    tenant: {
      id: context.tenant.id,
      slug: context.tenant.slug,
      name: context.tenant.name,
      projectLimit: context.tenant.projectLimit,
      monthlyJobLimit: context.tenant.monthlyJobLimit,
    },
    member: {
      id: context.member.id,
      role: context.member.role,
    },
    apiKeyId: context.apiKey?.id ?? null,
  };
}

function setSessionCookies(
  response: NextResponse,
  session: ReturnType<typeof normalizePlatformSessionInput>
): void {
  response.cookies.set(
    platformSessionCookieNames.email,
    encodeURIComponent(session.email),
    cookieOptions
  );
  response.cookies.set(
    platformSessionCookieNames.tenantSlug,
    encodeURIComponent(session.tenantSlug),
    cookieOptions
  );
  response.cookies.set(
    platformSessionCookieNames.tenantName,
    encodeURIComponent(session.tenantName),
    cookieOptions
  );
}

function clearSessionCookies(response: NextResponse): void {
  response.cookies.delete(platformSessionCookieNames.email);
  response.cookies.delete(platformSessionCookieNames.tenantSlug);
  response.cookies.delete(platformSessionCookieNames.tenantName);
}

export async function GET(req: NextRequest) {
  const context = await resolvePlatformContext(req);
  return NextResponse.json(sessionPayload(context), {
    headers: platformHeaders(context),
  });
}

export async function POST(req: NextRequest) {
  const body = (await req.json().catch(() => ({}))) as {
    email?: string;
    tenantSlug?: string;
    tenantName?: string;
  };
  const session = normalizePlatformSessionInput(body);
  if (!session.email.includes("@")) {
    return NextResponse.json({ error: "invalid email" }, { status: 400 });
  }
  const context = await resolvePlatformContextFromInput(session);
  const response = NextResponse.json(sessionPayload(context), {
    headers: platformHeaders(context),
  });
  setSessionCookies(response, session);
  return response;
}

export async function DELETE(req: NextRequest) {
  const context = await resolvePlatformContext(req);
  const response = NextResponse.json(
    { ok: true, resetTo: "environment defaults" },
    { headers: platformHeaders(context) }
  );
  clearSessionCookies(response);
  return response;
}
