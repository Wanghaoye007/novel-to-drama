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
    <section className="page-shell">
      <header className="page-header">
        <div>
          <div className="page-kicker">目标 {project.targetEpisodeCount} 集</div>
          <h1 className="page-title">{project.name} · 系统 Bible</h1>
          <p className="page-description">
            这是系统自动生成的全局设定、人物规则和轮次上下文，给后续改编链路使用，不需要运营手动确认。
          </p>
        </div>
        <div>
          <Badge variant="outline">internal</Badge>
        </div>
      </header>

      <section className="space-y-2">
        <Label>Story Bible JSON</Label>
        <Textarea
          value={bible.sixAssetsJson ?? "{}"}
          readOnly
          rows={10}
          className="font-mono text-xs"
        />
      </section>

      <section className="space-y-2">
        <Label>角色与世界规则</Label>
        <Textarea
          value={bible.charactersMd ?? ""}
          readOnly
          rows={18}
        />
      </section>

      <section className="space-y-2">
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
    </section>
  );
}
