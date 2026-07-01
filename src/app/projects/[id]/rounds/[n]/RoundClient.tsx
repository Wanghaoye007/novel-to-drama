"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Download, Languages, PackageCheck, Play, Video } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

type Project = {
  id: string;
  name: string;
  targetEpisodeCount: number;
  status: string;
};
type Round = {
  id: string;
  roundNum: number;
  epRange: string;
  status: string;
  summaryJson: string | null;
};
type Episode = {
  id: string;
  roundId: string;
  epNum: number;
  status: string;
  score: number | null;
  scriptTxt: string | null;
  retryCount: number;
};
type EngineRoundSummary = {
  quality_report?: {
    status: string;
    scores: Record<string, number>;
    blocking_issues: string[];
  };
  next_round_context?: {
    current_episode: number;
    summary: string;
    open_hooks: string[];
    forbidden_reveals: string[];
  };
};
type DeliveryPreflight = {
  ready: boolean;
  warnings: string[];
  files: Array<{ path: string; bytes: number }>;
};

function parseSummary(round?: Round): EngineRoundSummary | null {
  if (!round?.summaryJson) return null;
  try {
    return JSON.parse(round.summaryJson) as EngineRoundSummary;
  } catch {
    return null;
  }
}

export function RoundClient({
  projectId,
  roundNum,
  project,
}: {
  projectId: string;
  roundNum: number;
  project: Project;
}) {
  const [data, setData] = useState<{
    project: Project;
    rounds: Round[];
    episodes: Episode[];
  } | null>(null);
  const [delivery, setDelivery] = useState<DeliveryPreflight | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);

  useEffect(() => {
    let stopped = false;
    async function poll() {
      while (!stopped) {
        const res = await fetch(`/api/projects/${projectId}`);
        const d = await res.json();
        setData(d);
        const round = d.rounds.find((r: Round) => r.roundNum === roundNum);
        if (round?.status === "done" || round?.status === "failed") break;
        await new Promise((r) => setTimeout(r, 3000));
      }
    }
    poll();
    return () => {
      stopped = true;
    };
  }, [projectId, roundNum]);

  if (!data) return <main className="p-8">加载中...</main>;

  const round = data.rounds.find((r) => r.roundNum === roundNum);
  const summary = parseSummary(round);
  const quality = summary?.quality_report;
  const context = summary?.next_round_context;
  const eps = data.episodes
    .filter((e) => e.roundId === round?.id)
    .sort((a, b) => a.epNum - b.epNum);

  const projectDone = data.project.status === "done";

  async function nextRound() {
    await fetch(`/api/projects/${projectId}/rounds/start`, { method: "POST" });
    window.location.href = `/projects/${projectId}/rounds/${roundNum + 1}`;
  }

  async function runAction(name: string, action: () => Promise<string>) {
    setBusyAction(name);
    setActionMessage(null);
    try {
      setActionMessage(await action());
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function checkDelivery() {
    const res = await fetch(`/api/projects/${projectId}/delivery?round=${roundNum}`);
    if (!res.ok) throw new Error(await res.text());
    const report = (await res.json()) as DeliveryPreflight;
    setDelivery(report);
    return report.ready ? "交付预检通过" : "交付预检有 warning";
  }

  async function exportVideoBrief() {
    const res = await fetch(`/api/projects/${projectId}/video-brief?round=${roundNum}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error(await res.text());
    return "视频 brief 已生成";
  }

  async function exportLocalization() {
    const res = await fetch(`/api/projects/${projectId}/localization?round=${roundNum}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error(await res.text());
    return "本地化包已生成";
  }

  return (
    <main className="max-w-4xl mx-auto p-8 space-y-6">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">
            {project.name} · 第 {roundNum} 轮
          </h1>
          <p className="text-sm text-gray-500">
            {round?.epRange} · 目标 {project.targetEpisodeCount} 集
          </p>
        </div>
        <Badge>{round?.status ?? "pending"}</Badge>
      </header>

      {quality && (
        <Card className="p-4 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={quality.status === "usable" ? "default" : "destructive"}>
              {quality.status}
            </Badge>
            {Object.entries(quality.scores).map(([name, value]) => (
              <span key={name} className="text-sm text-gray-600">
                {name}: {value}
              </span>
            ))}
          </div>
          {quality.blocking_issues.length > 0 && (
            <ul className="list-disc pl-5 text-sm text-red-600">
              {quality.blocking_issues.map((issue) => (
                <li key={issue}>{issue}</li>
              ))}
            </ul>
          )}
        </Card>
      )}

      {context && (
        <Card className="p-4 space-y-2">
          <div className="text-sm text-gray-600">
            当前集数：{context.current_episode}
          </div>
          <p className="text-sm whitespace-pre-wrap">{context.summary}</p>
          {context.open_hooks.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {context.open_hooks.map((hook) => (
                <Badge key={hook} variant="outline">
                  {hook}
                </Badge>
              ))}
            </div>
          )}
        </Card>
      )}

      <div className="space-y-3">
        {eps.map((ep) => (
          <Card key={ep.id} className="p-4">
            <div className="flex justify-between items-start gap-4">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium">
                    E{String(ep.epNum).padStart(2, "0")}
                  </h3>
                  <Badge
                    variant={ep.status === "green" ? "default" : "destructive"}
                  >
                    {ep.status}
                  </Badge>
                  {ep.score != null && (
                    <span className="text-sm text-gray-500">
                      score: {ep.score}
                    </span>
                  )}
                </div>
                {ep.scriptTxt && (
                  <pre className="mt-2 text-xs bg-gray-50 p-3 rounded max-h-72 overflow-auto whitespace-pre-wrap">
                    {ep.scriptTxt.slice(0, 600)}
                    {ep.scriptTxt.length > 600 && "..."}
                  </pre>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>

      {round?.status === "done" && (
        <div className="space-y-4 pt-4">
          <div className="flex flex-wrap gap-2">
            {!projectDone && (
              <Button onClick={nextRound}>
                <Play className="size-4" />
                开始第 {roundNum + 1} 轮
              </Button>
            )}
            {projectDone && (
              <Link href={`/projects/${projectId}/complete`}>
                <Button>
                  <PackageCheck className="size-4" />
                  项目完成
                </Button>
              </Link>
            )}
            <Button
              variant="outline"
              disabled={busyAction === "video"}
              onClick={() => runAction("video", exportVideoBrief)}
            >
              <Video className="size-4" />
              生成视频 brief
            </Button>
            <Button
              variant="outline"
              disabled={busyAction === "localization"}
              onClick={() => runAction("localization", exportLocalization)}
            >
              <Languages className="size-4" />
              生成本地化包
            </Button>
            <Button
              variant="outline"
              disabled={busyAction === "delivery"}
              onClick={() => runAction("delivery", checkDelivery)}
            >
              <PackageCheck className="size-4" />
              交付预检
            </Button>
            <a href={`/api/projects/${projectId}/export?round=${roundNum}`}>
              <Button variant="outline">
                <Download className="size-4" />
                下载交付包
              </Button>
            </a>
            <Link href={`/projects/${projectId}/bible`}>
              <Button variant="outline">系统 Bible</Button>
            </Link>
          </div>

          {actionMessage && (
            <p className="text-sm text-gray-600">{actionMessage}</p>
          )}

          {delivery && (
            <Card className="p-4 space-y-2">
              <div className="flex items-center gap-2">
                <Badge variant={delivery.ready ? "default" : "destructive"}>
                  {delivery.ready ? "ready" : "warning"}
                </Badge>
                <span className="text-sm text-gray-600">
                  文件 {delivery.files.length}
                </span>
              </div>
              {delivery.warnings.length > 0 && (
                <ul className="list-disc pl-5 text-sm text-red-600">
                  {delivery.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              )}
            </Card>
          )}
        </div>
      )}
    </main>
  );
}
