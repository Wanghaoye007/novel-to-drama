import { and, desc, eq, gte } from "drizzle-orm";
import { v4 as uuid } from "uuid";
import { db, schema } from "@/db/client";
import type { PlatformContext } from "./platform-context";
import { settleUsageCredits } from "./platform-credits";

type UsageEventRow = typeof schema.usageEvents.$inferSelect;
export type UsageEventType = typeof schema.usageEvents.$inferInsert.eventType;

export type UsageEventView = {
  id: string;
  eventType: UsageEventType;
  quantity: number;
  billableUnits: number;
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
    billableUnits: number;
  }>;
  recentEvents: UsageEventView[];
};

const usageWeights: Record<UsageEventType, number> = {
  project_create: 2,
  round_start: 10,
  quality_samples_start: 5,
  video_brief_export: 2,
  localization_export: 3,
  delivery_preflight: 1,
  delivery_export: 1,
  episode_txt_export: 1,
  episode_word_export: 1,
};

export function billableUnitsForEvent(
  eventType: UsageEventType,
  quantity: number
): number {
  const normalizedQuantity = Math.max(1, Math.floor(quantity));
  return normalizedQuantity * (usageWeights[eventType] ?? 1);
}

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
  const billableUnits =
    row.billableUnits || billableUnitsForEvent(row.eventType, row.quantity);
  return {
    id: row.id,
    eventType: row.eventType,
    quantity: row.quantity,
    billableUnits,
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
  const normalizedQuantity = Math.max(1, Math.floor(quantity));
  const billableUnits = billableUnitsForEvent(eventType, normalizedQuantity);
  const usageEventId = uuid();
  await db.insert(schema.usageEvents).values({
    id: usageEventId,
    tenantId: context.tenant.id,
    userId: context.user.id,
    apiKeyId: context.apiKey?.id ?? null,
    projectId,
    jobId,
    eventType,
    quantity: normalizedQuantity,
    billableUnits,
    metadataJson: metadata == null ? null : JSON.stringify(metadata, null, 2),
    createdAt: new Date(),
  });
  await settleUsageCredits({
    context,
    usageEventId,
    billableUnits,
    metadata: { eventType, projectId, jobId },
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
  const totals = new Map<
    UsageEventType,
    { count: number; quantity: number; billableUnits: number }
  >();
  for (const row of rows) {
    const current = totals.get(row.eventType) ?? {
      count: 0,
      quantity: 0,
      billableUnits: 0,
    };
    current.count += 1;
    current.quantity += row.quantity;
    current.billableUnits +=
      row.billableUnits || billableUnitsForEvent(row.eventType, row.quantity);
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
