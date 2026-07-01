"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

type Project = { id: string; name: string; targetEpisodeCount: number };
type Round = { id: string; roundNum: number; epRange: string; status: string };
type Episode = {
  id: string;
  roundId: string;
  epNum: number;
  status: string;
  score: number | null;
  scriptTxt: string | null;
  retryCount: number;
};

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
    rounds: Round[];
    episodes: Episode[];
  } | null>(null);

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
  const eps = data.episodes
    .filter((e) => e.roundId === round?.id)
    .sort((a, b) => a.epNum - b.epNum);

  const totalRounds = Math.ceil(project.targetEpisodeCount / 5);
  const allDone =
    data.rounds.length >= totalRounds &&
    data.rounds.every((r) => r.status === "done");

  async function retry(epId: string) {
    await fetch(`/api/episodes/${epId}/retry`, { method: "POST" });
  }

  async function nextRound() {
    await fetch(`/api/projects/${projectId}/rounds/start`, { method: "POST" });
    window.location.href = `/projects/${projectId}/rounds/${roundNum + 1}`;
  }

  return (
    <main className="max-w-4xl mx-auto p-8 space-y-6">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">
            {project.name} · 第 {roundNum} 轮
          </h1>
          <p className="text-sm text-gray-500">{round?.epRange}</p>
        </div>
        <Badge>{round?.status ?? "pending"}</Badge>
      </header>

      <div className="space-y-3">
        {eps.map((ep) => (
          <Card key={ep.id} className="p-4">
            <div className="flex justify-between items-start">
              <div className="flex-1">
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
                  <pre className="mt-2 text-xs bg-gray-50 p-2 rounded max-h-40 overflow-auto whitespace-pre-wrap">
                    {ep.scriptTxt.slice(0, 600)}
                    {ep.scriptTxt.length > 600 && "..."}
                  </pre>
                )}
              </div>
              {ep.status === "red" && ep.retryCount < 2 && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => retry(ep.id)}
                >
                  重跑 ({2 - ep.retryCount} 次剩)
                </Button>
              )}
            </div>
          </Card>
        ))}
      </div>

      {round?.status === "done" && (
        <div className="flex gap-2 pt-4">
          {!allDone && roundNum * 5 < project.targetEpisodeCount && (
            <Button onClick={nextRound}>开始第 {roundNum + 1} 轮</Button>
          )}
          {allDone && (
            <Link href={`/projects/${projectId}/complete`}>
              <Button>项目完成 · 查看导出</Button>
            </Link>
          )}
          <Link href={`/projects/${projectId}/bible`}>
            <Button variant="outline">回到 Bible</Button>
          </Link>
        </div>
      )}
    </main>
  );
}
