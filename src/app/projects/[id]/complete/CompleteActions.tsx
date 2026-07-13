"use client";

import { useState } from "react";
import Link from "next/link";
import { Download, ScrollText } from "lucide-react";
import { Button } from "@/components/ui/button";

type CompleteActionsProps = {
  projectId: string;
  projectName: string;
  deliveryExportHref: string;
};

function filenameFromDisposition(
  disposition: string | null,
  fallback: string
): string {
  if (!disposition) return fallback;
  const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
  if (encoded) {
    try {
      return decodeURIComponent(encoded.replace(/^"|"$/g, ""));
    } catch {
      return fallback;
    }
  }
  return disposition.match(/filename="([^"]+)"/i)?.[1] ?? fallback;
}

async function readResponseError(res: Response, fallback: string): Promise<string> {
  const text = await res.text().catch(() => "");
  if (!text) return `${fallback} (${res.status})`;
  try {
    const payload = JSON.parse(text) as { error?: string };
    return payload.error ?? text;
  } catch {
    return text;
  }
}

async function downloadBlob(href: string, fallbackName: string): Promise<void> {
  const res = await fetch(href);
  if (!res.ok) throw new Error(await readResponseError(res, "下载失败"));
  const blob = await res.blob();
  const filename = filenameFromDisposition(
    res.headers.get("content-disposition"),
    fallbackName
  );
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function CompleteActions({
  projectId,
  projectName,
  deliveryExportHref,
}: CompleteActionsProps) {
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function runDownload(action: string, href: string, fallbackName: string) {
    setBusyAction(action);
    setMessage(null);
    try {
      await downloadBlob(href, fallbackName);
      setMessage("下载已开始");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button
        disabled={busyAction !== null}
        onClick={() =>
          runDownload("delivery", deliveryExportHref, `${projectName}-delivery.zip`)
        }
      >
        <Download className="size-4" />
        {busyAction === "delivery" ? "下载中" : "下载交付包"}
      </Button>
      <Button
        variant="outline"
        disabled={busyAction !== null}
        onClick={() =>
          runDownload(
            "txt",
            `/api/projects/${projectId}/novel-export?format=txt`,
            `${projectName}.txt`
          )
        }
      >
        <Download className="size-4" />
        {busyAction === "txt" ? "导出中" : "导出TXT"}
      </Button>
      <Button
        variant="outline"
        disabled={busyAction !== null}
        onClick={() =>
          runDownload(
            "word",
            `/api/projects/${projectId}/novel-export?format=word`,
            `${projectName}.docx`
          )
        }
      >
        <Download className="size-4" />
        {busyAction === "word" ? "导出中" : "导出Word"}
      </Button>
      <Button asChild variant="outline">
        <Link href={`/projects/${projectId}/bible`}>
          <ScrollText className="size-4" />
          系统 Bible
        </Link>
      </Button>
      {message && <span className="round-muted">{message}</span>}
    </div>
  );
}
