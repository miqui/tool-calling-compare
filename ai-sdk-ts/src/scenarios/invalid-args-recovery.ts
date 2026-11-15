import { generateText, stepCountIs, tool, type LanguageModel } from "ai";
import { z } from "zod";
import { Recorder, loadScenario, mockExecutor, summarize, type Outcome } from "../scenario.ts";

export const scenario = loadScenario("invalid-args-recovery");

/**
 * Schema-invalid input never reaches execute: the SDK records an InvalidToolInputError as a
 * `tool-error` content part and feeds it back, so the next step can retry with valid input.
 */
export async function run(model: LanguageModel): Promise<Outcome> {
  const rec = new Recorder();
  const result = await generateText({
    model,
    prompt: scenario.prompt,
    stopWhen: stepCountIs(5),
    tools: {
      set_timer: tool({
        description: "Set a timer for a number of minutes.",
        inputSchema: z.object({ minutes: z.number().int().min(1) }),
        execute: mockExecutor(scenario, "set_timer", rec),
      }),
    },
  });
  return summarize(result.steps, rec);
}
