"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Building2, LogIn, LogOut, UserRound } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export type WorkspaceSessionView = {
  userEmail: string;
  tenantSlug: string;
  tenantName: string;
  source: "browser" | "api_key" | "default";
};

export function WorkspaceSessionClient({
  session,
  compact = false,
}: {
  session: WorkspaceSessionView;
  compact?: boolean;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function saveSession(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    setError(null);
    const form = new FormData(event.currentTarget);
    try {
      const res = await fetch("/api/platform/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: String(form.get("email") ?? ""),
          tenantSlug: String(form.get("tenantSlug") ?? ""),
          tenantName: String(form.get("tenantName") ?? ""),
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error ?? "switch workspace failed");
      setMessage("工作区已切换。");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function clearSession() {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const res = await fetch("/api/platform/session", { method: "DELETE" });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error ?? "clear session failed");
      setMessage("已恢复默认工作区。");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="gap-4 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <Building2 className="mt-1 size-4 shrink-0 text-gray-500" />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="font-semibold">工作区会话</h2>
              <Badge variant="outline">{session.source}</Badge>
            </div>
            <p className="truncate text-sm text-gray-500">
              {session.tenantName} · {session.userEmail}
            </p>
          </div>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={busy}
          onClick={clearSession}
        >
          <LogOut className="size-4" />
          恢复默认
        </Button>
      </div>

      <form
        onSubmit={saveSession}
        className={
          compact
            ? "grid gap-3 md:grid-cols-[minmax(0,1fr)_180px_auto]"
            : "grid gap-3 md:grid-cols-[minmax(0,1fr)_180px_minmax(0,1fr)_auto]"
        }
      >
        <div>
          <Label htmlFor="session-email">邮箱</Label>
          <div className="relative">
            <UserRound className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-gray-400" />
            <Input
              id="session-email"
              name="email"
              type="email"
              defaultValue={session.userEmail}
              className="pl-9"
              disabled={busy}
              required
            />
          </div>
        </div>
        <div>
          <Label htmlFor="session-tenant">工作区</Label>
          <Input
            id="session-tenant"
            name="tenantSlug"
            defaultValue={session.tenantSlug}
            disabled={busy}
            required
          />
        </div>
        {!compact && (
          <div>
            <Label htmlFor="session-tenant-name">显示名称</Label>
            <Input
              id="session-tenant-name"
              name="tenantName"
              defaultValue={session.tenantName}
              disabled={busy}
            />
          </div>
        )}
        <div className="flex items-end">
          <Button type="submit" className="w-full" disabled={busy}>
            <LogIn className="size-4" />
            进入
          </Button>
        </div>
      </form>

      {(message || error) && (
        <div
          className={`rounded-md border px-3 py-2 text-sm ${
            error
              ? "border-red-200 bg-red-50 text-red-700"
              : "border-emerald-200 bg-emerald-50 text-emerald-700"
          }`}
        >
          {error ?? message}
        </div>
      )}
    </Card>
  );
}
