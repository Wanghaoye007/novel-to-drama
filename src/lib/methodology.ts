import { and, desc, eq } from "drizzle-orm";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { v4 as uuid } from "uuid";
import { db, schema } from "@/db/client";

export type MethodologyStatus = "draft" | "active" | "archived" | "rejected";

export type MethodologyCardView = {
  id: string;
  sourceId: string;
  name: string;
  category: string;
  status: MethodologyStatus;
  appliesToChannel: string[];
  appliesToGenre: string[];
  appliesToStage: string[];
  trigger: string;
  generationRule: string;
  qualityRule: string;
  positiveExamples: string[];
  negativeExamples: string[];
  version: number;
  updatedAt: number;
};

export type MethodologySourceView = {
  id: string;
  title: string;
  sourceType: string;
  rawText: string;
  originPath: string | null;
  status: MethodologyStatus;
  cardCount: number;
  createdAt: number;
  updatedAt: number;
};

export type MethodologyRunView = {
  id: string;
  projectId: string | null;
  roundId: string | null;
  sourceStrengthJson: string | null;
  methodologyContextJson: string | null;
  methodologyQualityJson: string | null;
  createdAt: number;
};

export type MethodologyData = {
  sources: MethodologySourceView[];
  cards: MethodologyCardView[];
  runs: MethodologyRunView[];
};

type MethodologyScope = {
  tenantId: string;
};

type BuiltInMethodologyCard = {
  id: string;
  source_id: string;
  name: string;
  category: string;
  applies_to_channel?: string[];
  applies_to_genre?: string[];
  applies_to_stage?: string[];
  trigger: string;
  generation_rule: string;
  quality_rule: string;
  positive_examples?: string[];
  negative_examples?: string[];
  status?: MethodologyStatus;
  version?: number;
};

type BuiltInSyncResult = {
  sourcesCreated: number;
  sourcesUpdated: number;
  cardsCreated: number;
  cardsUpdated: number;
  totalCards: number;
};

type ExtractedMethodologyCard = {
  name: string;
  category: string;
  appliesToChannel: string[];
  appliesToGenre: string[];
  appliesToStage: string[];
  trigger: string;
  generationRule: string;
  qualityRule: string;
  positiveExamples: string[];
  negativeExamples: string[];
};

const CATEGORY_RULES: Array<[string, string[]]> = [
  ["opening_design", ["开场", "前三秒", "前3秒", "3 秒", "3秒", "hook", "钩子"]],
  ["cliffhanger", ["断点", "结尾", "追更", "悬念", "下一集"]],
  ["visual_translation", ["视听", "镜头", "画面", "分镜", "景别", "运镜", "show", "动作行"]],
  ["dialogue", ["台词", "对白", "潜台词", "OS", "VO", "三不原则"]],
  ["character_bible", ["人物", "人设", "OOC", "动机", "角色", "功能性配角", "反派"]],
  ["series_structure", ["全剧", "结构", "三幕", "情绪曲线", "小高潮", "大高潮"]],
  ["episode_plan", ["单集", "每集", "30秒", "三波", "信息增量", "剧情推进"]],
  ["production_feasibility", ["拍摄", "成本", "场景", "道具", "制作", "可执行"]],
  ["source_fidelity", ["强原文", "轻改", "名场面", "原文资产", "主动方", "因果", "C0", "C1"]],
];

const CATEGORY_STAGES: Record<string, string[]> = {
  source_fidelity: ["episode_plan", "script_generation", "quality_gate"],
  opening_design: ["episode_plan", "script_generation", "quality_gate"],
  cliffhanger: ["episode_plan", "script_generation", "quality_gate"],
  visual_translation: ["script_generation", "quality_gate"],
  dialogue: ["script_generation", "quality_gate"],
  character_bible: ["story_bible", "episode_plan", "script_generation", "quality_gate"],
  series_structure: ["series_structure", "episode_plan"],
  episode_plan: ["episode_plan", "script_generation", "quality_gate"],
  production_feasibility: ["script_generation", "quality_gate"],
  general_adaptation: ["episode_context", "story_bible", "script_generation", "quality_gate"],
};

const builtInSourceTitles: Record<string, string> = {
  method_source_strong_source_light_v1: "强原文轻改规则",
  dj_project_00_sop: "DJ_Project 改编 SOP 总纲",
  dj_project_03_05_hook: "DJ_Project 节奏钩子与断集法",
  dj_project_04_character: "DJ_Project 人物方法论",
  dj_project_05_09_analysis: "DJ_Project 身份层级与钥匙系统",
  dj_project_06_plot_patterns: "DJ_Project 情节模式库",
  dj_project_08_09_analysis: "DJ_Project 拆剧分析方法",
  dj_project_00_12_dialogue: "DJ_Project 台词与功能对白",
  dj_project_00_13_shot: "DJ_Project 动作行与镜头逻辑",
  dj_project_12_mumu_female_male: "DJ_Project 木木脚本学习通用",
  dj_project_12_mumu_scripts: "DJ_Project 木木脚本 OS/VO 规则",
  dj_project_13_shot_logic: "DJ_Project 镜头逻辑深度分析",
  dj_project_12_mumu_male: "DJ_Project 男频实战脚本模式",
  dj_project_12_mumu_female: "DJ_Project 女频实战脚本模式",
  short_drama_333_engine_v1: "小说转爆款短剧剧本改编引擎 3-3-3",
};

function builtInId(scope: MethodologyScope, id: string): string {
  return `${scope.tenantId}:${id}`;
}

function safeStatus(status: string | undefined): MethodologyStatus {
  if (
    status === "draft" ||
    status === "active" ||
    status === "archived" ||
    status === "rejected"
  ) {
    return status;
  }
  return "draft";
}

function compactRule(text: string, limit = 260): string {
  const compact = text.replace(/\s+/g, " ").replace(/^[\s\-#*`：:]+|[\s\-#*`：:]+$/g, "");
  if (compact.length <= limit) return compact;
  return `${compact.slice(0, limit - 1).replace(/[，。；,;\s]+$/g, "")}…`;
}

function cleanHeading(value: string): string {
  const heading = value
    .replace(/^#+\s*/, "")
    .replace(/^[一二三四五六七八九十\d]+[、.．]\s*/, "")
    .replace(/^Step\s*\d+[:：-]?\s*/i, "")
    .replace(/^[\s\-#*`：:]+|[\s\-#*`：:]+$/g, "");
  return heading || "通用改编规则";
}

function splitMethodologyBlocks(rawText: string, fallbackTitle: string): Array<{ title: string; text: string }> {
  const blocks: Array<{ title: string; lines: string[] }> = [];
  let currentTitle = fallbackTitle;
  let currentLines: string[] = [];

  for (const line of rawText.split(/\r?\n/)) {
    const match = line.trim().match(/^(#{1,4})\s+(.+?)\s*$/);
    if (match) {
      if (currentLines.length) {
        blocks.push({ title: currentTitle, lines: currentLines });
      }
      currentTitle = cleanHeading(match[2] ?? fallbackTitle);
      currentLines = [];
      continue;
    }
    currentLines.push(line);
  }

  if (currentLines.length) {
    blocks.push({ title: currentTitle, lines: currentLines });
  }

  const cleaned = blocks
    .map((block) => ({ title: block.title, text: block.lines.join("\n").trim() }))
    .filter((block) => block.text.length >= 30);

  return cleaned.length ? cleaned : [{ title: fallbackTitle, text: rawText.trim() }];
}

function inferCategory(text: string, title: string): string {
  const haystack = `${title}\n${text}`.toLowerCase();
  for (const [category, tokens] of CATEGORY_RULES) {
    if (tokens.some((token) => haystack.includes(token.toLowerCase()))) {
      return category;
    }
  }
  return "general_adaptation";
}

function inferChannels(text: string): string[] {
  const channels: string[] = [];
  if (["女频", "现言", "古言", "甜宠", "追妻", "真假千金"].some((token) => text.includes(token))) {
    channels.push("female");
  }
  if (["男频", "玄幻", "历史", "赘婿", "战神", "经商"].some((token) => text.includes(token))) {
    channels.push("male");
  }
  if (!channels.length) return ["female", "male", "mixed"];
  if (channels.length === 2) channels.push("mixed");
  return Array.from(new Set(channels));
}

function inferGenres(text: string, category: string): string[] {
  const genres: string[] = [];
  const genreTokens: Record<string, string[]> = {
    identity: ["身份", "真假千金", "马甲", "继承人", "认亲"],
    revenge: ["复仇", "反击", "打脸", "清算"],
    billionaire: ["豪门", "霸总", "总裁"],
    transmigration: ["穿越", "重生", "系统", "预知"],
    business_counterattack: ["经商", "商战", "创业", "赚钱"],
    comedy: ["轻喜", "喜剧", "误会"],
  };
  for (const [genre, tokens] of Object.entries(genreTokens)) {
    if (tokens.some((token) => text.includes(token))) genres.push(genre);
  }
  if ((category === "source_fidelity" || category === "general_adaptation") && !genres.includes("unknown")) {
    genres.push("unknown");
  }
  return Array.from(new Set(genres.length ? genres : ["unknown"]));
}

function linesMatching(text: string, tokens: string[], limit = 3): string[] {
  const lines: string[] = [];
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.replace(/^[\s\-#*`]+|[\s\-#*`]+$/g, "");
    if (line.length < 6) continue;
    if (tokens.some((token) => line.includes(token))) {
      lines.push(compactRule(line, 140));
    }
    if (lines.length >= limit) break;
  }
  return lines;
}

function fallbackTrigger(category: string): string {
  if (category === "source_fidelity") return "原文已具备强冲突、强钩子、强反差或高情绪名场面";
  if (category === "opening_design") return "本集开场缺少前三秒可见冲突或原文天然钩子需要保护";
  if (category === "visual_translation") return "小说段落含内心戏、环境描写或抽象情绪，需要转成画面/动作/音效";
  if (category === "dialogue") return "台词过长、书面化或缺少潜台词时";
  if (category === "character_bible") return "人物动机、功能或台词风格存在 OOC 风险时";
  if (category === "cliffhanger") return "单集结尾缺少追更断点或断点说明化时";
  return "当前阶段需要引用内部方法论";
}

function fallbackGenerationRule(category: string, blockText: string): string {
  if (category === "source_fidelity") {
    return "保留原文主动方、因果顺序、名场面和情绪曲线，只做视听化、压缩、镜头补强和短台词化。";
  }
  return compactRule(blockText, 320);
}

function fallbackQualityRule(category: string): string {
  if (category === "source_fidelity") {
    return "如果脚本删除 C1 名场面、改变 C0 主动方、把克制情绪改成歇斯底里或新增 C4 编造道具/动作/狠话，必须 needs_rewrite。";
  }
  if (category === "character_bible") return "检查人物动机、主动权、台词风格和功能定位是否与 Story Bible 一致。";
  if (category === "visual_translation") return "检查抽象心理是否被转成可拍动作、表情、道具、景别、运镜和音效。";
  if (category === "dialogue") return "检查台词是否短、口语化、有潜台词，且每句都推进剧情或塑造人物。";
  if (category === "cliffhanger") return "检查结尾是否停在动作、证据、身份、关系或危机爆点前一秒。";
  return "检查输出是否遵守该方法论的触发条件和生成规则。";
}

function ruleFromLines(text: string, preferredTokens: string[], fallback: string): string {
  const matches = linesMatching(text, preferredTokens, 4);
  if (matches.length) return compactRule(matches.join("；"), 320);
  return compactRule(fallback, 320);
}

function extractMethodologyCardsFromText(title: string, rawText: string): ExtractedMethodologyCard[] {
  const blocks = splitMethodologyBlocks(rawText, title).slice(0, 12);
  return blocks.map((block) => {
    const category = inferCategory(block.text, block.title);
    return {
      name: cleanHeading(block.title),
      category,
      appliesToChannel: inferChannels(block.text),
      appliesToGenre: inferGenres(block.text, category),
      appliesToStage: CATEGORY_STAGES[category] ?? CATEGORY_STAGES.general_adaptation,
      trigger: ruleFromLines(block.text, ["触发", "适用", "场景", "当", "如果", "输入"], fallbackTrigger(category)),
      generationRule: ruleFromLines(
        block.text,
        ["方法", "操作", "执行", "生成", "原则", "必须", "要"],
        fallbackGenerationRule(category, block.text)
      ),
      qualityRule: ruleFromLines(
        block.text,
        ["质检", "自检", "检查", "验收", "失败", "禁止", "不得", "错误"],
        fallbackQualityRule(category)
      ),
      positiveExamples: linesMatching(block.text, ["正例", "示例", "例：", "例如", "正确"], 3),
      negativeExamples: linesMatching(block.text, ["反例", "错误", "常见错误", "坑", "禁止", "不得"], 3),
    };
  });
}

function sourceTypeFromInput(inputType: string | undefined, originPath: string | null | undefined): string {
  const trimmed = inputType?.trim();
  if (trimmed && trimmed !== "sop") return trimmed;
  const ext = originPath?.toLowerCase().match(/\.([a-z0-9]+)$/)?.[1];
  if (ext === "md" || ext === "markdown") return "markdown";
  if (ext === "txt") return "txt";
  return trimmed || "sop";
}

async function loadBuiltInMethodologyCards(): Promise<BuiltInMethodologyCard[]> {
  const cardsPath = path.join(process.cwd(), "examples", "methodology_cards.json");
  const raw = await readFile(cardsPath, "utf-8");
  const parsed = JSON.parse(raw) as unknown;
  if (!Array.isArray(parsed)) {
    throw new Error(`methodology_cards.json must contain an array: ${cardsPath}`);
  }
  return parsed as BuiltInMethodologyCard[];
}

export function parseArray(raw: string | null): string[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? parsed.map(String).filter(Boolean) : [];
  } catch {
    return [];
  }
}

function sourceToView(
  row: typeof schema.methodologySources.$inferSelect,
  cardCount: number
): MethodologySourceView {
  return {
    id: row.id,
    title: row.title,
    sourceType: row.sourceType,
    rawText: row.rawText,
    originPath: row.originPath,
    status: row.status,
    cardCount,
    createdAt: row.createdAt.getTime(),
    updatedAt: row.updatedAt.getTime(),
  };
}

export function cardToView(
  row: typeof schema.methodologyCards.$inferSelect
): MethodologyCardView {
  return {
    id: row.id,
    sourceId: row.sourceId,
    name: row.name,
    category: row.category,
    status: row.status,
    appliesToChannel: parseArray(row.appliesToChannelJson),
    appliesToGenre: parseArray(row.appliesToGenreJson),
    appliesToStage: parseArray(row.appliesToStageJson),
    trigger: row.trigger,
    generationRule: row.generationRule,
    qualityRule: row.qualityRule,
    positiveExamples: parseArray(row.positiveExamplesJson),
    negativeExamples: parseArray(row.negativeExamplesJson),
    version: row.version,
    updatedAt: row.updatedAt.getTime(),
  };
}

function runToView(row: typeof schema.methodologyRuns.$inferSelect): MethodologyRunView {
  return {
    id: row.id,
    projectId: row.projectId,
    roundId: row.roundId,
    sourceStrengthJson: row.sourceStrengthJson,
    methodologyContextJson: row.methodologyContextJson,
    methodologyQualityJson: row.methodologyQualityJson,
    createdAt: row.createdAt.getTime(),
  };
}

export async function listMethodology(
  scope: MethodologyScope
): Promise<MethodologyData> {
  const [sources, cards, runs] = await Promise.all([
    db.query.methodologySources.findMany({
      where: eq(schema.methodologySources.tenantId, scope.tenantId),
      orderBy: [desc(schema.methodologySources.updatedAt)],
    }),
    db.query.methodologyCards.findMany({
      where: eq(schema.methodologyCards.tenantId, scope.tenantId),
      orderBy: [desc(schema.methodologyCards.updatedAt)],
    }),
    db.query.methodologyRuns.findMany({
      where: eq(schema.methodologyRuns.tenantId, scope.tenantId),
      orderBy: [desc(schema.methodologyRuns.createdAt)],
      limit: 12,
    }),
  ]);

  const countBySource = new Map<string, number>();
  for (const card of cards) {
    countBySource.set(card.sourceId, (countBySource.get(card.sourceId) || 0) + 1);
  }

  return {
    sources: sources.map((source) =>
      sourceToView(source, countBySource.get(source.id) || 0)
    ),
    cards: cards.map(cardToView),
    runs: runs.map(runToView),
  };
}

export async function createMethodologySource(
  scope: MethodologyScope,
  input: {
    title: string;
    sourceType: string;
    rawText: string;
    originPath?: string | null;
  }
) {
  const now = new Date();
  const sourceId = uuid();
  const title = input.title.trim();
  const originPath = input.originPath?.trim() || null;
  const sourceType = sourceTypeFromInput(input.sourceType, originPath);
  const extractedCards = extractMethodologyCardsFromText(title, input.rawText);

  await db.insert(schema.methodologySources).values({
    id: sourceId,
    tenantId: scope.tenantId,
    title,
    sourceType,
    rawText: input.rawText,
    originPath,
    status: "draft",
    createdAt: now,
    updatedAt: now,
  });

  const cardIds: string[] = [];
  for (const card of extractedCards) {
    const cardId = uuid();
    cardIds.push(cardId);
    await db.insert(schema.methodologyCards).values({
      id: cardId,
      tenantId: scope.tenantId,
      sourceId,
      name: card.name,
      category: card.category,
      appliesToChannelJson: JSON.stringify(card.appliesToChannel),
      appliesToGenreJson: JSON.stringify(card.appliesToGenre),
      appliesToStageJson: JSON.stringify(card.appliesToStage),
      trigger: card.trigger,
      generationRule: card.generationRule,
      qualityRule: card.qualityRule,
      positiveExamplesJson: JSON.stringify(card.positiveExamples),
      negativeExamplesJson: JSON.stringify(card.negativeExamples),
      status: "draft",
      version: 1,
      createdAt: now,
      updatedAt: now,
    });
  }

  return { sourceId, cardIds, cardCount: cardIds.length };
}

export async function syncBuiltInMethodologyCards(
  scope: MethodologyScope
): Promise<BuiltInSyncResult> {
  const cards = await loadBuiltInMethodologyCards();
  const now = new Date();
  const cardsBySource = new Map<string, BuiltInMethodologyCard[]>();

  for (const card of cards) {
    if (!card.id || !card.source_id || !card.name) continue;
    const bucket = cardsBySource.get(card.source_id) ?? [];
    bucket.push(card);
    cardsBySource.set(card.source_id, bucket);
  }

  let sourcesCreated = 0;
  let sourcesUpdated = 0;
  let cardsCreated = 0;
  let cardsUpdated = 0;

  for (const [sourceId, sourceCards] of cardsBySource.entries()) {
    const sourceDbId = builtInId(scope, sourceId);
    const title = builtInSourceTitles[sourceId] ?? sourceId;
    const rawText = sourceCards
      .map((card) => `- ${card.name}: ${card.generation_rule}`)
      .join("\n");
    const existingSource = await db.query.methodologySources.findFirst({
      where: eq(schema.methodologySources.id, sourceDbId),
    });

    if (existingSource) {
      await db
        .update(schema.methodologySources)
        .set({
          title,
          sourceType: "builtin",
          rawText,
          originPath: "examples/methodology_cards.json",
          status: "active",
          updatedAt: now,
        })
        .where(
          and(
            eq(schema.methodologySources.id, sourceDbId),
            eq(schema.methodologySources.tenantId, scope.tenantId)
          )
        );
      sourcesUpdated += 1;
    } else {
      await db.insert(schema.methodologySources).values({
        id: sourceDbId,
        tenantId: scope.tenantId,
        title,
        sourceType: "builtin",
        rawText,
        originPath: "examples/methodology_cards.json",
        status: "active",
        createdAt: now,
        updatedAt: now,
      });
      sourcesCreated += 1;
    }

    for (const card of sourceCards) {
      const cardDbId = builtInId(scope, card.id);
      const values = {
        tenantId: scope.tenantId,
        sourceId: sourceDbId,
        name: card.name,
        category: card.category,
        appliesToChannelJson: JSON.stringify(card.applies_to_channel ?? []),
        appliesToGenreJson: JSON.stringify(card.applies_to_genre ?? []),
        appliesToStageJson: JSON.stringify(card.applies_to_stage ?? []),
        trigger: card.trigger,
        generationRule: card.generation_rule,
        qualityRule: card.quality_rule,
        positiveExamplesJson: JSON.stringify(card.positive_examples ?? []),
        negativeExamplesJson: JSON.stringify(card.negative_examples ?? []),
        status: safeStatus(card.status),
        version: card.version ?? 1,
        updatedAt: now,
      };
      const existingCard = await db.query.methodologyCards.findFirst({
        where: eq(schema.methodologyCards.id, cardDbId),
      });

      if (existingCard) {
        await db
          .update(schema.methodologyCards)
          .set(values)
          .where(
            and(
              eq(schema.methodologyCards.id, cardDbId),
              eq(schema.methodologyCards.tenantId, scope.tenantId)
            )
          );
        cardsUpdated += 1;
      } else {
        await db.insert(schema.methodologyCards).values({
          id: cardDbId,
          ...values,
          createdAt: now,
        });
        cardsCreated += 1;
      }
    }
  }

  return {
    sourcesCreated,
    sourcesUpdated,
    cardsCreated,
    cardsUpdated,
    totalCards: cards.length,
  };
}

export async function updateMethodologyCardStatus(
  scope: MethodologyScope,
  id: string,
  status: MethodologyStatus
) {
  const result = await db
    .update(schema.methodologyCards)
    .set({ status, updatedAt: new Date() })
    .where(
      and(
        eq(schema.methodologyCards.id, id),
        eq(schema.methodologyCards.tenantId, scope.tenantId)
      )
  );
  return result.changes > 0;
}

export async function getMethodologyCard(
  scope: MethodologyScope,
  id: string
): Promise<MethodologyCardView | null> {
  const row = await db.query.methodologyCards.findFirst({
    where: and(
      eq(schema.methodologyCards.id, id),
      eq(schema.methodologyCards.tenantId, scope.tenantId)
    ),
  });
  return row ? cardToView(row) : null;
}
