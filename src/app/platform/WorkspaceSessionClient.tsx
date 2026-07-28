"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Building2, LogIn } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/label";

export type WorkspaceSessionView = {
  userEmail: string;
  tenantSlug: string;
  tenantName: string;
  source: "browser" | "api_key" | "default";
  canSwitchSession: boolean;
  workspaces: Array<{
    id: string;
    slug: string;
    name: string;
    role: "owner" | "admin" | "member";
  }>;
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
  const [selectedWorkspace, setSelectedWorkspace] = useState(
    session.tenantSlug
  );
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setSelectedWorkspace(session.tenantSlug);
  }, [session.tenantSlug]);

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
          tenantSlug: String(form.get("tenantSlug") ?? ""),
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

  return (
    <Card className="gap-5 p-5">
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
        <Badge variant="secondary">
          {session.workspaces.length} 个可访问工作区
        </Badge>
      </div>

      {session.canSwitchSession && (
        <form
          onSubmit={saveSession}
          className={
            compact
              ? "grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]"
              : "grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]"
          }
        >
          <div>
            <Label htmlFor="session-tenant">选择工作区</Label>
            <select
              id="session-tenant"
              name="tenantSlug"
              value={selectedWorkspace}
              onChange={(event) => setSelectedWorkspace(event.target.value)}
              disabled={busy}
              className="mt-1 h-10 w-full rounded-[var(--radius-md)] border border-border bg-card px-3 text-sm text-foreground outline-none transition focus:border-primary focus:ring-4 focus:ring-ring/30"
            >
              {session.workspaces.map((workspace) => (
                <option key={workspace.id} value={workspace.slug}>
                  {workspace.name} · {workspace.role}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <Button
              type="submit"
              className="w-full"
              disabled={busy || selectedWorkspace === session.tenantSlug}
            >
              <LogIn className="size-4" />
              {busy ? "切换中…" : "进入工作区"}
            </Button>
          </div>
        </form>
      )}

      {(message || error) && (
        <div
          className={`rounded-[var(--radius-md)] border px-3 py-2 text-sm ${
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
