import { generateText, stepCountIs, tool, type LanguageModel } from "ai";
import { z } from "zod";
import { Recorder, loadScenario, mockExecutor, summarize, type Outcome } from "../scenario.ts";

export const scenario = loadScenario("max-steps-exceeded");

/** stepCountIs(3) halts the loop; the last step still has finishReason "tool-calls" (=> max_steps). */
export async function run(model: LanguageModel): Promise<Outcome> {
  const rec = new Recorder();
  const result = await generateText({
    model,
    prompt: scenario.prompt,
    stopWhen: stepCountIs(scenario.limits?.max_steps ?? 3),
    tools: {
      check_queue: tool({
        description: "Return the current queue length.",
        inputSchema: z.object({}),
        execute: mockExecutor(scenario, "check_queue", rec),
      }),
    },
  });
  return summarize(result.steps, rec);
}
