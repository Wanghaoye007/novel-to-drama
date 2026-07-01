import { and, desc, eq, gte } from "drizzle-orm";
import { v4 as uuid } from "uuid";
import { db, schema } from "@/db/client";
import type { PlatformContext } from "./platform-context";

type UsageEventRow = typeof schema.usageEvents.$inferSelect;
export type UsageEventType = typeof schema.usageEvents.$inferInsert.eventType;

export type UsageEventView = {
  id: string;
  eventType: UsageEventType;
  quantity: number;
  projectId: string | null;
  jobId: string | null;
  apiKeyId: string | null;
  metadata: unknown;
  createdAt: string;
};

export type UsageSummary = {
  tenantId: string;
  since: string;
  until: string;
  totals: Array<{
    eventType: UsageEventType;
    count: number;
    quantity: number;
  }>;
  recentEvents: UsageEventView[];
};

function monthStart(): Date {
  const value = new Date();
  value.setDate(1);
  value.setHours(0, 0, 0, 0);
  return value;
}

function parseMetadata(value: string | null): unknown {
  if (!value) return null;
  try {
    return JSON.parse(value) as unknown;
  } catch {
    return value;
  }
}

function usageEventToView(row: UsageEventRow): UsageEventView {
  return {
    id: row.id,
    eventType: row.eventType,
    quantity: row.quantity,
    projectId: row.projectId,
    jobId: row.jobId,
    apiKeyId: row.apiKeyId,
    metadata: parseMetadata(row.metadataJson),
    createdAt: row.createdAt.toISOString(),
  };
}

export async function recordUsageEvent({
  context,
  eventType,
  quantity = 1,
  projectId,
  jobId,
  metadata,
}: {
  context: PlatformContext;
  eventType: UsageEventType;
  quantity?: number;
  projectId?: string | null;
  jobId?: string | null;
  metadata?: unknown;
}): Promise<void> {
  await db.insert(schema.usageEvents).values({
    id: uuid(),
    tenantId: context.tenant.id,
    userId: context.user.id,
    apiKeyId: context.apiKey?.id ?? null,
    projectId,
    jobId,
    eventType,
    quantity: Math.max(1, Math.floor(quantity)),
    metadataJson: metadata == null ? null : JSON.stringify(metadata, null, 2),
    createdAt: new Date(),
  });
}

export async function getUsageSummary(
  context: PlatformContext,
  since = monthStart()
): Promise<UsageSummary> {
  const rows = await db.query.usageEvents.findMany({
    where: and(
      eq(schema.usageEvents.tenantId, context.tenant.id),
      gte(schema.usageEvents.createdAt, since)
    ),
    orderBy: [desc(schema.usageEvents.createdAt)],
    limit: 200,
  });
  const totals = new Map<UsageEventType, { count: number; quantity: number }>();
  for (const row of rows) {
    const current = totals.get(row.eventType) ?? { count: 0, quantity: 0 };
    current.count += 1;
    current.quantity += row.quantity;
    totals.set(row.eventType, current);
  }
  return {
    tenantId: context.tenant.id,
    since: since.toISOString(),
    until: new Date().toISOString(),
    totals: Array.from(totals, ([eventType, total]) => ({
      eventType,
      ...total,
    })),
    recentEvents: rows.slice(0, 50).map(usageEventToView),
  };
}
