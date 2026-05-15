"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

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
      router.push(`/projects/${data.id}/bible`);
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
            defaultValue={10}
            min={5}
            max={100}
          />
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
          {submitting ? "生成 Bible 中... (2-3 分钟)" : "上传并生成 Bible"}
        </Button>
      </form>
    </main>
  );
}
