"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  CreditCard,
  KeyRound,
  Plus,
  ReceiptText,
  Trash2,
  WalletCards,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { BillingOverview } from "@/lib/platform-billing";
import type { CreditOverview } from "@/lib/platform-credits";
import type { ApiKeyView, TenantMemberView } from "@/lib/platform-context";
import type { PlatformPageSession } from "@/lib/platform-page-context";
import type { UsageSummary } from "@/lib/platform-usage";
import { WorkspaceMembersClient } from "./WorkspaceMembersClient";
import { WorkspaceSessionClient } from "./WorkspaceSessionClient";

type TenantView = {
  id: string;
  name: string;
  slug: string;
  projectLimit: number;
  monthlyJobLimit: number;
};

type UserView = {
  id: string;
  email: string;
};

function formatDate(value: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}

function usageLabel(eventType: string): string {
  const labels: Record<string, string> = {
    project_create: "项目创建",
    round_start: "轮次启动",
    quality_samples_start: "样本质检",
    video_brief_export: "视频 brief",
    localization_export: "本地化包",
    delivery_preflight: "交付预检",
    delivery_export: "交付包",
  };
  return labels[eventType] ?? eventType;
}

function formatMoney(cents: number, currency: string): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(cents / 100);
}

function creditSourceLabel(sourceType: string): string {
  const labels: Record<string, string> = {
    monthly_grant: "套餐赠点",
    top_up: "充值",
    usage_debit: "用量扣点",
    manual_adjustment: "人工调整",
    refund: "退款",
  };
  return labels[sourceType] ?? sourceType;
}

export function PlatformClient({
  tenant,
  user,
  apiKeys,
  usage,
  billing,
  credits,
  session,
  members,
  canManageMembers,
}: {
  tenant: TenantView;
  user: UserView;
  apiKeys: ApiKeyView[];
  usage: UsageSummary;
  billing: BillingOverview;
  credits: CreditOverview;
  session: PlatformPageSession;
  members: TenantMemberView[];
  canManageMembers: boolean;
}) {
  const [keys, setKeys] = useState(apiKeys);
  const [billingState, setBillingState] = useState(billing);
  const [creditState, setCreditState] = useState(credits);
  const [checkoutMessage, setCheckoutMessage] = useState<string | null>(null);
  const [newToken, setNewToken] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function createKey(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNewToken(null);
    const form = new FormData(event.currentTarget);
    const name = String(form.get("name") ?? "");
    try {
      const res = await fetch("/api/platform/api-keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "create key failed");
      setKeys((current) => [data.apiKey as ApiKeyView, ...current]);
      setNewToken(String(data.token));
      event.currentTarget.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function revokeKey(id: string) {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`/api/platform/api-keys/${id}`, {
        method: "DELETE",
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error ?? "revoke key failed");
      const revokedAt = new Date().toISOString();
      setKeys((current) =>
        current.map((key) => (key.id === id ? { ...key, revokedAt } : key))
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function switchPlan(planSlug: string) {
    setBusy(true);
    setError(null);
    setCheckoutMessage(null);
    try {
      const res = await fetch("/api/platform/billing", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ planSlug }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "switch plan failed");
      setBillingState(data as BillingOverview);
      const creditRes = await fetch("/api/platform/credits");
      const creditData = await creditRes.json();
      if (creditRes.ok) setCreditState(creditData as CreditOverview);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function buyCredits(packageSlug: string) {
    setBusy(true);
    setError(null);
    setCheckoutMessage(null);
    try {
      const checkoutRes = await fetch("/api/platform/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ packageSlug, provider: "mock" }),
      });
      const checkout = await checkoutRes.json();
      if (!checkoutRes.ok) {
        throw new Error(checkout.error ?? "create checkout failed");
      }
      const completeRes = await fetch(
        `/api/platform/checkout/${checkout.id}/complete`,
        { method: "POST" }
      );
      const overview = await completeRes.json();
      if (!completeRes.ok) {
        throw new Error(overview.error ?? "complete checkout failed");
      }
      setCreditState(overview as CreditOverview);
      setCheckoutMessage("模拟支付完成，点数已入账。");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const activeKeys = keys.filter((key) => !key.revokedAt).length;
  const plan = billingState.plan;
  const billable = billingState.billableUsage;

  return (
    <section className="page-shell">
      <header className="page-header">
        <div>
          <div className="page-kicker">
            {tenant.name} · {user.email}
          </div>
          <h1 className="page-title">平台与点数</h1>
          <p className="page-description">
            管理工作区会话、成员、套餐、点数钱包、API Key 和本月用量。当前支付为模拟模板，可继续替换真实支付渠道。
          </p>
        </div>
        <Link href="/">
          <Button variant="outline">
            <ArrowLeft className="size-4" />
            项目列表
          </Button>
        </Link>
      </header>

      {error && (
        <div className="rounded-[var(--radius-md)] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <WorkspaceSessionClient session={session} />

      <WorkspaceMembersClient
        members={members}
        canManageMembers={canManageMembers}
      />

      <section className="grid gap-3 md:grid-cols-4">
        <Card className="gap-2 p-5">
          <div className="text-sm text-gray-500">租户</div>
          <div className="truncate text-lg font-semibold">{tenant.slug}</div>
        </Card>
        <Card className="gap-2 p-5">
          <div className="text-sm text-gray-500">项目额度</div>
          <div className="text-lg font-semibold">{plan.projectLimit}</div>
        </Card>
        <Card className="gap-2 p-5">
          <div className="text-sm text-gray-500">月度任务</div>
          <div className="text-lg font-semibold">{plan.monthlyJobLimit}</div>
        </Card>
        <Card className="gap-2 p-5">
          <div className="text-sm text-gray-500">活跃 Key</div>
          <div className="text-lg font-semibold">{activeKeys}</div>
        </Card>
      </section>

      <Card className="gap-5 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-semibold">套餐与账单</h2>
            <p className="text-sm text-gray-500">
              {billingState.subscription.status} ·{" "}
              {formatDate(billingState.subscription.currentPeriodStart)} -{" "}
              {formatDate(billingState.subscription.currentPeriodEnd)}
            </p>
          </div>
          <Badge variant="outline">{plan.name}</Badge>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          {billingState.plans.map((item) => {
            const active = item.slug === plan.slug;
            return (
              <div key={item.slug} className="soft-panel">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <div className="font-medium">{item.name}</div>
                    <div className="text-sm text-gray-500">
                      {formatMoney(item.monthlyPriceCents, item.currency)}/月
                    </div>
                  </div>
                  <Badge variant={active ? "default" : "outline"}>
                    {active ? "current" : item.slug}
                  </Badge>
                </div>
                <div className="mt-3 grid gap-1 text-xs text-gray-600">
                  <span>项目 {item.projectLimit}</span>
                  <span>月度任务 {item.monthlyJobLimit}</span>
                  <span>包含 {item.includedBillableUnits} billable units</span>
                  <span>
                    超额 {formatMoney(item.overageUnitPriceCents, item.currency)}
                    /unit
                  </span>
                </div>
                {item.features.length > 0 && (
                  <div className="mt-3 grid gap-1 text-xs text-gray-500">
                    {item.features.map((feature) => (
                      <span key={feature}>{feature}</span>
                    ))}
                  </div>
                )}
                <Button
                  type="button"
                  variant={active ? "secondary" : "outline"}
                  size="sm"
                  className="mt-3 w-full"
                  disabled={busy || active}
                  onClick={() => switchPlan(item.slug)}
                >
                  {active ? "当前套餐" : "切换"}
                </Button>
              </div>
            );
          })}
        </div>

        <div className="grid gap-3 md:grid-cols-4">
          <div className="soft-panel">
            <div className="text-sm text-gray-500">已用 units</div>
            <div className="text-xl font-semibold">{billable.usedUnits}</div>
            <div className="text-xs text-gray-500">
              包含 {billable.includedUnits}
            </div>
          </div>
          <div className="soft-panel">
            <div className="text-sm text-gray-500">超额 units</div>
            <div className="text-xl font-semibold">{billable.overageUnits}</div>
            <div className="text-xs text-gray-500">
              {formatMoney(billable.overageUnitPriceCents, plan.currency)}/unit
            </div>
          </div>
          <div className="soft-panel">
            <div className="text-sm text-gray-500">基础费用</div>
            <div className="text-xl font-semibold">
              {formatMoney(billable.monthlyPriceCents, plan.currency)}
            </div>
          </div>
          <div className="soft-panel">
            <div className="text-sm text-gray-500">预估合计</div>
            <div className="text-xl font-semibold">
              {formatMoney(billable.estimatedTotalCents, plan.currency)}
            </div>
            <div className="text-xs text-gray-500">
              超额 {formatMoney(billable.estimatedOverageCents, plan.currency)}
            </div>
          </div>
        </div>
      </Card>

      <Card className="gap-5 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <WalletCards className="size-4 text-gray-500" />
            <div>
              <h2 className="font-semibold">点数钱包</h2>
              <p className="text-sm text-gray-500">
                1 billable unit = 1 credit
              </p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-500">当前余额</div>
            <div className="text-2xl font-semibold">{creditState.balance}</div>
          </div>
        </div>

        {checkoutMessage && (
          <div className="rounded-[var(--radius-md)] border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            {checkoutMessage}
          </div>
        )}

        <div className="grid gap-3 md:grid-cols-3">
          {creditState.packages.map((pack) => (
            <div key={pack.slug} className="soft-panel">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="font-medium">{pack.name}</div>
                  <div className="text-sm text-gray-500">
                    {pack.credits} credits
                  </div>
                </div>
                <Badge variant="outline">
                  {formatMoney(pack.priceCents, pack.currency)}
                </Badge>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="mt-3 w-full"
                disabled={busy || !pack.active}
                onClick={() => buyCredits(pack.slug)}
              >
                <CreditCard className="size-4" />
                模拟支付
              </Button>
            </div>
          ))}
        </div>

        <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
          <div className="table-shell">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead className="text-xs text-gray-500">
                <tr className="border-b">
                  <th className="py-2 font-medium">类型</th>
                  <th className="py-2 font-medium">变化</th>
                  <th className="py-2 font-medium">余额</th>
                  <th className="py-2 font-medium">时间</th>
                </tr>
              </thead>
              <tbody>
                {creditState.recentLedger.map((entry) => (
                  <tr key={entry.id} className="border-b last:border-0">
                    <td className="py-2">
                      {creditSourceLabel(entry.sourceType)}
                    </td>
                    <td
                      className={`py-2 font-mono text-xs ${
                        entry.creditsDelta >= 0
                          ? "text-emerald-700"
                          : "text-red-700"
                      }`}
                    >
                      {entry.creditsDelta >= 0 ? "+" : ""}
                      {entry.creditsDelta}
                    </td>
                    <td className="py-2">{entry.balanceAfter}</td>
                    <td className="py-2 text-gray-600">
                      {formatDate(entry.createdAt)}
                    </td>
                  </tr>
                ))}
                {creditState.recentLedger.length === 0 && (
                  <tr>
                    <td className="py-3 text-sm text-gray-500" colSpan={4}>
                      暂无点数流水
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="soft-panel">
            <div className="mb-3 flex items-center gap-2">
              <ReceiptText className="size-4 text-gray-500" />
              <h3 className="text-sm font-medium">最近发票</h3>
            </div>
            <div className="grid gap-2">
              {creditState.recentInvoices.map((invoice) => (
                <div
                  key={invoice.id}
                  className="flex items-center justify-between gap-3 border-b pb-2 last:border-0 last:pb-0"
                >
                  <div>
                    <div className="text-sm font-medium">
                      {formatMoney(invoice.amountCents, invoice.currency)}
                    </div>
                    <div className="text-xs text-gray-500">
                      {invoice.credits} credits
                    </div>
                  </div>
                  <Badge variant={invoice.status === "paid" ? "default" : "outline"}>
                    {invoice.status}
                  </Badge>
                </div>
              ))}
              {creditState.recentInvoices.length === 0 && (
                <div className="text-sm text-gray-500">暂无发票</div>
              )}
            </div>
          </div>
        </div>
      </Card>

      <Card className="gap-5 p-5">
        <div className="flex items-center gap-2">
          <KeyRound className="size-4 text-gray-500" />
          <h2 className="font-semibold">API Keys</h2>
        </div>
        <form onSubmit={createKey} className="flex flex-wrap items-end gap-2">
          <div className="min-w-64 flex-1">
            <Label htmlFor="api-key-name">名称</Label>
            <Input
              id="api-key-name"
              name="name"
              placeholder="Production key"
              disabled={busy}
            />
          </div>
          <Button type="submit" disabled={busy}>
            <Plus className="size-4" />
            创建
          </Button>
        </form>
        {newToken && (
          <div className="rounded-[var(--radius-md)] border border-[color:var(--hairline-soft)] bg-[color:var(--surface-embedded)] p-3">
            <div className="mb-1 text-xs text-gray-500">只显示一次</div>
            <code className="block break-all text-xs">{newToken}</code>
          </div>
        )}
        <div className="table-shell">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="text-xs text-gray-500">
              <tr className="border-b">
                <th className="py-2 font-medium">名称</th>
                <th className="py-2 font-medium">前缀</th>
                <th className="py-2 font-medium">状态</th>
                <th className="py-2 font-medium">最近使用</th>
                <th className="py-2 font-medium">创建时间</th>
                <th className="py-2 text-right font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              {keys.map((key) => (
                <tr key={key.id} className="border-b last:border-0">
                  <td className="py-2">{key.name}</td>
                  <td className="py-2 font-mono text-xs">{key.keyPrefix}</td>
                  <td className="py-2">
                    <Badge variant={key.revokedAt ? "outline" : "default"}>
                      {key.revokedAt ? "revoked" : "active"}
                    </Badge>
                  </td>
                  <td className="py-2 text-gray-600">
                    {formatDate(key.lastUsedAt)}
                  </td>
                  <td className="py-2 text-gray-600">
                    {formatDate(key.createdAt)}
                  </td>
                  <td className="py-2 text-right">
                    <Button
                      type="button"
                      variant="outline"
                      size="icon-sm"
                      disabled={busy || Boolean(key.revokedAt)}
                      onClick={() => revokeKey(key.id)}
                      aria-label={`撤销 ${key.name}`}
                      title={`撤销 ${key.name}`}
                    >
                      <Trash2 className="size-4" />
                    </Button>
                  </td>
                </tr>
              ))}
              {keys.length === 0 && (
                <tr>
                  <td className="py-3 text-sm text-gray-500" colSpan={6}>
                    暂无 API key
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <Card className="gap-5 p-5">
        <h2 className="font-semibold">本月用量</h2>
        <div className="grid gap-3 md:grid-cols-3">
          {usage.totals.map((item) => {
            const line = billable.lines.find(
              (candidate) => candidate.eventType === item.eventType
            );
            return (
              <div key={item.eventType} className="soft-panel">
                <div className="text-sm text-gray-500">
                  {usageLabel(item.eventType)}
                </div>
                <div className="text-xl font-semibold">{item.quantity}</div>
                <div className="text-xs text-gray-500">
                  {item.count} 条记录 · {line?.billableUnits ?? 0} units
                </div>
              </div>
            );
          })}
          {usage.totals.length === 0 && (
            <div className="text-sm text-gray-500">暂无用量</div>
          )}
        </div>
      </Card>
    </section>
  );
}
