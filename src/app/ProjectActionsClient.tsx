"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Copy, Settings2, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type ProjectSummary = {
  id: string;
  name: string;
  targetEpisodeCount: number;
  status: string;
};

async function readError(res: Response, fallback: string): Promise<string> {
  const payload = (await res.json().catch(() => null)) as { error?: string } | null;
  return payload?.error ?? `${fallback}（HTTP ${res.status}）`;
}

export function ProjectCloneButton({ projectId }: { projectId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function cloneProject() {
    setBusy(true);
    try {
      const res = await fetch(`/api/projects/${projectId}/clone`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const payload = (await res.json()) as {
        id?: string;
        roundNum?: number;
        error?: string;
      };
      if (!res.ok || !payload.id) {
        throw new Error(payload.error ?? "复制项目失败");
      }
      router.push(`/projects/${payload.id}/rounds/${payload.roundNum ?? 1}`);
    } catch (error) {
      window.alert(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      disabled={busy}
      onClick={cloneProject}
    >
      <Copy className="size-4" />
      {busy ? "复制中" : "复制"}
    </Button>
  );
}

export function ProjectManageButton({
  projectId,
  projectName,
  targetEpisodeCount,
  status,
  size = "sm",
  deleteRedirectHref,
  onUpdated,
  onDeleted,
}: {
  projectId: string;
  projectName: string;
  targetEpisodeCount: number;
  status: string;
  size?: "xs" | "sm" | "default";
  deleteRedirectHref?: string;
  onUpdated?: (project: ProjectSummary) => void;
  onDeleted?: () => void;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(projectName);
  const [targetCount, setTargetCount] = useState(String(targetEpisodeCount));
  const [busy, setBusy] = useState<"save" | "delete" | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  function resetDraft(nextOpen: boolean) {
    setOpen(nextOpen);
    if (nextOpen) {
      setName(projectName);
      setTargetCount(String(targetEpisodeCount));
      setMessage(null);
    }
  }

  async function saveProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedName = name.trim();
    const parsedCount = Number(targetCount);
    if (!trimmedName) {
      setMessage("项目名不能为空");
      return;
    }
    if (!Number.isInteger(parsedCount) || parsedCount < 1 || parsedCount > 100) {
      setMessage("目标集数必须是 1-100 的整数");
      return;
    }

    setBusy("save");
    setMessage(null);
    try {
      const res = await fetch(`/api/projects/${projectId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: trimmedName,
          targetEpisodeCount: parsedCount,
        }),
      });
      if (!res.ok) throw new Error(await readError(res, "保存项目失败"));
      const payload = (await res.json()) as { project?: ProjectSummary };
      if (payload.project) onUpdated?.(payload.project);
      router.refresh();
      setMessage("已保存");
      setOpen(false);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  }

  async function deleteProject() {
    const confirmed = window.confirm(
      `确定删除「${projectName}」？项目、剧集、任务记录和导出文件都会被删除。`
    );
    if (!confirmed) return;

    setBusy("delete");
    setMessage(null);
    try {
      const res = await fetch(`/api/projects/${projectId}`, { method: "DELETE" });
      if (!res.ok) throw new Error(await readError(res, "删除项目失败"));
      onDeleted?.();
      setOpen(false);
      if (deleteRedirectHref) {
        router.push(deleteRedirectHref);
      } else {
        router.refresh();
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  }

  return (
    <Dialog open={open} onOpenChange={resetDraft}>
      <DialogTrigger asChild>
        <Button type="button" variant="outline" size={size}>
          <Settings2 className="size-4" />
          管理
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>项目管理</DialogTitle>
          <DialogDescription>
            修改项目基础信息，或删除不再需要的改编项目。
          </DialogDescription>
        </DialogHeader>

        <form id="project-manage-form" className="grid gap-4" onSubmit={saveProject}>
          <div>
            <Label htmlFor={`project-name-${projectId}`}>项目名</Label>
            <Input
              id={`project-name-${projectId}`}
              value={name}
              disabled={busy !== null}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor={`project-target-${projectId}`}>目标集数</Label>
            <Input
              id={`project-target-${projectId}`}
              type="number"
              min={1}
              max={100}
              value={targetCount}
              disabled={busy !== null}
              onChange={(event) => setTargetCount(event.target.value)}
            />
          </div>
          <p className="text-xs text-muted-foreground">
            当前状态：{status}。目标集数不能低于已生成集数。
          </p>
        </form>

        <div className="rounded-[var(--radius-sm)] border border-destructive/20 bg-destructive/5 p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="text-sm font-semibold text-destructive">删除项目</div>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                正在执行中的项目会被拦截，避免删除后 worker 继续写入。
              </p>
            </div>
            <Button
              type="button"
              variant="destructive"
              size="sm"
              disabled={busy !== null}
              onClick={deleteProject}
            >
              <Trash2 className="size-4" />
              {busy === "delete" ? "删除中" : "删除"}
            </Button>
          </div>
        </div>

        {message && (
          <div className="rounded-[var(--radius-sm)] bg-secondary px-3 py-2 text-sm text-muted-foreground">
            {message}
          </div>
        )}

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            disabled={busy !== null}
            onClick={() => setOpen(false)}
          >
            取消
          </Button>
          <Button form="project-manage-form" type="submit" disabled={busy !== null}>
            {busy === "save" ? "保存中" : "保存修改"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
