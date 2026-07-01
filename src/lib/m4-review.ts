import { callLLM } from "./anthropic";
import {
  M4_WRITER_REVIEW,
  M4_AUDIENCE_REVIEW,
  M4_VILLAIN_REVIEW,
} from "./prompts/m4-review";
import { fill } from "./prompts/m2-bible";

export interface ReviewDimension {
  score: number;
  strengths: string[];
  issues: string[];
  verdict: "通过" | "需改";
}

export interface ReviewResult {
  overall_score: number;
  writer: ReviewDimension;
  audience: ReviewDimension;
  villain: ReviewDimension;
  status: "green" | "red";
}

async function runOne(template: string, script: string): Promise<ReviewDimension> {
  const raw = await callLLM({
    model: "haiku",
    user: fill(template, { SCRIPT: script }),
    maxTokens: 768,
    temperature: 0.3,
  });
  const match = raw.match(/\{[\s\S]*\}/);
  if (!match) throw new Error("no JSON in review");
  return JSON.parse(match[0]);
}

export async function reviewScript(script: string): Promise<ReviewResult> {
  const [writer, audience, villain] = await Promise.all([
    runOne(M4_WRITER_REVIEW, script),
    runOne(M4_AUDIENCE_REVIEW, script),
    runOne(M4_VILLAIN_REVIEW, script),
  ]);
  const overall = (writer.score + audience.score + villain.score) / 3;
  return {
    overall_score: Math.round(overall * 10) / 10,
    writer,
    audience,
    villain,
    status: overall >= 9.0 ? "green" : "red",
  };
}
