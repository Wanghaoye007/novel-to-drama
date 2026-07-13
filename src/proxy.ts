import { NextResponse, type NextRequest } from "next/server";

const ACCESS_COOKIE = "novel_drama_access";
const TOKEN_QUERY = "access_token";
const TOKEN_HEADER = "x-novel-access-token";

function configuredAccessToken(): string | null {
  const token = process.env.NOVEL_DRAMA_ACCESS_TOKEN?.trim();
  return token || null;
}

function requestToken(request: NextRequest): string | null {
  const queryToken = request.nextUrl.searchParams.get(TOKEN_QUERY)?.trim();
  if (queryToken) return queryToken;
  const headerToken = request.headers.get(TOKEN_HEADER)?.trim();
  if (headerToken) return headerToken;
  const bearer = request.headers.get("authorization")?.match(/^Bearer\s+(.+)$/i)?.[1];
  return bearer?.trim() || null;
}

function hasAccess(request: NextRequest, accessToken: string): boolean {
  return (
    request.cookies.get(ACCESS_COOKIE)?.value === accessToken ||
    requestToken(request) === accessToken
  );
}

function setAccessCookie(response: NextResponse, accessToken: string) {
  response.cookies.set(ACCESS_COOKIE, accessToken, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NOVEL_DRAMA_ACCESS_COOKIE_SECURE === "1",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  });
}

function unauthorized(request: NextRequest): NextResponse {
  if (request.nextUrl.pathname.startsWith("/api/")) {
    return NextResponse.json(
      { error: "access_token_required" },
      { status: 401 }
    );
  }
  return new NextResponse(
    [
      "<!doctype html>",
      "<meta charset=\"utf-8\">",
      "<title>Access required</title>",
      "<main style=\"font-family:-apple-system,BlinkMacSystemFont,sans-serif;padding:48px;line-height:1.6\">",
      "<h1>需要访问令牌</h1>",
      "<p>请使用带 access_token 的运营链接打开一次，系统会写入浏览器 Cookie。</p>",
      "</main>",
    ].join(""),
    {
      status: 401,
      headers: { "content-type": "text/html; charset=utf-8" },
    }
  );
}

export function proxy(request: NextRequest) {
  const accessToken = configuredAccessToken();
  if (!accessToken) return NextResponse.next();

  const pathname = request.nextUrl.pathname;
  if (pathname === "/api/health") return NextResponse.next();

  const token = requestToken(request);
  if (token === accessToken) {
    if (pathname.startsWith("/api/")) {
      const response = NextResponse.next();
      setAccessCookie(response, accessToken);
      return response;
    }
    const cleanUrl = request.nextUrl.clone();
    cleanUrl.searchParams.delete(TOKEN_QUERY);
    const response = NextResponse.redirect(cleanUrl);
    setAccessCookie(response, accessToken);
    return response;
  }

  if (hasAccess(request, accessToken)) return NextResponse.next();
  return unauthorized(request);
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:png|jpg|jpeg|gif|webp|svg|ico|css|js|map)$).*)",
  ],
};
