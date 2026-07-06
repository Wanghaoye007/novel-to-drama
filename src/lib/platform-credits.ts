import { and, desc, eq } from "drizzle-orm";
import { v4 as uuid } from "uuid";
import { db, schema } from "@/db/client";
import type { PlatformContext } from "./platform-context";

type CreditPackageRow = typeof schema.creditPackages.$inferSelect;
type CreditLedgerRow = typeof schema.creditLedger.$inferSelect;
type CheckoutSessionRow = typeof schema.paymentCheckoutSessions.$inferSelect;
type PaymentInvoiceRow = typeof schema.paymentInvoices.$inferSelect;

export class PaymentRequiredError extends Error {
  status = 402;
}

export type CreditPackageView = {
  id: string;
  slug: string;
  name: string;
  credits: number;
  priceCents: number;
  currency: string;
  active: boolean;
};

export type CreditLedgerView = {
  id: string;
  sourceType: CreditLedgerRow["sourceType"];
  creditsDelta: number;
  balanceAfter: number;
  referenceKey: string | null;
  metadata: unknown;
  createdAt: string;
};

export type CheckoutSessionView = {
  id: string;
  provider: CheckoutSessionRow["provider"];
  status: CheckoutSessionRow["status"];
  credits: number;
  amountCents: number;
  currency: string;
  checkoutUrl: string | null;
  createdAt: string;
  completedAt: string | null;
};

export type PaymentInvoiceView = {
  id: string;
  provider: PaymentInvoiceRow["provider"];
  status: PaymentInvoiceRow["status"];
  credits: number;
  amountCents: number;
  currency: string;
  hostedInvoiceUrl: string | null;
  paidAt: string | null;
  createdAt: string;
};

export type CreditOverview = {
  balance: number;
  packages: CreditPackageView[];
  recentLedger: CreditLedgerView[];
  recentCheckoutSessions: CheckoutSessionView[];
  recentInvoices: PaymentInvoiceView[];
};

const defaultCreditPackages = [
  {
    slug: "credits_100",
    name: "100 credits",
    credits: 100,
    priceCents: 1900,
    currency: "USD",
    sortOrder: 10,
  },
  {
    slug: "credits_500",
    name: "500 credits",
    credits: 500,
    priceCents: 7900,
    currency: "USD",
    sortOrder: 20,
  },
  {
    slug: "credits_2000",
    name: "2000 credits",
    credits: 2000,
    priceCents: 24900,
    currency: "USD",
    sortOrder: 30,
  },
] as const;

function parseMetadata(value: string | null): unknown {
  if (!value) return null;
  try {
    return JSON.parse(value) as unknown;
  } catch {
    return value;
  }
}

function dateToIso(value: Date | null): string | null {
  return value ? value.toISOString() : null;
}

function packageToView(row: CreditPackageRow): CreditPackageView {
  return {
    id: row.id,
    slug: row.slug,
    name: row.name,
    credits: row.credits,
    priceCents: row.priceCents,
    currency: row.currency,
    active: row.active,
  };
}

function ledgerToView(row: CreditLedgerRow): CreditLedgerView {
  return {
    id: row.id,
    sourceType: row.sourceType,
    creditsDelta: row.creditsDelta,
    balanceAfter: row.balanceAfter,
    referenceKey: row.referenceKey,
    metadata: parseMetadata(row.metadataJson),
    createdAt: row.createdAt.toISOString(),
  };
}

function checkoutToView(row: CheckoutSessionRow): CheckoutSessionView {
  return {
    id: row.id,
    provider: row.provider,
    status: row.status,
    credits: row.credits,
    amountCents: row.amountCents,
    currency: row.currency,
    checkoutUrl: row.checkoutUrl,
    createdAt: row.createdAt.toISOString(),
    completedAt: dateToIso(row.completedAt),
  };
}

function invoiceToView(row: PaymentInvoiceRow): PaymentInvoiceView {
  return {
    id: row.id,
    provider: row.provider,
    status: row.status,
    credits: row.credits,
    amountCents: row.amountCents,
    currency: row.currency,
    hostedInvoiceUrl: row.hostedInvoiceUrl,
    paidAt: dateToIso(row.paidAt),
    createdAt: row.createdAt.toISOString(),
  };
}

async function ensureDefaultCreditPackages(): Promise<CreditPackageRow[]> {
  const rows: CreditPackageRow[] = [];
  for (const pack of defaultCreditPackages) {
    const existing = await db.query.creditPackages.findFirst({
      where: eq(schema.creditPackages.slug, pack.slug),
    });
    const now = new Date();
    const values = {
      name: pack.name,
      credits: pack.credits,
      priceCents: pack.priceCents,
      currency: pack.currency,
      active: true,
      sortOrder: pack.sortOrder,
      updatedAt: now,
    };
    if (existing) {
      await db
        .update(schema.creditPackages)
        .set(values)
        .where(eq(schema.creditPackages.id, existing.id));
      rows.push({ ...existing, ...values });
      continue;
    }
    const id = uuid();
    await db.insert(schema.creditPackages).values({
      id,
      slug: pack.slug,
      ...values,
      createdAt: now,
    });
    const created = await db.query.creditPackages.findFirst({
      where: eq(schema.creditPackages.id, id),
    });
    if (!created) throw new Error("credit package insert failed");
    rows.push(created);
  }
  return rows.sort((a, b) => a.sortOrder - b.sortOrder);
}

export async function getCreditBalance(tenantId: string): Promise<number> {
  const rows = await db.query.creditLedger.findMany({
    where: eq(schema.creditLedger.tenantId, tenantId),
  });
  return rows.reduce((sum, row) => sum + row.creditsDelta, 0);
}

async function writeLedgerEntry({
  tenantId,
  userId,
  sourceType,
  creditsDelta,
  usageEventId,
  checkoutSessionId,
  invoiceId,
  referenceKey,
  metadata,
}: {
  tenantId: string;
  userId?: string | null;
  sourceType: CreditLedgerRow["sourceType"];
  creditsDelta: number;
  usageEventId?: string | null;
  checkoutSessionId?: string | null;
  invoiceId?: string | null;
  referenceKey?: string | null;
  metadata?: unknown;
}): Promise<CreditLedgerRow> {
  const balance = await getCreditBalance(tenantId);
  const row = {
    id: uuid(),
    tenantId,
    userId: userId ?? null,
    sourceType,
    creditsDelta,
    balanceAfter: balance + creditsDelta,
    usageEventId,
    checkoutSessionId,
    invoiceId,
    referenceKey,
    metadataJson: metadata == null ? null : JSON.stringify(metadata, null, 2),
    createdAt: new Date(),
  };
  await db.insert(schema.creditLedger).values(row);
  const created = await db.query.creditLedger.findFirst({
    where: eq(schema.creditLedger.id, row.id),
  });
  if (!created) throw new Error("credit ledger insert failed");
  return created;
}

export async function ensureMonthlyCreditGrant({
  context,
  subscriptionId,
  periodStart,
  credits,
}: {
  context: PlatformContext;
  subscriptionId: string;
  periodStart: string;
  credits: number;
}): Promise<void> {
  if (credits <= 0) return;
  const referencePrefix = `monthly_grant:${periodStart}:`;
  const grantEntries = await db.query.creditLedger.findMany({
    where: eq(schema.creditLedger.tenantId, context.tenant.id),
  });
  const grantedThisPeriod = grantEntries
    .filter(
      (entry) =>
        entry.sourceType === "monthly_grant" &&
        entry.referenceKey?.startsWith(referencePrefix)
    )
    .reduce((sum, entry) => sum + Math.max(0, entry.creditsDelta), 0);
  if (grantedThisPeriod >= credits) return;
  const creditsDelta = credits - grantedThisPeriod;
  await writeLedgerEntry({
    tenantId: context.tenant.id,
    userId: context.user.id,
    sourceType: "monthly_grant",
    creditsDelta,
    referenceKey: `${referencePrefix}subscription:${subscriptionId}:total:${credits}`,
    metadata: { subscriptionId, periodStart, targetCredits: credits },
  });
}

export async function settleUsageCredits({
  context,
  usageEventId,
  billableUnits,
  metadata,
}: {
  context: PlatformContext;
  usageEventId: string;
  billableUnits: number;
  metadata?: unknown;
}): Promise<void> {
  if (billableUnits <= 0) return;
  const balance = await getCreditBalance(context.tenant.id);
  if (
    process.env.NOVEL_DRAMA_REQUIRE_CREDITS === "1" &&
    balance < billableUnits
  ) {
    throw new PaymentRequiredError("insufficient credits");
  }
  await writeLedgerEntry({
    tenantId: context.tenant.id,
    userId: context.user.id,
    sourceType: "usage_debit",
    creditsDelta: -billableUnits,
    usageEventId,
    referenceKey: `usage:${usageEventId}`,
    metadata,
  });
}

async function ensurePaymentCustomer(
  context: PlatformContext,
  provider: CheckoutSessionRow["provider"]
): Promise<void> {
  const existing = await db.query.paymentCustomers.findFirst({
    where: and(
      eq(schema.paymentCustomers.tenantId, context.tenant.id),
      eq(schema.paymentCustomers.provider, provider)
    ),
  });
  if (existing) return;
  const now = new Date();
  await db.insert(schema.paymentCustomers).values({
    id: uuid(),
    tenantId: context.tenant.id,
    provider,
    billingEmail: context.user.email,
    metadataJson: JSON.stringify({ source: "platform_template" }, null, 2),
    createdAt: now,
    updatedAt: now,
  });
}

export async function createCreditCheckoutSession(
  context: PlatformContext,
  packageSlug: string,
  provider: CheckoutSessionRow["provider"] = "mock"
): Promise<CheckoutSessionView> {
  const packages = await ensureDefaultCreditPackages();
  const pack = packages.find((item) => item.slug === packageSlug && item.active);
  if (!pack) throw new Error("credit package not found");
  await ensurePaymentCustomer(context, provider);
  const now = new Date();
  const id = uuid();
  const checkoutUrl =
    provider === "mock" ? `/api/platform/checkout/${id}/complete` : null;
  await db.insert(schema.paymentCheckoutSessions).values({
    id,
    tenantId: context.tenant.id,
    packageId: pack.id,
    provider,
    status: "open",
    credits: pack.credits,
    amountCents: pack.priceCents,
    currency: pack.currency,
    checkoutUrl,
    metadataJson: JSON.stringify({ packageSlug }, null, 2),
    expiresAt: new Date(now.getTime() + 30 * 60 * 1000),
    createdAt: now,
    updatedAt: now,
  });
  const created = await db.query.paymentCheckoutSessions.findFirst({
    where: eq(schema.paymentCheckoutSessions.id, id),
  });
  if (!created) throw new Error("checkout session insert failed");
  return checkoutToView(created);
}

async function completeCheckoutSessionInternal(
  session: CheckoutSessionRow,
  userId?: string | null
): Promise<PaymentInvoiceRow> {
  if (session.status === "paid") {
    const existing = await db.query.paymentInvoices.findFirst({
      where: eq(schema.paymentInvoices.checkoutSessionId, session.id),
    });
    if (existing) return existing;
  }
  if (session.status !== "open" && session.status !== "paid") {
    throw new Error(`checkout session is ${session.status}`);
  }
  const now = new Date();
  await db
    .update(schema.paymentCheckoutSessions)
    .set({ status: "paid", completedAt: now, updatedAt: now })
    .where(eq(schema.paymentCheckoutSessions.id, session.id));

  const invoiceId = uuid();
  await db.insert(schema.paymentInvoices).values({
    id: invoiceId,
    tenantId: session.tenantId,
    checkoutSessionId: session.id,
    provider: session.provider,
    status: "paid",
    credits: session.credits,
    amountCents: session.amountCents,
    currency: session.currency,
    hostedInvoiceUrl: `/api/platform/invoices/${invoiceId}`,
    metadataJson: session.metadataJson,
    paidAt: now,
    createdAt: now,
    updatedAt: now,
  });
  const invoice = await db.query.paymentInvoices.findFirst({
    where: eq(schema.paymentInvoices.id, invoiceId),
  });
  if (!invoice) throw new Error("payment invoice insert failed");
  await writeLedgerEntry({
    tenantId: session.tenantId,
    userId,
    sourceType: "top_up",
    creditsDelta: session.credits,
    checkoutSessionId: session.id,
    invoiceId: invoice.id,
    referenceKey: `checkout:${session.id}:paid`,
    metadata: {
      provider: session.provider,
      amountCents: session.amountCents,
      currency: session.currency,
    },
  });
  return invoice;
}

export async function completeCreditCheckoutSession(
  context: PlatformContext,
  sessionId: string
): Promise<CreditOverview> {
  const session = await db.query.paymentCheckoutSessions.findFirst({
    where: and(
      eq(schema.paymentCheckoutSessions.id, sessionId),
      eq(schema.paymentCheckoutSessions.tenantId, context.tenant.id)
    ),
  });
  if (!session) throw new Error("checkout session not found");
  await completeCheckoutSessionInternal(session, context.user.id);
  return getCreditOverview(context);
}

export async function processPaymentWebhook(payload: {
  provider?: CheckoutSessionRow["provider"];
  eventType?: string;
  checkoutSessionId?: string;
  externalEventId?: string;
  raw?: unknown;
}): Promise<{ ok: boolean; webhookEventId: string }> {
  const eventId = uuid();
  let tenantId: string | null = null;
  let session: CheckoutSessionRow | undefined;
  if (payload.checkoutSessionId) {
    session = await db.query.paymentCheckoutSessions.findFirst({
      where: eq(schema.paymentCheckoutSessions.id, payload.checkoutSessionId),
    });
    tenantId = session?.tenantId ?? null;
  }
  const provider = payload.provider ?? session?.provider ?? "mock";
  if (payload.externalEventId) {
    const existing = await db.query.paymentWebhookEvents.findFirst({
      where: and(
        eq(schema.paymentWebhookEvents.provider, provider),
        eq(schema.paymentWebhookEvents.externalEventId, payload.externalEventId)
      ),
    });
    if (existing?.status === "processed" || existing?.status === "received") {
      return { ok: true, webhookEventId: existing.id };
    }
  }
  const now = new Date();
  await db.insert(schema.paymentWebhookEvents).values({
    id: eventId,
    tenantId,
    checkoutSessionId: session?.id ?? null,
    provider,
    eventType: payload.eventType ?? "unknown",
    status: "received",
    externalEventId: payload.externalEventId,
    payloadJson: JSON.stringify(payload.raw ?? payload, null, 2),
    createdAt: now,
  });
  try {
    if (payload.eventType === "checkout.paid" && session) {
      await completeCheckoutSessionInternal(session);
    }
    await db
      .update(schema.paymentWebhookEvents)
      .set({ status: "processed", processedAt: new Date() })
      .where(eq(schema.paymentWebhookEvents.id, eventId));
    return { ok: true, webhookEventId: eventId };
  } catch (error) {
    await db
      .update(schema.paymentWebhookEvents)
      .set({
        status: "failed",
        errorText: error instanceof Error ? error.message : String(error),
        processedAt: new Date(),
      })
      .where(eq(schema.paymentWebhookEvents.id, eventId));
    throw error;
  }
}

export async function getCreditOverview(
  context: PlatformContext
): Promise<CreditOverview> {
  const packages = await ensureDefaultCreditPackages();
  const [balance, ledger, sessions, invoices] = await Promise.all([
    getCreditBalance(context.tenant.id),
    db.query.creditLedger.findMany({
      where: eq(schema.creditLedger.tenantId, context.tenant.id),
      orderBy: [desc(schema.creditLedger.createdAt)],
      limit: 30,
    }),
    db.query.paymentCheckoutSessions.findMany({
      where: eq(schema.paymentCheckoutSessions.tenantId, context.tenant.id),
      orderBy: [desc(schema.paymentCheckoutSessions.createdAt)],
      limit: 10,
    }),
    db.query.paymentInvoices.findMany({
      where: eq(schema.paymentInvoices.tenantId, context.tenant.id),
      orderBy: [desc(schema.paymentInvoices.createdAt)],
      limit: 10,
    }),
  ]);
  return {
    balance,
    packages: packages.map(packageToView),
    recentLedger: ledger.map(ledgerToView),
    recentCheckoutSessions: sessions.map(checkoutToView),
    recentInvoices: invoices.map(invoiceToView),
  };
}
