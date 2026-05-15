"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

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
  const router = useRouter();
  const [chars, setChars] = useState(bible.charactersMd ?? "");
  const [plan, setPlan] = useState(bible.episodePlanMd ?? "");
  const [assets, setAssets] = useState(bible.sixAssetsJson ?? "{}");
  const [saving, setSaving] = useState(false);
  const [starting, setStarting] = useState(false);

  async function save() {
    setSaving(true);
    await fetch(`/api/projects/${project.id}/bible`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        charactersMd: chars,
        episodePlanMd: plan,
        sixAssetsJson: assets,
      }),
    });
    setSaving(false);
  }

  async function startRound() {
    setStarting(true);
    await save();
    const res = await fetch(`/api/projects/${project.id}/rounds/start`, {
      method: "POST",
    });
    const data = await res.json();
    router.push(`/projects/${project.id}/rounds/${data.roundNum}`);
  }

  return (
    <main className="max-w-4xl mx-auto p-8 space-y-6">
      <header>
        <h1 className="text-2xl font-bold">{project.name} · Bible</h1>
        <p className="text-sm text-gray-500">
          频道：{bible.channel} · 目标 {project.targetEpisodeCount} 集
        </p>
      </header>

      <section>
        <Label>六大资产（JSON）</Label>
        <Textarea
          value={assets}
          onChange={(e) => setAssets(e.target.value)}
          rows={10}
          className="font-mono text-xs"
        />
      </section>

      <section>
        <Label>人物小传</Label>
        <Textarea
          value={chars}
          onChange={(e) => setChars(e.target.value)}
          rows={18}
        />
      </section>

      <section>
        <Label>集数规划</Label>
        <Textarea
          value={plan}
          onChange={(e) => setPlan(e.target.value)}
          rows={22}
        />
      </section>

      <div className="flex gap-2">
        <Button variant="outline" onClick={save} disabled={saving}>
          {saving ? "保存中" : "保存"}
        </Button>
        <Button onClick={startRound} disabled={starting}>
          {starting ? "启动中" : "开始第 1 轮"}
        </Button>
      </div>
    </main>
  );
}
