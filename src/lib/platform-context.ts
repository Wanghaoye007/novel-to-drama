import { and, count, eq, gte, isNull } from "drizzle-orm";
import { v4 as uuid } from "uuid";
import { db, schema } from "@/db/client";

type UserRow = typeof schema.users.$inferSelect;
type TenantRow = typeof schema.tenants.$inferSelect;
type MemberRow = typeof schema.tenantMembers.$inferSelect;
type ProjectRow = typeof schema.projects.$inferSelect;
type HeaderBag = { get(name: string): string | null };
type HeaderSource = { headers: HeaderBag } | HeaderBag;

export class QuotaError extends Error {
  status = 429;

  constructor(
    message: string,
    readonly quota: { limit: number; used: number; kind: string }
  ) {
    super(message);
  }
}

export type PlatformContext = {
  user: UserRow;
  tenant: TenantRow;
  member: MemberRow;
};

function hasHeaders(source: HeaderSource): source is { headers: HeaderBag } {
  return "headers" in source;
}

function headerValue(source: HeaderSource | undefined, name: string): string | null {
  if (!source) return null;
  if (hasHeaders(source)) return source.headers.get(name);
  return source.get(name);
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

function contextInput(source?: HeaderSource) {
  const email =
    headerValue(source, "x-novel-user-email") ??
    process.env.NOVEL_DRAMA_USER_EMAIL ??
    "local@novel-drama.local";
  const tenantSlug =
    headerValue(source, "x-novel-tenant") ??
    process.env.NOVEL_DRAMA_TENANT_SLUG ??
    "local";
  const tenantName =
    headerValue(source, "x-novel-tenant-name") ??
    process.env.NOVEL_DRAMA_TENANT_NAME ??
    "Local Workspace";
  return {
    email: email.trim().toLowerCase(),
    tenantSlug: slugify(tenantSlug),
    tenantName,
  };
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
  userId: string
): Promise<MemberRow> {
  const existing = await db.query.tenantMembers.findFirst({
    where: and(
      eq(schema.tenantMembers.tenantId, tenantId),
      eq(schema.tenantMembers.userId, userId)
    ),
  });
  if (existing) return existing;
  const id = uuid();
  await db.insert(schema.tenantMembers).values({
    id,
    tenantId,
    userId,
    role: "owner",
    createdAt: new Date(),
  });
  const created = await db.query.tenantMembers.findFirst({
    where: eq(schema.tenantMembers.id, id),
  });
  if (!created) throw new Error("tenant membership insert failed");
  return created;
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

export async function resolvePlatformContext(
  source?: HeaderSource
): Promise<PlatformContext> {
  const input = contextInput(source);
  const user = await ensureUser(input.email);
  const tenant = await ensureTenant(input.tenantSlug, input.tenantName);
  const member = await ensureMembership(tenant.id, user.id);
  const context = { user, tenant, member };
  await attachLegacyRows(context);
  return context;
}

async function countRows(tableCount: Promise<Array<{ value: number }>>): Promise<number> {
  const rows = await tableCount;
  return rows[0]?.value ?? 0;
}

export async function assertProjectQuota(context: PlatformContext): Promise<void> {
  const used = await countRows(
    db
      .select({ value: count() })
      .from(schema.projects)
      .where(eq(schema.projects.tenantId, context.tenant.id))
  );
  const limit = context.tenant.projectLimit;
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
  const limit = tenant.monthlyJobLimit;
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
  tenantId: string
): Promise<ProjectRow | undefined> {
  return db.query.projects.findFirst({
    where: and(
      eq(schema.projects.id, projectId),
      eq(schema.projects.tenantId, tenantId)
    ),
  });
}

export function platformHeaders(context: PlatformContext) {
  return {
    "x-novel-tenant-id": context.tenant.id,
    "x-novel-tenant-slug": context.tenant.slug,
    "x-novel-user-id": context.user.id,
  };
}
