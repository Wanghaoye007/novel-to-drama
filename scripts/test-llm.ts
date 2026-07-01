import { callLLM } from "../src/lib/anthropic";

(async () => {
  const out = await callLLM({
    model: "haiku",
    user: "Say 'hello world' and nothing else.",
  });
  console.log("LLM said:", out);
})();
