"use client";

import { FormEvent, useState } from "react";
import { ShieldCheck, Trash2, UserPlus, UsersRound } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { TenantMemberRole, TenantMemberView } from "@/lib/platform-context";

const roleLabels: Record<TenantMemberRole, string> = {
  owner: "Owner",
  admin: "Admin",
  member: "Member",
};

const roles: TenantMemberRole[] = ["member", "admin", "owner"];

export function WorkspaceMembersClient({
  members: initialMembers,
  canManageMembers,
}: {
  members: TenantMemberView[];
  canManageMembers: boolean;
}) {
  const [members, setMembers] = useState(initialMembers);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function upsertMember(member: TenantMemberView) {
    setMembers((current) => {
      const exists = current.some((item) => item.id === member.id);
      if (exists) {
        return current.map((item) => (item.id === member.id ? member : item));
      }
      return [...current, member];
    });
  }

  async function addMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    setError(null);
    const form = new FormData(event.currentTarget);
    try {
      const res = await fetch("/api/platform/members", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: String(form.get("email") ?? ""),
          role: String(form.get("role") ?? "member"),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "add member failed");
      upsertMember(data as TenantMemberView);
      setMessage("成员已加入工作区。");
      event.currentTarget.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function updateRole(memberId: string, role: TenantMemberRole) {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const res = await fetch(`/api/platform/members/${memberId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "update member failed");
      upsertMember(data as TenantMemberView);
      setMessage("成员角色已更新。");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function removeMember(memberId: string) {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const res = await fetch(`/api/platform/members/${memberId}`, {
        method: "DELETE",
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "remove member failed");
      setMembers((current) => current.filter((item) => item.id !== memberId));
      setMessage("成员已移除。");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="gap-4 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <UsersRound className="size-4 text-gray-500" />
          <div>
            <h2 className="font-semibold">团队成员</h2>
            <p className="text-sm text-gray-500">
              {members.length} members · {canManageMembers ? "可管理" : "只读"}
            </p>
          </div>
        </div>
        <Badge variant="outline">
          <ShieldCheck className="size-3" />
          owner/admin
        </Badge>
      </div>

      {canManageMembers && (
        <form
          onSubmit={addMember}
          className="grid gap-3 md:grid-cols-[minmax(0,1fr)_160px_auto]"
        >
          <div>
            <Label htmlFor="member-email">邮箱</Label>
            <Input
              id="member-email"
              name="email"
              type="email"
              placeholder="teammate@example.com"
              disabled={busy}
              required
            />
          </div>
          <div>
            <Label htmlFor="member-role">角色</Label>
            <select
              id="member-role"
              name="role"
              defaultValue="member"
              disabled={busy}
              className="h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              {roles.map((role) => (
                <option key={role} value={role}>
                  {roleLabels[role]}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <Button type="submit" className="w-full" disabled={busy}>
              <UserPlus className="size-4" />
              添加
            </Button>
          </div>
        </form>
      )}

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

      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="text-xs text-gray-500">
            <tr className="border-b">
              <th className="py-2 font-medium">邮箱</th>
              <th className="py-2 font-medium">名称</th>
              <th className="py-2 font-medium">角色</th>
              <th className="py-2 font-medium">加入时间</th>
              <th className="py-2 text-right font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            {members.map((member) => (
              <tr key={member.id} className="border-b last:border-0">
                <td className="py-2">
                  <div className="flex items-center gap-2">
                    <span>{member.email}</span>
                    {member.isCurrentUser && <Badge variant="outline">you</Badge>}
                  </div>
                </td>
                <td className="py-2 text-gray-600">{member.name ?? "-"}</td>
                <td className="py-2">
                  {canManageMembers ? (
                    <select
                      value={member.role}
                      disabled={busy}
                      onChange={(event) =>
                        updateRole(
                          member.id,
                          event.target.value as TenantMemberRole
                        )
                      }
                      className="h-8 rounded-md border border-input bg-transparent px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
                    >
                      {roles.map((role) => (
                        <option key={role} value={role}>
                          {roleLabels[role]}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <Badge variant="outline">{roleLabels[member.role]}</Badge>
                  )}
                </td>
                <td className="py-2 text-gray-600">
                  {new Date(member.createdAt).toLocaleString()}
                </td>
                <td className="py-2 text-right">
                  <Button
                    type="button"
                    variant="outline"
                    size="icon-sm"
                    disabled={busy || !canManageMembers || member.isCurrentUser}
                    onClick={() => removeMember(member.id)}
                    aria-label={`移除 ${member.email}`}
                    title={`移除 ${member.email}`}
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
