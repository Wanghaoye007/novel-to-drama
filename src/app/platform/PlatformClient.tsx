"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { ArrowLeft, KeyRound, Plus, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { ApiKeyView } from "@/lib/platform-context";
import type { UsageSummary } from "@/lib/platform-usage";

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
  return new Date(value).toLocaleString();
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

export function PlatformClient({
  tenant,
  user,
  apiKeys,
  usage,
}: {
  tenant: TenantView;
  user: UserView;
  apiKeys: ApiKeyView[];
  usage: UsageSummary;
}) {
  const [keys, setKeys] = useState(apiKeys);
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

  const activeKeys = keys.filter((key) => !key.revokedAt).length;

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-8">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">平台设置</h1>
          <p className="text-sm text-gray-500">
            {tenant.name} · {user.email}
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
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <section className="grid gap-3 md:grid-cols-4">
        <Card className="gap-2 p-4">
          <div className="text-sm text-gray-500">租户</div>
          <div className="truncate text-lg font-semibold">{tenant.slug}</div>
        </Card>
        <Card className="gap-2 p-4">
          <div className="text-sm text-gray-500">项目额度</div>
          <div className="text-lg font-semibold">{tenant.projectLimit}</div>
        </Card>
        <Card className="gap-2 p-4">
          <div className="text-sm text-gray-500">月度任务</div>
          <div className="text-lg font-semibold">{tenant.monthlyJobLimit}</div>
        </Card>
        <Card className="gap-2 p-4">
          <div className="text-sm text-gray-500">活跃 Key</div>
          <div className="text-lg font-semibold">{activeKeys}</div>
        </Card>
      </section>

      <Card className="gap-4 p-4">
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
          <div className="rounded-md border bg-gray-50 p-3">
            <div className="mb-1 text-xs text-gray-500">只显示一次</div>
            <code className="block break-all text-xs">{newToken}</code>
          </div>
        )}
        <div className="overflow-x-auto">
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

      <Card className="gap-4 p-4">
        <h2 className="font-semibold">本月用量</h2>
        <div className="grid gap-3 md:grid-cols-3">
          {usage.totals.map((item) => (
            <div key={item.eventType} className="rounded-md border p-3">
              <div className="text-sm text-gray-500">
                {usageLabel(item.eventType)}
              </div>
              <div className="text-xl font-semibold">{item.quantity}</div>
              <div className="text-xs text-gray-500">{item.count} 条记录</div>
            </div>
          ))}
          {usage.totals.length === 0 && (
            <div className="text-sm text-gray-500">暂无用量</div>
          )}
        </div>
      </Card>
    </main>
  );
}
