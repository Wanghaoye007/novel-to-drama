import { and, desc, eq } from "drizzle-orm";
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
