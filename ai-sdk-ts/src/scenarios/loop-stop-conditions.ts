import { generateText, hasToolCall, stepCountIs, tool, type LanguageModel } from "ai";
import { z } from "zod";
import { Recorder, loadScenario, mockExecutor, summarize, type Outcome, type ScriptTurn } from "../scenario.ts";

export const scenario = loadScenario("loop-stop-conditions");

/** TS-side mock script: the model never stops polling. */
export const script: ScriptTurn[] = Array.from({ length: 3 }, () => ({
  finish_reason: "tool_calls" as const,
  tool_calls: [{ name: "poll_status", arguments: {} }],
}));

/**
 * variant "has-tool-call": stop as soon as poll_status is called (hasToolCall) instead of
 * waiting for the step cap. Default: stepCountIs(max_steps).
 */
export async function run(model: LanguageModel, opts: { variant?: string } = {}): Promise<Outcome> {
  const rec = new Recorder();
  const cap = stepCountIs(scenario.limits?.max_steps ?? 3);
  const result = await generateText({
    model,
    prompt: scenario.prompt,
    stopWhen: opts.variant === "has-tool-call" ? [hasToolCall("poll_status"), cap] : cap,
    tools: {
      poll_status: tool({
        description: "Poll the job status.",
        inputSchema: z.object({}),
        execute: mockExecutor(scenario, "poll_status", rec),
      }),
    },
  });
  return summarize(result.steps, rec);
}
