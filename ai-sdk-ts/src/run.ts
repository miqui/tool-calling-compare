// Real-LLM runner (local only, never CI): npx tsx src/run.ts <scenario-id> [variant]
import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import { scenarios } from "./scenarios/index.ts";

const [id, variant] = process.argv.slice(2);
const mod = id ? scenarios[id] : undefined;
if (!mod) {
  console.error(`usage: tsx src/run.ts <scenario-id> [variant]\navailable: ${Object.keys(scenarios).join(", ")}`);
  process.exit(2);
}
const apiKey = process.env.OPENROUTER_API_KEY;
if (!apiKey) {
  console.error("OPENROUTER_API_KEY is not set (real runs are local only).");
  process.exit(2);
}
const openrouter = createOpenAICompatible({
  name: "openrouter",
  baseURL: "https://openrouter.ai/api/v1",
  apiKey,
});
const modelId = process.env.OPENROUTER_MODEL ?? "openai/gpt-4o-mini";
const outcome = await mod.run(openrouter.chatModel(modelId), { variant, sandbox: "./sandbox" });
console.log(JSON.stringify({ scenario: id, model: modelId, ...outcome }, null, 2));
