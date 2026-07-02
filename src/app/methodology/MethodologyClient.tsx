"use client";

import { FormEvent, useMemo, useState } from "react";
import {
  BookOpen,
  CheckCircle2,
  Database,
  FileText,
  Layers3,
  Plus,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type {
  MethodologyCardView,
  MethodologyData,
  MethodologyStatus,
} from "@/lib/methodology";

const statusOptions: MethodologyStatus[] = [
  "draft",
  "active",
  "archived",
  "rejected",
];

const statusLabels: Record<MethodologyStatus, string> = {
  draft: "草稿",
  active: "启用",
  archived: "归档",
  rejected: "拒绝",
};

function statusVariant(
  status: MethodologyStatus
): "default" | "destructive" | "outline" | "secondary" {
  if (status === "active") return "default";
  if (status === "rejected") return "destructive";
  if (status === "archived") return "secondary";
  return "outline";
}

function formatDate(value: number): string {
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

function summarizeJson(raw: string | null): string {
  if (!raw) return "未记录";
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const level = parsed.overall_level ?? parsed.overallLevel;
    const intensity = parsed.recommended_intensity ?? parsed.recommendedIntensity;
    if (level && intensity) return `${String(level)} / ${String(intensity)}`;
    const cards = Array.isArray(parsed.cards) ? parsed.cards.length : null;
    if (cards != null) return `${cards} 张方法卡`;
    return "已记录";
  } catch {
    return "已记录";
  }
}

function cardStageLabel(card: MethodologyCardView): string {
  if (!card.appliesToStage.length) return "未设定阶段";
  return card.appliesToStage.join(" · ");
}

export function MethodologyClient({
  initialData,
  workspaceName,
  sessionSource,
}: {
  initialData: MethodologyData;
  workspaceName: string;
  sessionSource: "browser" | "api_key" | "default";
}) {
  const [data, setData] = useState(initialData);
  const [title, setTitle] = useState("");
  const [sourceType, setSourceType] = useState("sop");
  const [originPath, setOriginPath] = useState("");
  const [rawText, setRawText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const stats = useMemo(() => {
    const activeCards = data.cards.filter((card) => card.status === "active").length;
    const draftCards = data.cards.filter((card) => card.status === "draft").length;
    return {
      sources: data.sources.length,
      cards: data.cards.length,
      activeCards,
      draftCards,
      runs: data.runs.length,
    };
  }, [data]);

  async function refresh() {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/methodology");
      const nextData = await res.json();
      if (!res.ok) throw new Error(nextData.error ?? "methodology load failed");
      setData(nextData as MethodologyData);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function createSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/methodology", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          sourceType,
          originPath,
          rawText,
        }),
      });
      const result = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(result.error ?? "methodology create failed");
      setTitle("");
      setOriginPath("");
      setRawText("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function setCardStatus(id: string, status: MethodologyStatus) {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`/api/methodology/cards/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      const result = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(result.error ?? "card status update failed");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-shell">
      <header className="page-header">
        <div>
          <div className="page-kicker">
            Internal Knowledge · {workspaceName} · {sessionSource}
          </div>
          <h1 className="page-title">内部方法论</h1>
          <p className="page-description">
            沉淀短剧改编 SOP、爆款规则和强原文轻改策略，进入生成链路前先以草稿卡审核。
          </p>
        </div>
        <Button variant="outline" onClick={refresh} disabled={busy}>
          <RefreshCw className="size-4" />
          刷新
        </Button>
      </header>

      {error && (
        <div className="rounded-[var(--radius-md)] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-200">
          {error}
        </div>
      )}

      <section className="grid gap-3 md:grid-cols-5">
        <Card className="gap-2 p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <FileText className="size-4" />
            来源
          </div>
          <div className="text-2xl font-semibold">{stats.sources}</div>
        </Card>
        <Card className="gap-2 p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Layers3 className="size-4" />
            方法卡
          </div>
          <div className="text-2xl font-semibold">{stats.cards}</div>
        </Card>
        <Card className="gap-2 p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <CheckCircle2 className="size-4" />
            已启用
          </div>
          <div className="text-2xl font-semibold">{stats.activeCards}</div>
        </Card>
        <Card className="gap-2 p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <BookOpen className="size-4" />
            待审
          </div>
          <div className="text-2xl font-semibold">{stats.draftCards}</div>
        </Card>
        <Card className="gap-2 p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Database className="size-4" />
            运行
          </div>
          <div className="text-2xl font-semibold">{stats.runs}</div>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-[390px_1fr]">
        <div className="space-y-4">
          <Card className="gap-4 p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold">导入来源</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  新来源默认生成草稿卡
                </p>
              </div>
              <Plus className="size-4 text-[color:var(--reela-pink)]" />
            </div>

            <form className="grid gap-3" onSubmit={createSource}>
              <Input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="标题"
              />
              <div className="grid gap-3 sm:grid-cols-[120px_1fr] xl:grid-cols-1">
                <Input
                  value={sourceType}
                  onChange={(event) => setSourceType(event.target.value)}
                  placeholder="类型"
                />
                <Input
                  value={originPath}
                  onChange={(event) => setOriginPath(event.target.value)}
                  placeholder="来源路径"
                />
              </div>
              <Textarea
                value={rawText}
                onChange={(event) => setRawText(event.target.value)}
                placeholder="粘贴 SOP、拆剧笔记或规则片段"
                className="min-h-56"
              />
              <Button
                type="submit"
                disabled={busy || !title.trim() || !rawText.trim()}
              >
                <BookOpen className="size-4" />
                生成草稿卡
              </Button>
            </form>
          </Card>

          <Card className="gap-3 p-5">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-base font-semibold">来源库</h2>
              <Badge variant="outline">{data.sources.length}</Badge>
            </div>
            <div className="space-y-2">
              {data.sources.length === 0 ? (
                <div className="rounded-[var(--radius-md)] border border-dashed border-border p-4 text-sm text-muted-foreground">
                  暂无来源
                </div>
              ) : (
                data.sources.map((source) => (
                  <div
                    key={source.id}
                    className="rounded-[var(--radius-md)] border border-[color:var(--hairline-soft)] bg-[color:var(--surface-muted)] p-3"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="truncate font-semibold">{source.title}</div>
                        <div className="mt-1 text-xs text-muted-foreground">
                          {source.sourceType} · {source.cardCount} 张卡 ·{" "}
                          {formatDate(source.updatedAt)}
                        </div>
                      </div>
                      <Badge variant={statusVariant(source.status)}>
                        {statusLabels[source.status]}
                      </Badge>
                    </div>
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>

        <div className="space-y-4">
          <Card className="gap-4 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold">方法卡</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  只有启用状态会进入后续方法论上下文
                </p>
              </div>
              <Badge variant="outline">{data.cards.length}</Badge>
            </div>

            <div className="space-y-3">
              {data.cards.length === 0 ? (
                <div className="rounded-[var(--radius-md)] border border-dashed border-border p-6 text-sm text-muted-foreground">
                  暂无方法卡
                </div>
              ) : (
                data.cards.map((card) => (
                  <article
                    key={card.id}
                    className="rounded-[var(--radius-lg)] border border-[color:var(--hairline-soft)] bg-[color:var(--surface-muted)] p-4"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="font-semibold">{card.name}</h3>
                          <Badge variant={statusVariant(card.status)}>
                            {statusLabels[card.status]}
                          </Badge>
                        </div>
                        <div className="mt-1 text-xs text-muted-foreground">
                          {card.category} · v{card.version} ·{" "}
                          {formatDate(card.updatedAt)}
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {statusOptions.map((status) => (
                          <Button
                            key={status}
                            type="button"
                            size="xs"
                            variant={card.status === status ? "default" : "outline"}
                            disabled={busy || card.status === status}
                            onClick={() => setCardStatus(card.id, status)}
                          >
                            {statusLabels[status]}
                          </Button>
                        ))}
                      </div>
                    </div>

                    <div className="mt-3 grid gap-3 lg:grid-cols-[0.92fr_1.08fr]">
                      <div className="rounded-[var(--radius-md)] bg-card p-3">
                        <div className="text-xs font-semibold text-muted-foreground">
                          触发条件
                        </div>
                        <p className="mt-1 text-sm leading-6">{card.trigger}</p>
                      </div>
                      <div className="rounded-[var(--radius-md)] bg-card p-3">
                        <div className="text-xs font-semibold text-muted-foreground">
                          适用阶段
                        </div>
                        <p className="mt-1 text-sm leading-6">
                          {cardStageLabel(card)}
                        </p>
                      </div>
                    </div>

                    <div className="mt-3 grid gap-3 lg:grid-cols-2">
                      <div>
                        <div className="text-xs font-semibold text-muted-foreground">
                          生成规则
                        </div>
                        <p className="mt-1 text-sm leading-6">{card.generationRule}</p>
                      </div>
                      <div>
                        <div className="text-xs font-semibold text-muted-foreground">
                          质检规则
                        </div>
                        <p className="mt-1 text-sm leading-6 text-muted-foreground">
                          {card.qualityRule}
                        </p>
                      </div>
                    </div>
                  </article>
                ))
              )}
            </div>
          </Card>

          <Card className="gap-3 p-5">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="size-4 text-[color:var(--reela-pink)]" />
                <h2 className="text-base font-semibold">最近方法论运行</h2>
              </div>
              <Badge variant="outline">{data.runs.length}</Badge>
            </div>
            <div className="space-y-2">
              {data.runs.length === 0 ? (
                <div className="rounded-[var(--radius-md)] border border-dashed border-border p-4 text-sm text-muted-foreground">
                  暂无运行记录
                </div>
              ) : (
                data.runs.map((run) => (
                  <div
                    key={run.id}
                    className="grid gap-2 rounded-[var(--radius-md)] border border-[color:var(--hairline-soft)] bg-[color:var(--surface-muted)] p-3 md:grid-cols-[1fr_1fr_auto]"
                  >
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold">
                        {run.projectId ?? "未关联项目"}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {run.roundId ?? "未关联轮次"}
                      </div>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {summarizeJson(run.sourceStrengthJson)} ·{" "}
                      {summarizeJson(run.methodologyContextJson)}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {formatDate(run.createdAt)}
                    </div>
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>
      </section>
    </section>
  );
}
