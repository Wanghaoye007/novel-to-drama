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
  const cardId = uuid();
  const title = input.title.trim();

  await db.insert(schema.methodologySources).values({
    id: sourceId,
    tenantId: scope.tenantId,
    title,
    sourceType: input.sourceType.trim() || "sop",
    rawText: input.rawText,
    originPath: input.originPath?.trim() || null,
    status: "draft",
    createdAt: now,
    updatedAt: now,
  });

  await db.insert(schema.methodologyCards).values({
    id: cardId,
    tenantId: scope.tenantId,
    sourceId,
    name: title,
    category: "source_fidelity",
    appliesToChannelJson: JSON.stringify(["female", "male", "mixed"]),
    appliesToGenreJson: JSON.stringify(["unknown"]),
    appliesToStageJson: JSON.stringify([
      "episode_plan",
      "script_generation",
      "quality_gate",
    ]),
    trigger: "原文具备强冲突、强钩子、强反差或高情绪名场面",
    generationRule:
      "保留原文主动方、因果顺序、名场面和情绪曲线，只做视听化、压缩、镜头补强和短台词化。",
    qualityRule:
      "删除 C1 名场面、改变 C0 主动方或新增 C4 编造内容时必须阻断。",
    positiveExamplesJson: JSON.stringify([]),
    negativeExamplesJson: JSON.stringify([]),
    status: "draft",
    version: 1,
    createdAt: now,
    updatedAt: now,
  });

  return { sourceId, cardId };
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
