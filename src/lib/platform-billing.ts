import { and, eq } from "drizzle-orm";
import { v4 as uuid } from "uuid";
import { db, schema } from "@/db/client";
import type { PlatformContext } from "./platform-context";
import { getUsageSummary, type UsageEventType } from "./platform-usage";
import { ensureMonthlyCreditGrant } from "./platform-credits";

type BillingPlanRow = typeof schema.billingPlans.$inferSelect;
type TenantSubscriptionRow = typeof schema.tenantSubscriptions.$inferSelect;

export type BillingPlanView = {
  id: string;
  slug: string;
  name: string;
  monthlyPriceCents: number;
  currency: string;
  projectLimit: number;
  monthlyJobLimit: number;
  includedBillableUnits: number;
  overageUnitPriceCents: number;
  features: string[];
};

export type SubscriptionView = {
  id: string;
  status: TenantSubscriptionRow["status"];
  currentPeriodStart: string;
  currentPeriodEnd: string;
  canceledAt: string | null;
};

export type BillableUsageLine = {
  eventType: UsageEventType;
  quantity: number;
  billableUnits: number;
  weight: number;
};

export type BillingOverview = {
  plan: BillingPlanView;
  subscription: SubscriptionView;
  plans: BillingPlanView[];
  billableUsage: {
    periodStart: string;
    periodEnd: string;
    includedUnits: number;
    usedUnits: number;
    overageUnits: number;
    monthlyPriceCents: number;
    overageUnitPriceCents: number;
    estimatedOverageCents: number;
    estimatedTotalCents: number;
    lines: BillableUsageLine[];
  };
};

const defaultPlans = [
  {
    slug: "starter",
    name: "Starter",
    monthlyPriceCents: 0,
    currency: "USD",
    projectLimit: 5,
    monthlyJobLimit: 40,
    includedBillableUnits: 50,
    overageUnitPriceCents: 0,
    features: ["本地/小团队试用", "基础短剧改编", "Mock 与真实引擎共用额度"],
  },
  {
    slug: "studio",
    name: "Studio",
    monthlyPriceCents: 9900,
    currency: "USD",
    projectLimit: 25,
    monthlyJobLimit: 200,
    includedBillableUnits: 300,
    overageUnitPriceCents: 25,
    features: ["适合内容工作室", "API key 接入", "本地化与交付资产导出"],
  },
  {
    slug: "scale",
    name: "Scale",
    monthlyPriceCents: 29900,
    currency: "USD",
    projectLimit: 100,
    monthlyJobLimit: 1000,
    includedBillableUnits: 1800,
    overageUnitPriceCents: 15,
    features: ["适合批量生产", "更高月度任务额度", "后续可接 SLA 与企业结算"],
  },
] as const;

function periodStart(): Date {
  const value = new Date();
  value.setDate(1);
  value.setHours(0, 0, 0, 0);
  return value;
}

function periodEnd(start = periodStart()): Date {
  return new Date(
    start.getFullYear(),
    start.getMonth() + 1,
    1,
    0,
    0,
    0,
    0
  );
}

function parseFeatures(value: string | null): string[] {
  if (!value) return [];
  try {
    const parsed = JSON.parse(value) as unknown;
    return Array.isArray(parsed)
      ? parsed.filter((item): item is string => typeof item === "string")
      : [];
  } catch {
    return [];
  }
}

function planToView(row: BillingPlanRow): BillingPlanView {
  return {
    id: row.id,
    slug: row.slug,
    name: row.name,
    monthlyPriceCents: row.monthlyPriceCents,
    currency: row.currency,
    projectLimit: row.projectLimit,
    monthlyJobLimit: row.monthlyJobLimit,
    includedBillableUnits: row.includedBillableUnits,
    overageUnitPriceCents: row.overageUnitPriceCents,
    features: parseFeatures(row.featuresJson),
  };
}

function subscriptionToView(row: TenantSubscriptionRow): SubscriptionView {
  return {
    id: row.id,
    status: row.status,
    currentPeriodStart: row.currentPeriodStart.toISOString(),
    currentPeriodEnd: row.currentPeriodEnd.toISOString(),
    canceledAt: row.canceledAt ? row.canceledAt.toISOString() : null,
  };
}

async function ensureDefaultBillingPlans(): Promise<BillingPlanRow[]> {
  const rows: BillingPlanRow[] = [];
  for (const plan of defaultPlans) {
    const existing = await db.query.billingPlans.findFirst({
      where: eq(schema.billingPlans.slug, plan.slug),
    });
    const now = new Date();
    const values = {
      name: plan.name,
      monthlyPriceCents: plan.monthlyPriceCents,
      currency: plan.currency,
      projectLimit: plan.projectLimit,
      monthlyJobLimit: plan.monthlyJobLimit,
      includedBillableUnits: plan.includedBillableUnits,
      overageUnitPriceCents: plan.overageUnitPriceCents,
      featuresJson: JSON.stringify(plan.features, null, 2),
      updatedAt: now,
    };
    if (existing) {
      await db
        .update(schema.billingPlans)
        .set(values)
        .where(eq(schema.billingPlans.id, existing.id));
      rows.push({ ...existing, ...values });
      continue;
    }
    const id = uuid();
    await db.insert(schema.billingPlans).values({
      id,
      slug: plan.slug,
      ...values,
      createdAt: now,
    });
    const created = await db.query.billingPlans.findFirst({
      where: eq(schema.billingPlans.id, id),
    });
    if (!created) throw new Error("billing plan insert failed");
    rows.push(created);
  }
  return rows;
}

async function syncTenantPlanLimits(
  tenantId: string,
  plan: BillingPlanRow
): Promise<void> {
  await db
    .update(schema.tenants)
    .set({
      projectLimit: plan.projectLimit,
      monthlyJobLimit: plan.monthlyJobLimit,
      updatedAt: new Date(),
    })
    .where(eq(schema.tenants.id, tenantId));
}

async function ensureTenantSubscription(
  context: PlatformContext,
  plans: BillingPlanRow[]
): Promise<{ subscription: TenantSubscriptionRow; plan: BillingPlanRow }> {
  const existing = await db.query.tenantSubscriptions.findFirst({
    where: and(
      eq(schema.tenantSubscriptions.tenantId, context.tenant.id),
      eq(schema.tenantSubscriptions.status, "active")
    ),
  });
  if (existing) {
    const plan = await db.query.billingPlans.findFirst({
      where: eq(schema.billingPlans.id, existing.planId),
    });
    if (plan) return { subscription: existing, plan };
  }

  const plan =
    plans.find((item) => item.slug === "studio") ??
    plans[0];
  if (!plan) throw new Error("billing plan missing");
  const start = periodStart();
  const now = new Date();
  const id = uuid();
  await db.insert(schema.tenantSubscriptions).values({
    id,
    tenantId: context.tenant.id,
    planId: plan.id,
    status: "active",
    currentPeriodStart: start,
    currentPeriodEnd: periodEnd(start),
    createdAt: now,
    updatedAt: now,
  });
  await syncTenantPlanLimits(context.tenant.id, plan);
  const created = await db.query.tenantSubscriptions.findFirst({
    where: eq(schema.tenantSubscriptions.id, id),
  });
  if (!created) throw new Error("tenant subscription insert failed");
  return { subscription: created, plan };
}

function calculateBillableUsage(
  plan: BillingPlanRow,
  summary: Awaited<ReturnType<typeof getUsageSummary>>
): BillingOverview["billableUsage"] {
  const lines: BillableUsageLine[] = summary.totals.map((item) => {
    const billableUnits = item.billableUnits;
    const weight =
      item.quantity > 0
        ? Number((billableUnits / item.quantity).toFixed(2))
        : billableUnits;
    return {
      eventType: item.eventType,
      quantity: item.quantity,
      weight,
      billableUnits,
    };
  });
  const usedUnits = lines.reduce((sum, line) => sum + line.billableUnits, 0);
  const overageUnits = Math.max(0, usedUnits - plan.includedBillableUnits);
  const estimatedOverageCents = overageUnits * plan.overageUnitPriceCents;
  return {
    periodStart: summary.since,
    periodEnd: summary.until,
    includedUnits: plan.includedBillableUnits,
    usedUnits,
    overageUnits,
    monthlyPriceCents: plan.monthlyPriceCents,
    overageUnitPriceCents: plan.overageUnitPriceCents,
    estimatedOverageCents,
    estimatedTotalCents: plan.monthlyPriceCents + estimatedOverageCents,
    lines,
  };
}

export async function getBillingOverview(
  context: PlatformContext
): Promise<BillingOverview> {
  const plans = await ensureDefaultBillingPlans();
  const { subscription, plan } = await ensureTenantSubscription(context, plans);
  await ensureMonthlyCreditGrant({
    context,
    subscriptionId: subscription.id,
    periodStart: subscription.currentPeriodStart.toISOString(),
    credits: plan.includedBillableUnits,
  });
  const usage = await getUsageSummary(context, subscription.currentPeriodStart);
  return {
    plan: planToView(plan),
    subscription: subscriptionToView(subscription),
    plans: plans.map(planToView),
    billableUsage: calculateBillableUsage(plan, usage),
  };
}

export async function switchTenantPlan(
  context: PlatformContext,
  planSlug: string
): Promise<BillingOverview> {
  const plans = await ensureDefaultBillingPlans();
  const plan = plans.find((item) => item.slug === planSlug);
  if (!plan) throw new Error("billing plan not found");
  const now = new Date();
  await db
    .update(schema.tenantSubscriptions)
    .set({
      status: "canceled",
      canceledAt: now,
      updatedAt: now,
    })
    .where(
      and(
        eq(schema.tenantSubscriptions.tenantId, context.tenant.id),
        eq(schema.tenantSubscriptions.status, "active")
      )
    );
  const start = periodStart();
  await db.insert(schema.tenantSubscriptions).values({
    id: uuid(),
    tenantId: context.tenant.id,
    planId: plan.id,
    status: "active",
    currentPeriodStart: start,
    currentPeriodEnd: periodEnd(start),
    createdAt: now,
    updatedAt: now,
  });
  await syncTenantPlanLimits(context.tenant.id, plan);
  return getBillingOverview(context);
}
