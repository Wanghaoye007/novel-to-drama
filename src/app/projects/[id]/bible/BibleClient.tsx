"use client";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

type Project = { id: string; name: string; targetEpisodeCount: number };
type Bible = {
  channel: string | null;
  charactersMd: string | null;
  episodePlanMd: string | null;
  sixAssetsJson: string | null;
};

export function BibleClient({
  project,
  bible,
}: {
  project: Project;
  bible: Bible;
}) {
  return (
    <main className="max-w-4xl mx-auto p-8 space-y-6">
      <header>
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold">{project.name} · 系统 Bible</h1>
          <Badge variant="outline">internal</Badge>
        </div>
        <p className="text-sm text-gray-500">目标 {project.targetEpisodeCount} 集</p>
      </header>

      <section>
        <Label>Story Bible JSON</Label>
        <Textarea
          value={bible.sixAssetsJson ?? "{}"}
          readOnly
          rows={10}
          className="font-mono text-xs"
        />
      </section>

      <section>
        <Label>角色与世界规则</Label>
        <Textarea
          value={bible.charactersMd ?? ""}
          readOnly
          rows={18}
        />
      </section>

      <section>
        <Label>本轮上下文识别</Label>
        <Textarea
          value={bible.episodePlanMd ?? ""}
          readOnly
          rows={22}
        />
      </section>

      <div className="flex gap-2">
        <Link href={`/projects/${project.id}/rounds/1`}>
          <Button variant="outline">返回轮次</Button>
        </Link>
      </div>
    </main>
  );
}
