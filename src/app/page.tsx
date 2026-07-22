import Link from "next/link";
import {
  BadgeCheck,
  BookOpen,
  CircleDollarSign,
  Clapperboard,
  FileUp,
  Gauge,
  KeyRound,
  Layers3,
  LineChart,
  Play,
  Rocket,
  ShieldCheck,
  Sparkles,
  Users,
  WandSparkles,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const demoSteps = [
  {
    title: "上传小说原文",
    body: "txt/docx 进入素材池，系统自动识别章节、人物、爽点和可改编密度。",
    icon: FileUp,
  },
  {
    title: "生成 Story Bible",
    body: "角色关系、世界观、矛盾线和当前集基线由系统持有，不靠人工确认推进。",
    icon: BookOpen,
  },
  {
    title: "轮次式分集改编",
    body: "按目标集数自动衔接上下文，持续产出对白剧本、视频 brief 和本地化包。",
    icon: Layers3,
  },
  {
    title: "质量门禁与交付",
    body: "源文证据、戏剧功能、节奏、交付预检同步进入运营看板。",
    icon: BadgeCheck,
  },
];

const showcases = [
  {
    name: "都市逆袭 · 60 集",
    tag: "版权方样片",
    metric: "18 分钟完成首轮",
    summary: "从 42 万字男频小说中抽取主线、反转钩子和 60 集对白脚本。",
  },
  {
    name: "豪门复仇 · 80 集",
    tag: "短剧厂牌",
    metric: "96% 关键情节覆盖",
    summary: "保留当前集旧稿作为修复基线，控制改动范围并输出重拍提示。",
  },
  {
    name: "出海甜宠 · 45 集",
    tag: "本地化团队",
    metric: "3 类交付资产",
    summary: "同步产出中文对白、视频生成 brief、海外本地化 package。",
  },
];

const dashboardSignals = [
  ["任务队列", "12 个轮次运行中", "bg-[#ff2f73]"],
  ["质量门禁", "5 类样本回归", "bg-[#2aa876]"],
  ["点数钱包", "42,800 credits", "bg-[#e6a22f]"],
  ["API 访问", "7 把生产密钥", "bg-[#3b7cf6]"],
];

const partnerTypes = [
  "版权方批量测剧",
  "短剧厂牌提效",
  "MCN 内容孵化",
  "出海本地化交付",
];

export default function Home() {
  return (
    <main className="min-h-screen bg-[#f7f6f2] text-[#17171b]">
      <section className="relative overflow-hidden border-b border-black/10 bg-[#f7f6f2]">
        <div className="absolute inset-x-0 top-0 h-2 bg-[linear-gradient(90deg,#ff2f73,#2aa876,#3b7cf6,#e6a22f)]" />
        <nav className="mx-auto flex w-full max-w-7xl items-center justify-between gap-5 px-5 py-5 md:px-8">
          <Link href="/" className="flex items-center gap-3" aria-label="Novel-to-Drama">
            <span className="grid size-10 place-items-center rounded-lg bg-[#17171b] text-sm font-black text-white shadow-[0_12px_30px_rgba(23,23,27,0.18)]">
              剧
            </span>
            <span>
              <span className="block text-sm font-black uppercase">Novel-to-Drama</span>
              <span className="block text-xs font-semibold text-[#68686f]">
                小说转短剧生产平台
              </span>
            </span>
          </Link>
          <div className="hidden items-center gap-6 text-sm font-semibold text-[#55555c] md:flex">
            <Link href="/projects">项目工作台</Link>
            <a href="#demo">产品演示</a>
            <a href="#showcase">作品展示</a>
            <a href="#ops">运营看板</a>
            <a href="#partners">招商合作</a>
          </div>
          <Button asChild size="sm">
            <Link href="/projects/new">
              <WandSparkles className="size-4" />
              开始改编
            </Link>
          </Button>
        </nav>

        <div className="mx-auto grid w-full max-w-7xl items-center gap-10 px-5 pb-14 pt-8 md:grid-cols-[minmax(0,0.92fr)_minmax(420px,1.08fr)] md:px-8 md:pb-18 md:pt-12">
          <div className="min-w-0">
            <Badge className="border border-[#ff2f73]/20 bg-white text-[#d8175b] shadow-sm">
              <Sparkles className="size-3" />
              从小说原文到可投放短剧资产
            </Badge>
            <h1 className="mt-6 max-w-3xl text-5xl font-black leading-[0.98] text-[#17171b] md:text-7xl">
              把一本小说变成一条短剧生产线
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-[#4f5057]">
              上传原文，平台自动生成 Story Bible、轮次上下文、分集对白、
              视频 brief、本地化包和质量门禁记录。适合版权测剧、厂牌量产、
              出海改编与招商演示。
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Button asChild size="lg">
                <Link href="/projects/new">
                  <Play className="size-4" />
                  体验产品演示
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link href="/projects">
                  <Gauge className="size-4" />
                  进入项目工作台
                </Link>
              </Button>
            </div>
            <div className="mt-8 grid max-w-2xl grid-cols-3 gap-3">
              {[
                ["60-120", "目标集数"],
                ["4", "核心交付链路"],
                ["24/7", "异步任务队列"],
              ].map(([value, label]) => (
                <div key={label} className="border-l border-black/15 pl-4">
                  <div className="text-2xl font-black text-[#17171b]">{value}</div>
                  <div className="mt-1 text-xs font-bold text-[#74747b]">{label}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="relative min-w-0">
            <div className="absolute -left-6 top-8 hidden h-24 w-24 rounded-lg bg-[#2aa876] opacity-90 shadow-[0_18px_40px_rgba(42,168,118,0.24)] md:block" />
            <div className="absolute -right-5 bottom-8 hidden h-32 w-20 rounded-lg bg-[#e6a22f] opacity-90 shadow-[0_18px_40px_rgba(230,162,47,0.24)] md:block" />
            <div className="relative rounded-lg border border-black/10 bg-[#17171b] p-3 shadow-[0_28px_70px_rgba(23,23,27,0.28)]">
              <div className="rounded-md bg-[#f5f3ec] p-4">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-black/10 pb-4">
                  <div>
                    <div className="text-xs font-black uppercase text-[#ff2f73]">
                      Live Production Board
                    </div>
                    <div className="mt-1 text-xl font-black">《她从灰烬归来》EP01-EP12</div>
                  </div>
                  <Badge className="bg-[#17171b] text-white">Round 3 生成中</Badge>
                </div>

                <div className="mt-4 grid gap-3 md:grid-cols-[0.92fr_1.08fr]">
                  <div className="space-y-3">
                    {[
                      ["原文资产", "第 1-18 章已锁定"],
                      ["Story Bible", "人物动机与冲突线同步"],
                      ["当前集基线", "旧稿保护范围已加载"],
                    ].map(([label, value]) => (
                      <div key={label} className="rounded-lg border border-black/10 bg-white p-4">
                        <div className="text-xs font-bold text-[#77777e]">{label}</div>
                        <div className="mt-2 text-sm font-black text-[#17171b]">{value}</div>
                      </div>
                    ))}
                  </div>
                  <div className="rounded-lg border border-black/10 bg-white p-4">
                    <div className="flex items-center justify-between">
                      <div className="text-sm font-black">短剧脚本片段</div>
                      <Clapperboard className="size-4 text-[#ff2f73]" />
                    </div>
                    <div className="mt-4 space-y-3 font-mono text-xs leading-6 text-[#3c3c42]">
                      <p>（夜，雨水砸在玻璃幕墙上。林棠推门而入。）</p>
                      <p>
                        林棠：你们以为我回来，是为了求一个位置？
                      </p>
                      <p>（众人沉默。她把旧合同拍在桌面。）</p>
                      <p className="border-l-4 border-[#ff2f73] bg-[#fff0f6] py-2 pl-3 font-sans font-bold text-[#17171b]">
                        Hook: 反转身份在第 48 秒露出
                      </p>
                    </div>
                    <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs font-bold">
                      <div className="rounded-md bg-[#edf8f3] p-2 text-[#1d7d56]">证据 94</div>
                      <div className="rounded-md bg-[#fff7e5] p-2 text-[#9a6700]">节奏 A</div>
                      <div className="rounded-md bg-[#eef3ff] p-2 text-[#285fc2]">可拍摄</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="demo" className="bg-white py-16 md:py-20">
        <div className="mx-auto w-full max-w-7xl px-5 md:px-8">
          <div className="flex flex-col justify-between gap-5 md:flex-row md:items-end">
            <div>
              <p className="text-sm font-black uppercase text-[#ff2f73]">产品演示</p>
              <h2 className="mt-3 max-w-2xl text-3xl font-black leading-tight md:text-5xl">
                不再让编剧和运营在文档里反复搬运上下文
              </h2>
            </div>
            <p className="max-w-md text-sm leading-7 text-[#5f6068]">
              平台把“原文、当前稿、质量评估、交付资产”绑定在同一条改编链路里，
              每一轮都能继续生产，而不是重新开始。
            </p>
          </div>
          <div className="mt-10 grid gap-4 md:grid-cols-4">
            {demoSteps.map((step, index) => {
              const Icon = step.icon;
              return (
                <article key={step.title} className="rounded-lg border border-black/10 bg-[#fbfaf7] p-5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-black text-[#8c8c93]">0{index + 1}</span>
                    <Icon className="size-5 text-[#ff2f73]" />
                  </div>
                  <h3 className="mt-8 text-lg font-black">{step.title}</h3>
                  <p className="mt-3 text-sm leading-6 text-[#62636b]">{step.body}</p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section id="showcase" className="bg-[#f0efe9] py-16 md:py-20">
        <div className="mx-auto w-full max-w-7xl px-5 md:px-8">
          <div className="grid gap-8 md:grid-cols-[0.76fr_1.24fr] md:items-start">
            <div>
              <p className="text-sm font-black uppercase text-[#2a8060]">作品展示</p>
              <h2 className="mt-3 text-3xl font-black leading-tight md:text-5xl">
                给业务方看的不是概念，是可验收的项目包
              </h2>
              <p className="mt-5 text-sm leading-7 text-[#5f6068]">
                每个样张都围绕真实生产问题：覆盖率、改动边界、节奏钩子、
                交付格式、出海本地化。
              </p>
            </div>
            <div className="grid gap-4">
              {showcases.map((item) => (
                <article key={item.name} className="grid gap-4 rounded-lg border border-black/10 bg-white p-5 md:grid-cols-[1fr_auto]">
                  <div>
                    <Badge variant="outline">{item.tag}</Badge>
                    <h3 className="mt-4 text-2xl font-black">{item.name}</h3>
                    <p className="mt-3 text-sm leading-6 text-[#62636b]">{item.summary}</p>
                  </div>
                  <div className="flex items-end">
                    <div className="rounded-lg bg-[#17171b] px-4 py-3 text-sm font-black text-white">
                      {item.metric}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section id="ops" className="bg-[#17171b] py-16 text-white md:py-20">
        <div className="mx-auto grid w-full max-w-7xl gap-10 px-5 md:grid-cols-[0.95fr_1.05fr] md:px-8">
          <div>
            <p className="text-sm font-black uppercase text-[#e6a22f]">内部运营看板</p>
            <h2 className="mt-3 text-3xl font-black leading-tight md:text-5xl">
              从试用到付费，平台状态都能被运营接住
            </h2>
            <p className="mt-5 text-sm leading-7 text-white/68">
              项目队列、质量回归、点数钱包、成员权限和 API key 不再散落在脚本里。
              管理者可以直接看见产能、成本和风险。
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Button asChild variant="secondary">
                <Link href="/platform">
                  <CircleDollarSign className="size-4" />
                  平台与点数
                </Link>
              </Button>
              <Button asChild variant="outline" className="border-white/20 bg-white/5 text-white hover:bg-white/10">
                <Link href="/quality">
                  <LineChart className="size-4" />
                  内部回归
                </Link>
              </Button>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {dashboardSignals.map(([label, value, color]) => (
              <div key={label} className="rounded-lg border border-white/12 bg-white/[0.06] p-5">
                <div className={`mb-8 h-2 w-16 rounded-full ${color}`} />
                <div className="text-sm font-bold text-white/58">{label}</div>
                <div className="mt-2 text-2xl font-black">{value}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="partners" className="bg-white py-16 md:py-20">
        <div className="mx-auto w-full max-w-7xl px-5 md:px-8">
          <div className="rounded-lg border border-black/10 bg-[#fbfaf7] p-6 md:p-10">
            <div className="grid gap-8 md:grid-cols-[1fr_auto] md:items-end">
              <div>
                <p className="text-sm font-black uppercase text-[#3b7cf6]">招商落地</p>
                <h2 className="mt-3 max-w-3xl text-3xl font-black leading-tight md:text-5xl">
                  把版权、编剧、制作和出海团队接到同一条改编流水线
                </h2>
                <div className="mt-7 flex flex-wrap gap-2">
                  {partnerTypes.map((type) => (
                    <Badge key={type} variant="outline" className="bg-white">
                      {type}
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="flex flex-col gap-3 sm:flex-row md:flex-col">
                <Button asChild size="lg">
                  <Link href="/projects/new">
                    <Rocket className="size-4" />
                    上传小说试跑
                  </Link>
                </Button>
                <Button asChild size="lg" variant="outline">
                  <Link href="/methodology">
                    <ShieldCheck className="size-4" />
                    查看方法论
                  </Link>
                </Button>
              </div>
            </div>
            <div className="mt-10 grid gap-4 md:grid-cols-3">
              {[
                [Users, "团队协作", "租户、成员、角色和 API key 已有平台边界。"],
                [KeyRound, "机器接入", "自动化脚本可以通过密钥进入项目与任务链路。"],
                [Gauge, "成本可见", "点数、账单和任务用量面向商业化扩展。"],
              ].map(([Icon, title, body]) => {
                const FeatureIcon = Icon as typeof Users;
                return (
                  <div key={title as string} className="rounded-lg border border-black/10 bg-white p-5">
                    <FeatureIcon className="size-5 text-[#ff2f73]" />
                    <h3 className="mt-5 text-lg font-black">{title as string}</h3>
                    <p className="mt-2 text-sm leading-6 text-[#62636b]">{body as string}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-black/10 bg-[#f7f6f2] px-5 py-8 md:px-8">
        <div className="mx-auto flex max-w-7xl flex-col justify-between gap-4 text-sm text-[#68686f] md:flex-row md:items-center">
          <span className="font-bold text-[#17171b]">Novel-to-Drama</span>
          <span>小说转短剧生产平台 · Story Bible · 轮次改编 · 质量门禁 · 交付资产</span>
        </div>
      </footer>
    </main>
  );
}
