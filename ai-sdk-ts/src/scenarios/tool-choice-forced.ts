import { generateText, stepCountIs, tool, type LanguageModel } from "ai";
import { z } from "zod";
import { Recorder, loadScenario, mockExecutor, summarize, type Outcome, type RunOptions } from "../scenario.ts";

export const scenario = loadScenario("tool-choice-forced");

/**
 * variant: undefined (auto) | "required" | "tool" (force log_greeting).
 * prepareStep forces step 0 only; a top-level toolChoice would apply to every step and block the final answer.
 */
export async function run(model: LanguageModel, opts: RunOptions = {}): Promise<Outcome> {
  const rec = new Recorder();
  const forced =
    opts.variant === "required"
      ? ("required" as const)
      : opts.variant === "tool"
        ? { type: "tool" as const, toolName: "log_greeting" as const }
        : undefined;
  const result = await generateText({
    model,
    prompt: scenario.prompt,
    stopWhen: stepCountIs(5),
    prepareStep: ({ stepNumber }) =>
      forced && stepNumber === 0 ? { toolChoice: forced } : { toolChoice: "auto" },
    tools: {
      log_greeting: tool({
        description: "Log a greeting.",
        inputSchema: z.object({ text: z.string() }),
        execute: mockExecutor(scenario, "log_greeting", rec),
      }),
      get_weather: tool({
        description: "Get current weather for a city.",
        inputSchema: z.object({ city: z.string() }),
        execute: mockExecutor(scenario, "get_weather", rec),
      }),
    },
  });
  return summarize(result.steps, rec);
}
