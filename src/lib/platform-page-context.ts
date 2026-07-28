import { cookies, headers } from "next/headers";
import {
  listUserWorkspaces,
  platformSessionCookieNames,
  resolvePlatformContext,
  type PlatformContext,
  type UserWorkspaceView,
} from "./platform-context";

export type PlatformPageSession = {
  userEmail: string;
  tenantSlug: string;
  tenantName: string;
  source: "browser" | "api_key" | "default";
  canSwitchSession: boolean;
  workspaces: UserWorkspaceView[];
};

export async function resolvePlatformPageContext(): Promise<{
  context: PlatformContext;
  session: PlatformPageSession;
}> {
  const [headerStore, cookieStore] = await Promise.all([headers(), cookies()]);
  const context = await resolvePlatformContext({
    headers: headerStore,
    cookies: cookieStore,
  });
  const workspaces = await listUserWorkspaces(context.user.id);
  const hasBrowserSession =
    cookieStore.has(platformSessionCookieNames.signed) ||
    cookieStore.has(platformSessionCookieNames.email) ||
    cookieStore.has(platformSessionCookieNames.tenantSlug);
  return {
    context,
    session: {
      userEmail: context.user.email,
      tenantSlug: context.tenant.slug,
      tenantName: context.tenant.name,
      source: context.apiKey ? "api_key" : hasBrowserSession ? "browser" : "default",
      canSwitchSession: workspaces.length > 1,
      workspaces,
    },
  };
}
