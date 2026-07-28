import { NextRequest, NextResponse } from "next/server";
import {
  createPlatformSessionToken,
  listUserWorkspaces,
  normalizePlatformSessionInput,
  platformHeaders,
  platformSessionCookieNames,
  platformSessionSwitchAllowed,
  resolveMemberWorkspace,
  resolvePlatformContext,
  resolvePlatformContextFromInput,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";

function cookieOptions() {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NOVEL_DRAMA_ACCESS_COOKIE_SECURE === "1",
    path: "/",
    maxAge: 60 * 60 * 24 * 180,
  };
}

async function sessionPayload(
  context: Awaited<ReturnType<typeof resolvePlatformContext>>
) {
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
    workspaces: await listUserWorkspaces(context.user.id),
  };
}

function setSessionCookies(
  response: NextResponse,
  session: ReturnType<typeof normalizePlatformSessionInput>
): void {
  response.cookies.set(
    platformSessionCookieNames.signed,
    createPlatformSessionToken(session),
    cookieOptions()
  );
  response.cookies.delete(platformSessionCookieNames.email);
  response.cookies.delete(platformSessionCookieNames.tenantSlug);
  response.cookies.delete(platformSessionCookieNames.tenantName);
}

function clearSessionCookies(response: NextResponse): void {
  response.cookies.delete(platformSessionCookieNames.signed);
  response.cookies.delete(platformSessionCookieNames.email);
  response.cookies.delete(platformSessionCookieNames.tenantSlug);
  response.cookies.delete(platformSessionCookieNames.tenantName);
}

export async function GET(req: NextRequest) {
  const context = await resolvePlatformContext(req);
  return NextResponse.json(await sessionPayload(context), {
    headers: platformHeaders(context),
  });
}

export async function POST(req: NextRequest) {
  try {
    const body = (await req.json().catch(() => ({}))) as {
      email?: string;
      tenantSlug?: string;
      tenantName?: string;
    };
    if (!body.tenantSlug?.trim()) {
      return NextResponse.json({ error: "missing tenantSlug" }, { status: 400 });
    }

    let context: Awaited<ReturnType<typeof resolvePlatformContext>>;
    if (platformSessionSwitchAllowed()) {
      const session = normalizePlatformSessionInput(body);
      if (!session.email.includes("@")) {
        return NextResponse.json({ error: "invalid email" }, { status: 400 });
      }
      context = await resolvePlatformContextFromInput(session);
    } else {
      const current = await resolvePlatformContext(req);
      context = await resolveMemberWorkspace(current, body.tenantSlug);
    }

    const session = normalizePlatformSessionInput({
      email: context.user.email,
      tenantSlug: context.tenant.slug,
      tenantName: context.tenant.name,
    });
    const response = NextResponse.json(await sessionPayload(context), {
      headers: platformHeaders(context),
    });
    setSessionCookies(response, session);
    return response;
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    return NextResponse.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 400 }
    );
  }
}

export async function DELETE(req: NextRequest) {
  if (!platformSessionSwitchAllowed()) {
    return NextResponse.json({ error: "session_switch_disabled" }, { status: 403 });
  }
  const context = await resolvePlatformContext(req);
  const response = NextResponse.json(
    { ok: true, resetTo: "environment defaults" },
    { headers: platformHeaders(context) }
  );
  clearSessionCookies(response);
  return response;
}
