import { generateText, stepCountIs, tool, type LanguageModel } from "ai";
import { z } from "zod";
import { Recorder, loadScenario, mockExecutor, summarize, type Outcome } from "../scenario.ts";

export const scenario = loadScenario("sequential-dependent-calls");

/** get_latest_order needs find_user's output, so the model must use two sequential steps. */
export async function run(model: LanguageModel): Promise<Outcome> {
  const rec = new Recorder();
  const result = await generateText({
    model,
    prompt: scenario.prompt,
    stopWhen: stepCountIs(5),
    tools: {
      find_user: tool({
        description: "Find a user by email.",
        inputSchema: z.object({ email: z.string() }),
        execute: mockExecutor(scenario, "find_user", rec),
      }),
      get_latest_order: tool({
        description: "Get the latest order for a user id.",
        inputSchema: z.object({ user_id: z.string() }),
        execute: mockExecutor(scenario, "get_latest_order", rec),
      }),
    },
  });
  return summarize(result.steps, rec);
}
