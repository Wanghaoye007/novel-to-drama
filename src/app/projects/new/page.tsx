"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, FileUp, SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { DEFAULT_LLM_MODEL, llmModelOptions } from "@/lib/llm-model-options";

const generationVariantOptions = [
  { value: "drama_engine_first", label: "强剧情优先" },
  { value: "sop_full_stack", label: "SOP 全链路（慢速精修）" },
];

const repairBudgetOptions = [
  { value: "episode", label: "逐集修复" },
  { value: "rewrite", label: "改写一次" },
  { value: "none", label: "不自动修复" },
];

const episodeCountOptions = [1, 2, 3, 4, 5];

async function readApiError(res: Response): Promise<string> {
  const text = await res.text();
  try {
    const data = JSON.parse(text) as {
      error?: string;
      quota?: { kind?: string; limit?: number; used?: number };
    };
    if (data.quota?.kind === "projects") {
      return `项目数量已达到当前工作区上限（${data.quota.used}/${data.quota.limit}）。请清理旧项目或提升项目额度后再试。`;
    }
    if (data.quota?.kind === "monthly_jobs") {
      return `本月任务额度已用完（${data.quota.used}/${data.quota.limit}）。请稍后再试或提升任务额度。`;
    }
    if (data.error === "API key required") {
      return "当前环境需要 API Key，请先完成平台授权后再上传。";
    }
    return data.error ?? text;
  } catch {
    return text || `请求失败（HTTP ${res.status}）`;
  }
}

export default function NewProjectPage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState("");

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    const form = new FormData(e.currentTarget);
    try {
      const res = await fetch("/api/projects", { method: "POST", body: form });
      if (!res.ok) throw new Error(await readApiError(res));
      const data = await res.json();
      router.push(`/projects/${data.id}/rounds/${data.roundNum}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  }

  return (
    <section className="page-shell page-shell-narrow">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="page-kicker">自动生成 Story Bible 与第 1 轮脚本</div>
          <h1 className="page-title">新建改编项目</h1>
          <p className="page-description">
            MVP 不要求用户确认 Bible。上传后系统会按目标集数和上下文自动拆轮次，先产出可继续迭代的第 1 轮结果。
          </p>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link href="/projects">
            <ArrowLeft className="size-4" />
            返回项目列表
          </Link>
        </Button>
      </header>

      <Card className="p-6">
        <form onSubmit={onSubmit} className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-[1fr_160px]">
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
          </div>

          <div className="soft-panel">
            <div className="mb-4 flex items-center gap-2 text-sm font-semibold">
              <SlidersHorizontal className="size-4 text-[color:var(--reela-pink)]" />
              生成策略
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <Label htmlFor="generationVariant">改编策略</Label>
                <select
                  id="generationVariant"
                  name="generationVariant"
                  defaultValue="drama_engine_first"
                  className="form-select"
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
                  className="form-select"
                >
                  {repairBudgetOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <Label htmlFor="episodesPerRound">首轮生成集数</Label>
                <select
                  id="episodesPerRound"
                  name="episodesPerRound"
                  defaultValue="5"
                  className="form-select"
                >
                  {episodeCountOptions.map((count) => (
                    <option key={count} value={count}>
                      {count} 集
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <Label htmlFor="llmModel">模型</Label>
                <select
                  id="llmModel"
                  name="llmModel"
                  defaultValue={DEFAULT_LLM_MODEL}
                  className="form-select"
                >
                  {llmModelOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div>
            <Label htmlFor="file">上传小说（txt 或 docx）</Label>
            <input
              id="file"
              name="file"
              type="file"
              accept=".txt,.docx"
              required
              className="sr-only"
              onChange={(event) =>
                setFileName(event.currentTarget.files?.[0]?.name ?? "")
              }
            />
            <label htmlFor="file" className="file-picker">
              <span>
                <FileUp className="size-4" />
                选择文件
              </span>
              <b>{fileName || "尚未选择文件"}</b>
            </label>
          </div>

          {error && (
            <div className="rounded-[var(--radius-md)] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <Button type="submit" size="lg" disabled={submitting}>
            <FileUp className="size-4" />
            {submitting ? "启动自动改编中..." : "上传并开始第 1 轮"}
          </Button>
        </form>
      </Card>
    </section>
  );
}
