"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Copy } from "lucide-react";
import { Button } from "@/components/ui/button";

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
