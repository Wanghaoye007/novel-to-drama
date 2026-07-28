import assert from "node:assert/strict";
import test from "node:test";
import {
  applyMethodologyCardStatus,
  methodologyCardActions,
  methodologyStatusLabel,
} from "../src/lib/methodology-controls";
import type {
  MethodologyCardView,
  MethodologyData,
  MethodologyStatus,
} from "../src/lib/methodology";

function card(
  id: string,
  status: MethodologyStatus,
  updatedAt: number
): MethodologyCardView {
  return {
    id,
    sourceId: "source-1",
    name: id,
    category: "source_fidelity",
    status,
    appliesToChannel: [],
    appliesToGenre: [],
    appliesToStage: [],
    trigger: "trigger",
    generationRule: "generation",
    qualityRule: "quality",
    positiveExamples: [],
    negativeExamples: [],
    version: 1,
    updatedAt,
  };
}

test("active methodology cards expose a clear enabled state and a real stop action", () => {
  assert.equal(methodologyStatusLabel("active"), "已启用");
  assert.deepEqual(methodologyCardActions("active"), [
    { label: "停用", status: "archived", variant: "outline" },
  ]);
});

test("inactive methodology cards expose an activation action", () => {
  assert.deepEqual(methodologyCardActions("draft"), [
    { label: "启用", status: "active", variant: "default" },
    { label: "拒绝", status: "rejected", variant: "destructive" },
  ]);
  assert.deepEqual(methodologyCardActions("archived"), [
    { label: "重新启用", status: "active", variant: "default" },
    { label: "拒绝", status: "rejected", variant: "destructive" },
  ]);
  assert.deepEqual(methodologyCardActions("rejected"), [
    { label: "重新启用", status: "active", variant: "default" },
    { label: "归档", status: "archived", variant: "outline" },
  ]);
});

test("optimistic methodology status updates touch only the selected card", () => {
  const data = {
    sources: [],
    runs: [],
    cards: [
      card("card-a", "draft", 1),
      card("card-b", "active", 2),
    ],
  } satisfies MethodologyData;

  const updated = applyMethodologyCardStatus(data, "card-a", "active", 100);

  assert.equal(updated.cards[0]?.status, "active");
  assert.equal(updated.cards[0]?.updatedAt, 100);
  assert.equal(updated.cards[1], data.cards[1]);
  assert.equal(data.cards[0]?.status, "draft");
});
