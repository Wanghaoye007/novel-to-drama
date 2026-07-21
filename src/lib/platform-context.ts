import { createHash, createHmac, randomBytes, timingSafeEqual } from "crypto";
import { and, count, eq, gte, inArray, isNull } from "drizzle-orm";
import { v4 as uuid } from "uuid";
import { db, schema } from "@/db/client";
import { isProductionLike } from "./deployment-readiness";

type UserRow = typeof schema.users.$inferSelect;
type TenantRow = typeof schema.tenants.$inferSelect;
type MemberRow = typeof schema.tenantMembers.$inferSelect;
type ProjectRow = typeof schema.projects.$inferSelect;
type ApiKeyRow = typeof schema.apiKeys.$inferSelect;
type HeaderBag = { get(name: string): string | null };
type CookieBag = { get(name: string): { value: string } | undefined };
type RequestLike = { headers: HeaderBag; cookies?: CookieBag; url?: string };
type HeaderSource = RequestLike | HeaderBag;

export type ApiKeyView = {
  id: string;
  name: string;
  keyPrefix: string;
  lastUsedAt: string | null;
  revokedAt: string | null;
  createdAt: string;
};

export class QuotaError extends Error {
  status = 429;

  constructor(
    message: string,
    readonly quota: { limit: number; used: number; kind: string }
  ) {
    super(message);
  }
}

export class PlatformAuthError extends Error {
  status = 401;
}

export class PlatformPermissionError extends Error {
  status = 403;
}

export type PlatformContext = {
  user: UserRow;
  tenant: TenantRow;
  member: MemberRow;
  apiKey: ApiKeyRow | null;
};

export type TenantMemberRole = MemberRow["role"];

export type TenantMemberView = {
  id: string;
  userId: string;
  email: string;
  name: string | null;
  role: TenantMemberRole;
  isCurrentUser: boolean;
  createdAt: string;
};

export type PlatformSessionInput = {
  email?: string | null;
  tenantSlug?: string | null;
  tenantName?: string | null;
};

export const platformSessionCookieNames = {
  signed: "novel_platform_session",
  email: "novel_user_email",
  tenantSlug: "novel_tenant_slug",
  tenantName: "novel_tenant_name",
} as const;

export function platformSessionSwitchAllowed(): boolean {
  return !isProductionLike() || process.env.NOVEL_DRAMA_ALLOW_SESSION_SWITCH === "1";
}

function platformSessionSecret(): string {
  const configured = process.env.NOVEL_DRAMA_SESSION_SECRET?.trim();
  const accessToken = process.env.NOVEL_DRAMA_ACCESS_TOKEN?.trim();
  if (
    configured &&
    (!isProductionLike() ||
      (configured.length >= 32 && (!accessToken || configured !== accessToken)))
  ) {
    return configured;
  }
  if (isProductionLike()) {
    throw new PlatformAuthError(
      "NOVEL_DRAMA_SESSION_SECRET must be at least 32 characters and independent"
    );
  }
  return accessToken || "local-novel-drama-session";
}

function sessionSignature(payload: string): string {
  return createHmac("sha256", platformSessionSecret())
    .update(payload)
    .digest("base64url");
}

export function createPlatformSessionToken(input: PlatformSessionInput): string {
  const normalized = normalizePlatformSessionInput(input);
  const payload = Buffer.from(JSON.stringify(normalized), "utf8").toString(
    "base64url"
  );
  return `${payload}.${sessionSignature(payload)}`;
}

function readPlatformSessionToken(token: string | null): PlatformSessionInput | null {
  if (!token) return null;
  const [payload, signature, extra] = token.split(".");
  if (!payload || !signature || extra) return null;
  const expected = sessionSignature(payload);
  const actualBuffer = Buffer.from(signature);
  const expectedBuffer = Buffer.from(expected);
  if (
    actualBuffer.length !== expectedBuffer.length ||
    !timingSafeEqual(actualBuffer, expectedBuffer)
  ) {
    return null;
  }
  try {
    return JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as PlatformSessionInput;
  } catch {
    return null;
  }
}

function hasHeaders(source: HeaderSource): source is RequestLike {
  return typeof (source as RequestLike).headers?.get === "function";
}

function hasCookies(source: HeaderSource): source is RequestLike {
  return typeof (source as RequestLike).cookies?.get === "function";
}

function headerValue(source: HeaderSource | undefined, name: string): string | null {
  if (!source) return null;
  if (hasHeaders(source)) return source.headers.get(name);
  return source.get(name);
}

function cookieValue(source: HeaderSource | undefined, name: string): string | null {
  if (!source || !hasCookies(source)) return null;
  const value = source.cookies?.get(name)?.value;
  if (!value) return null;
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

function bearerToken(source?: HeaderSource): string | null {
  const authorization = headerValue(source, "authorization");
  const match = authorization?.match(/^Bearer\s+(.+)$/i);
  return match?.[1]?.trim() || null;
}

function apiKeyToken(source?: HeaderSource): string | null {
  return headerValue(source, "x-novel-api-key")?.trim() || bearerToken(source);
}

function shouldRequireApiKey(source?: HeaderSource): boolean {
  if (process.env.NOVEL_DRAMA_REQUIRE_API_KEY !== "1") return false;
  if (!source || !hasHeaders(source) || !source.url) return false;
  const pathname = new URL(source.url).pathname;
  if (pathname === "/api/platform/session") return false;
  return pathname.startsWith("/api/");
}

function hashApiKey(token: string): string {
  return createHash("sha256").update(token).digest("hex");
}

function dateToIso(value: Date | null): string | null {
  return value ? value.toISOString() : null;
}

function slugify(value: string): string {
  return (
    value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9_-]+/g, "-")
      .replace(/^-+|-+$/g, "") || "local"
  );
}

function nameFromSlug(slug: string): string {
  if (slug === "local") return "Local Workspace";
  return slug
    .split(/[-_]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function normalizePlatformSessionInput(input: PlatformSessionInput) {
  const tenantSlug = slugify(input.tenantSlug ?? "local");
  const tenantName = (input.tenantName ?? "").trim() || nameFromSlug(tenantSlug);
  const email = (input.email ?? "local@novel-drama.local").trim().toLowerCase();
  return {
    email,
    tenantSlug,
    tenantName,
  };
}

function contextInput(source?: HeaderSource) {
  const configuredProxySecret = process.env.NOVEL_DRAMA_TRUST_PROXY_SECRET?.trim();
  const suppliedProxySecret = headerValue(source, "x-novel-proxy-secret")?.trim();
  const proxySecretMatches = Boolean(
    configuredProxySecret &&
      suppliedProxySecret &&
      configuredProxySecret.length === suppliedProxySecret.length &&
      timingSafeEqual(Buffer.from(configuredProxySecret), Buffer.from(suppliedProxySecret))
  );
  const trustIdentityHeaders =
    process.env.NOVEL_DRAMA_TRUST_IDENTITY_HEADERS === "1" &&
    (!isProductionLike() || proxySecretMatches);
  const signedSession = readPlatformSessionToken(
    cookieValue(source, platformSessionCookieNames.signed)
  );
  if (signedSession) return normalizePlatformSessionInput(signedSession);
  const allowLegacyCookies =
    process.env.NOVEL_DRAMA_ALLOW_LEGACY_SESSION_COOKIES === "1";
  const email =
    (trustIdentityHeaders ? headerValue(source, "x-novel-user-email") : null) ??
    (allowLegacyCookies
      ? cookieValue(source, platformSessionCookieNames.email)
      : null) ??
    process.env.NOVEL_DRAMA_USER_EMAIL ??
    "local@novel-drama.local";
  const tenantSlug =
    (trustIdentityHeaders ? headerValue(source, "x-novel-tenant") : null) ??
    (allowLegacyCookies
      ? cookieValue(source, platformSessionCookieNames.tenantSlug)
      : null) ??
    process.env.NOVEL_DRAMA_TENANT_SLUG ??
    "local";
  const tenantName =
    (trustIdentityHeaders ? headerValue(source, "x-novel-tenant-name") : null) ??
    (allowLegacyCookies
      ? cookieValue(source, platformSessionCookieNames.tenantName)
      : null) ??
    process.env.NOVEL_DRAMA_TENANT_NAME ??
    "Local Workspace";
  return normalizePlatformSessionInput({ email, tenantSlug, tenantName });
}

async function ensureUser(email: string): Promise<UserRow> {
  const existing = await db.query.users.findFirst({
    where: eq(schema.users.email, email),
  });
  if (existing) return existing;
  const now = new Date();
  const id = uuid();
  await db.insert(schema.users).values({
    id,
    email,
    name: email.split("@")[0],
    createdAt: now,
    updatedAt: now,
  });
  const created = await db.query.users.findFirst({ where: eq(schema.users.id, id) });
  if (!created) throw new Error("user insert failed");
  return created;
}

async function ensureTenant(slug: string, name: string): Promise<TenantRow> {
  const existing = await db.query.tenants.findFirst({
    where: eq(schema.tenants.slug, slug),
  });
  if (existing) return existing;
  const now = new Date();
  const id = uuid();
  await db.insert(schema.tenants).values({
    id,
    slug,
    name,
    createdAt: now,
    updatedAt: now,
  });
  const created = await db.query.tenants.findFirst({
    where: eq(schema.tenants.id, id),
  });
  if (!created) throw new Error("tenant insert failed");
  return created;
}

async function ensureMembership(
  tenantId: string,
  userId: string,
  role?: TenantMemberRole
): Promise<MemberRow> {
  const existing = await db.query.tenantMembers.findFirst({
    where: and(
      eq(schema.tenantMembers.tenantId, tenantId),
      eq(schema.tenantMembers.userId, userId)
    ),
  });
  if (existing) return existing;
  const existingMemberCount = await countRows(
    db
      .select({ value: count() })
      .from(schema.tenantMembers)
      .where(eq(schema.tenantMembers.tenantId, tenantId))
  );
  const id = uuid();
  await db.insert(schema.tenantMembers).values({
    id,
    tenantId,
    userId,
    role: role ?? (existingMemberCount === 0 ? "owner" : "member"),
    createdAt: new Date(),
  });
  const created = await db.query.tenantMembers.findFirst({
    where: eq(schema.tenantMembers.id, id),
  });
  if (!created) throw new Error("tenant membership insert failed");
  return created;
}

function canManageMembers(context: PlatformContext): boolean {
  return context.member.role === "owner" || context.member.role === "admin";
}

function assertCanManageMembers(context: PlatformContext): void {
  if (!canManageMembers(context)) {
    throw new PlatformPermissionError("workspace admin required");
  }
}

function normalizeMemberRole(value: string | null | undefined): TenantMemberRole {
  if (value === "owner" || value === "admin" || value === "member") return value;
  return "member";
}

async function countOwners(tenantId: string): Promise<number> {
  return countRows(
    db
      .select({ value: count() })
      .from(schema.tenantMembers)
      .where(
        and(
          eq(schema.tenantMembers.tenantId, tenantId),
          eq(schema.tenantMembers.role, "owner")
        )
      )
  );
}

function memberToView({
  member,
  user,
  currentUserId,
}: {
  member: MemberRow;
  user: UserRow | undefined;
  currentUserId: string;
}): TenantMemberView {
  return {
    id: member.id,
    userId: member.userId,
    email: user?.email ?? "unknown@novel-drama.local",
    name: user?.name ?? null,
    role: member.role,
    isCurrentUser: member.userId === currentUserId,
    createdAt: member.createdAt.toISOString(),
  };
}

async function attachLegacyRows(context: PlatformContext): Promise<void> {
  if (process.env.NOVEL_DRAMA_BACKFILL_LEGACY_TENANT === "0") return;
  await db
    .update(schema.projects)
    .set({
      tenantId: context.tenant.id,
      ownerUserId: context.user.id,
      updatedAt: new Date(),
    })
    .where(isNull(schema.projects.tenantId));
  await db
    .update(schema.jobs)
    .set({ tenantId: context.tenant.id, updatedAt: new Date() })
    .where(isNull(schema.jobs.tenantId));
}

async function contextFromApiKey(source?: HeaderSource): Promise<PlatformContext | null> {
  const token = apiKeyToken(source);
  if (!token) {
    if (shouldRequireApiKey(source)) {
      throw new PlatformAuthError("API key required");
    }
    return null;
  }

  const keyHash = hashApiKey(token);
  const apiKey = await db.query.apiKeys.findFirst({
    where: and(
      eq(schema.apiKeys.keyHash, keyHash),
      isNull(schema.apiKeys.revokedAt)
    ),
  });
  if (!apiKey) throw new PlatformAuthError("invalid API key");

  const tenant = await db.query.tenants.findFirst({
    where: eq(schema.tenants.id, apiKey.tenantId),
  });
  if (!tenant) throw new PlatformAuthError("API key tenant not found");

  let user: UserRow | undefined;
  if (apiKey.createdByUserId) {
    user = await db.query.users.findFirst({
      where: eq(schema.users.id, apiKey.createdByUserId),
    });
  }
  if (!user) {
    const member = await db.query.tenantMembers.findFirst({
      where: eq(schema.tenantMembers.tenantId, tenant.id),
    });
    if (member) {
      user = await db.query.users.findFirst({
        where: eq(schema.users.id, member.userId),
      });
    }
  }
  if (!user) {
    user = await ensureUser(`api-key-${apiKey.keyPrefix}@novel-drama.local`);
  }

  const member = await ensureMembership(tenant.id, user.id);
  const now = new Date();
  await db
    .update(schema.apiKeys)
    .set({ lastUsedAt: now, updatedAt: now })
    .where(eq(schema.apiKeys.id, apiKey.id));

  return {
    user,
    tenant,
    member,
    apiKey: { ...apiKey, lastUsedAt: now, updatedAt: now },
  };
}

export async function resolvePlatformContext(
  source?: HeaderSource
): Promise<PlatformContext> {
  const apiKeyContext = await contextFromApiKey(source);
  if (apiKeyContext) return apiKeyContext;

  return resolvePlatformContextFromInput(contextInput(source));
}

export async function resolvePlatformContextFromInput(
  input: PlatformSessionInput
): Promise<PlatformContext> {
  const normalized = normalizePlatformSessionInput(input);
  const user = await ensureUser(normalized.email);
  const tenant = await ensureTenant(
    normalized.tenantSlug,
    normalized.tenantName
  );
  const member = await ensureMembership(tenant.id, user.id);
  const context = { user, tenant, member, apiKey: null };
  await attachLegacyRows(context);
  return context;
}

async function countRows(tableCount: Promise<Array<{ value: number }>>): Promise<number> {
  const rows = await tableCount;
  return rows[0]?.value ?? 0;
}

function envLimit(name: string): number | null {
  const raw = process.env[name]?.trim();
  if (!raw) return null;
  const value = Number.parseInt(raw, 10);
  return Number.isFinite(value) && value > 0 ? value : null;
}

function effectiveProjectLimit(planLimit: number): number {
  return Math.max(planLimit, envLimit("NOVEL_DRAMA_INTERNAL_PROJECT_LIMIT") ?? 0);
}

function effectiveMonthlyJobLimit(planLimit: number): number {
  return Math.max(planLimit, envLimit("NOVEL_DRAMA_INTERNAL_MONTHLY_JOB_LIMIT") ?? 0);
}

export async function assertProjectQuota(context: PlatformContext): Promise<void> {
  const used = await countRows(
    db
      .select({ value: count() })
      .from(schema.projects)
      .where(eq(schema.projects.tenantId, context.tenant.id))
  );
  const limit = effectiveProjectLimit(context.tenant.projectLimit);
  if (used >= limit) {
    throw new QuotaError("project quota exceeded", {
      kind: "projects",
      limit,
      used,
    });
  }
}

export async function assertTenantJobQuota(tenantId: string): Promise<void> {
  const tenant = await db.query.tenants.findFirst({
    where: eq(schema.tenants.id, tenantId),
  });
  if (!tenant) return;
  const monthStart = new Date();
  monthStart.setDate(1);
  monthStart.setHours(0, 0, 0, 0);
  const used = await countRows(
    db
      .select({ value: count() })
      .from(schema.jobs)
      .where(
        and(
          eq(schema.jobs.tenantId, tenantId),
          gte(schema.jobs.createdAt, monthStart)
        )
      )
  );
  const limit = effectiveMonthlyJobLimit(tenant.monthlyJobLimit);
  if (used >= limit) {
    throw new QuotaError("monthly job quota exceeded", {
      kind: "monthly_jobs",
      limit,
      used,
    });
  }
}

export async function findTenantProject(
  projectId: string,
  tenantId: string,
  ownerUserId?: string | null
): Promise<ProjectRow | undefined> {
  const filters = [
    eq(schema.projects.id, projectId),
    eq(schema.projects.tenantId, tenantId),
  ];
  if (ownerUserId) filters.push(eq(schema.projects.ownerUserId, ownerUserId));
  return db.query.projects.findFirst({
    where: and(...filters),
  });
}

export function apiKeyToView(apiKey: ApiKeyRow): ApiKeyView {
  return {
    id: apiKey.id,
    name: apiKey.name,
    keyPrefix: apiKey.keyPrefix,
    lastUsedAt: dateToIso(apiKey.lastUsedAt),
    revokedAt: dateToIso(apiKey.revokedAt),
    createdAt: apiKey.createdAt.toISOString(),
  };
}

export async function listTenantApiKeys(
  context: PlatformContext
): Promise<ApiKeyView[]> {
  const rows = await db.query.apiKeys.findMany({
    where: eq(schema.apiKeys.tenantId, context.tenant.id),
  });
  return rows
    .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())
    .map(apiKeyToView);
}

export async function listTenantMembers(
  context: PlatformContext
): Promise<{
  members: TenantMemberView[];
  canManageMembers: boolean;
}> {
  const members = await db.query.tenantMembers.findMany({
    where: eq(schema.tenantMembers.tenantId, context.tenant.id),
  });
  const userIds = members.map((member) => member.userId);
  const users = userIds.length
    ? await db.query.users.findMany({
        where: inArray(schema.users.id, userIds),
      })
    : [];
  const userById = new Map(users.map((user) => [user.id, user]));
  return {
    canManageMembers: canManageMembers(context),
    members: members
      .sort((a, b) => a.createdAt.getTime() - b.createdAt.getTime())
      .map((member) =>
        memberToView({
          member,
          user: userById.get(member.userId),
          currentUserId: context.user.id,
        })
      ),
  };
}

export async function addTenantMember(
  context: PlatformContext,
  email: string,
  role: string | null | undefined
): Promise<TenantMemberView> {
  assertCanManageMembers(context);
  const normalizedEmail = email.trim().toLowerCase();
  if (!normalizedEmail.includes("@")) {
    throw new Error("invalid email");
  }
  const user = await ensureUser(normalizedEmail);
  const member = await ensureMembership(
    context.tenant.id,
    user.id,
    normalizeMemberRole(role)
  );
  return memberToView({
    member,
    user,
    currentUserId: context.user.id,
  });
}

export async function updateTenantMemberRole(
  context: PlatformContext,
  memberId: string,
  role: string | null | undefined
): Promise<TenantMemberView> {
  assertCanManageMembers(context);
  const nextRole = normalizeMemberRole(role);
  const existing = await db.query.tenantMembers.findFirst({
    where: and(
      eq(schema.tenantMembers.id, memberId),
      eq(schema.tenantMembers.tenantId, context.tenant.id)
    ),
  });
  if (!existing) throw new Error("member not found");
  if (existing.role === "owner" && nextRole !== "owner") {
    const owners = await countOwners(context.tenant.id);
    if (owners <= 1) throw new Error("workspace must keep at least one owner");
  }
  await db
    .update(schema.tenantMembers)
    .set({ role: nextRole })
    .where(eq(schema.tenantMembers.id, memberId));
  const updated = await db.query.tenantMembers.findFirst({
    where: eq(schema.tenantMembers.id, memberId),
  });
  if (!updated) throw new Error("member update failed");
  const user = await db.query.users.findFirst({
    where: eq(schema.users.id, updated.userId),
  });
  return memberToView({
    member: updated,
    user,
    currentUserId: context.user.id,
  });
}

export async function removeTenantMember(
  context: PlatformContext,
  memberId: string
): Promise<boolean> {
  assertCanManageMembers(context);
  const existing = await db.query.tenantMembers.findFirst({
    where: and(
      eq(schema.tenantMembers.id, memberId),
      eq(schema.tenantMembers.tenantId, context.tenant.id)
    ),
  });
  if (!existing) return false;
  if (existing.userId === context.user.id) {
    throw new Error("cannot remove the current session member");
  }
  if (existing.role === "owner") {
    const owners = await countOwners(context.tenant.id);
    if (owners <= 1) throw new Error("workspace must keep at least one owner");
  }
  await db
    .delete(schema.tenantMembers)
    .where(eq(schema.tenantMembers.id, memberId));
  return true;
}

export async function createTenantApiKey(
  context: PlatformContext,
  name: string
): Promise<{ token: string; apiKey: ApiKeyView }> {
  const publicPart = randomBytes(6).toString("hex");
  const secret = randomBytes(24).toString("base64url");
  const token = `ndk_${publicPart}_${secret}`;
  const now = new Date();
  const id = uuid();
  await db.insert(schema.apiKeys).values({
    id,
    tenantId: context.tenant.id,
    createdByUserId: context.user.id,
    name: name.trim() || "Untitled key",
    keyPrefix: `ndk_${publicPart}`,
    keyHash: hashApiKey(token),
    createdAt: now,
    updatedAt: now,
  });
  const created = await db.query.apiKeys.findFirst({
    where: eq(schema.apiKeys.id, id),
  });
  if (!created) throw new Error("API key insert failed");
  return { token, apiKey: apiKeyToView(created) };
}

export async function revokeTenantApiKey(
  context: PlatformContext,
  apiKeyId: string
): Promise<boolean> {
  const existing = await db.query.apiKeys.findFirst({
    where: and(
      eq(schema.apiKeys.id, apiKeyId),
      eq(schema.apiKeys.tenantId, context.tenant.id)
    ),
  });
  if (!existing) return false;
  const now = new Date();
  await db
    .update(schema.apiKeys)
    .set({ revokedAt: existing.revokedAt ?? now, updatedAt: now })
    .where(eq(schema.apiKeys.id, apiKeyId));
  return true;
}

export function platformHeaders(context: PlatformContext) {
  const headers: Record<string, string> = {
    "x-novel-tenant-id": context.tenant.id,
    "x-novel-tenant-slug": context.tenant.slug,
    "x-novel-user-id": context.user.id,
  };
  if (context.apiKey) headers["x-novel-api-key-id"] = context.apiKey.id;
  return headers;
}
