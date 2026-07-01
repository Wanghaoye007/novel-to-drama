"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const generationVariantOptions = [
  { value: "sop_full_stack", label: "SOP 全链路" },
  { value: "drama_engine_first", label: "强剧情优先" },
  { value: "current_density", label: "当前密度" },
];

const repairBudgetOptions = [
  { value: "episode", label: "逐集修复" },
  { value: "rewrite", label: "改写一次" },
  { value: "none", label: "不自动修复" },
];

export default function NewProjectPage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    const form = new FormData(e.currentTarget);
    try {
      const res = await fetch("/api/projects", { method: "POST", body: form });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      router.push(`/projects/${data.id}/rounds/${data.roundNum}`);
    } catch (err) {
      setError(String(err));
      setSubmitting(false);
    }
  }

  return (
    <main className="max-w-2xl mx-auto p-8">
      <h1 className="text-2xl font-bold mb-6">新建项目</h1>
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <Label htmlFor="name">项目名</Label>
          <Input id="name" name="name" required />
        </div>
        <div>
          <Label htmlFor="targetEpisodeCount">目标集数</Label>
          <Input
            id="targetEpisodeCount"
            name="targetEpisodeCount"
            type="number"
            defaultValue={30}
            min={1}
            max={100}
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="generationVariant">改编策略</Label>
            <select
              id="generationVariant"
              name="generationVariant"
              defaultValue="sop_full_stack"
              className="h-10 w-full rounded-md border bg-white px-3 text-sm"
            >
              {generationVariantOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="repairBudget">修复预算</Label>
            <select
              id="repairBudget"
              name="repairBudget"
              defaultValue="episode"
              className="h-10 w-full rounded-md border bg-white px-3 text-sm"
            >
              {repairBudgetOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div>
          <Label htmlFor="file">上传小说（txt 或 docx）</Label>
          <Input
            id="file"
            name="file"
            type="file"
            accept=".txt,.docx"
            required
          />
        </div>
        {error && <p className="text-red-500 text-sm">{error}</p>}
        <Button type="submit" disabled={submitting}>
          {submitting ? "启动自动改编中..." : "上传并开始第 1 轮"}
        </Button>
      </form>
    </main>
  );
}
