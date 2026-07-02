"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  CreditCard,
  FlaskConical,
  FolderKanban,
  KeyRound,
  Plus,
  Sparkles,
} from "lucide-react";

const navItems = [
  { href: "/", label: "项目工作台", icon: FolderKanban },
  { href: "/projects/new", label: "新建改编", icon: Plus },
  { href: "/platform", label: "平台与点数", icon: CreditCard },
  { href: "/quality", label: "内部回归", icon: FlaskConical },
];

function pageLabel(pathname: string): string {
  if (pathname === "/") return "项目工作台";
  if (pathname.startsWith("/projects/new")) return "新建改编";
  if (pathname.startsWith("/platform")) return "平台与点数";
  if (pathname.startsWith("/quality")) return "内部回归";
  if (pathname.includes("/bible")) return "系统 Story Bible";
  if (pathname.includes("/complete")) return "交付完成";
  if (pathname.includes("/rounds/")) return "轮次生成";
  return "短剧改编工作台";
}

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isRoundWorkspace = pathname.includes("/rounds/");

  return (
    <div className="studio-shell">
      <aside className="studio-rail" aria-label="主导航">
        <Link href="/" className="studio-brand" aria-label="Novel-to-Drama">
          <span className="studio-brand-mark">剧</span>
          <span>
            <span className="studio-brand-title block">Novel-to-Drama</span>
            <span className="studio-brand-subtitle block">
              爆款短剧自动改编
            </span>
          </span>
        </Link>

        <nav className="studio-nav">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className="studio-nav-link"
                data-active={isActive(pathname, item.href)}
              >
                <Icon aria-hidden="true" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="studio-rail-foot">
          <div className="mb-2 flex items-center gap-2 font-semibold text-[color:var(--foreground)]">
            <KeyRound className="size-3.5" />
            运营体验模式
          </div>
          <p>上传小说后系统自动拆解 Bible、轮次上下文、脚本和交付包。</p>
        </div>
      </aside>

      <div
        className="studio-main"
        data-mode={isRoundWorkspace ? "round-workspace" : undefined}
      >
        <header className="studio-topbar">
          <div className="studio-topbar-inner">
            <div className="flex min-w-0 items-center gap-3">
              <Sparkles className="size-4 shrink-0 text-[color:var(--reela-pink)]" />
              <span className="studio-topbar-title truncate">
                {pageLabel(pathname)}
              </span>
            </div>
            <div className="studio-topbar-meta">
              <span>Stable Ops URL</span>
              <span aria-hidden="true">·</span>
              <span>Gemini 3.5 Flash</span>
            </div>
          </div>
        </header>
        <nav className="studio-mobile-nav" aria-label="移动主导航">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className="studio-mobile-nav-link"
                data-active={isActive(pathname, item.href)}
              >
                <Icon aria-hidden="true" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="studio-view">{children}</div>
      </div>
    </div>
  );
}
