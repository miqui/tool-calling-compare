import { generateText, stepCountIs, tool, type LanguageModel, type StopCondition, type ToolSet } from "ai";
import { z } from "zod";
import { type AnySteps, Recorder, loadScenario, mockExecutor, summarize, type Outcome } from "../scenario.ts";

export const scenario = loadScenario("stuck-loop-detection");

/** True when the last `threshold` steps made identical tool calls (same names + inputs). */
export function isStuck(steps: AnySteps, threshold: number): boolean {
  if (steps.length < threshold) return false;
  const sigs = steps.slice(-threshold).map((s) => JSON.stringify(s.toolCalls.map((c) => [c.toolName, c.input])));
  return sigs[0] !== "[]" && sigs.every((s) => s === sigs[0]);
}

/** Custom StopCondition: stopWhen accepts functions of the step history. */
export const repeatedToolCalls =
  <T extends ToolSet>(threshold: number): StopCondition<T> =>
  ({ steps }) =>
    isStuck(steps, threshold);

export async function run(model: LanguageModel): Promise<Outcome> {
  const rec = new Recorder();
  const threshold = scenario.limits?.repeat_threshold ?? 3;
  const result = await generateText({
    model,
    prompt: scenario.prompt,
    stopWhen: [stepCountIs(scenario.limits?.max_steps ?? 10), repeatedToolCalls(threshold)],
    tools: {
      click: tool({
        description: "Click a UI element.",
        inputSchema: z.object({ target: z.string() }),
        execute: mockExecutor(scenario, "click", rec),
      }),
    },
  });
  const out = summarize(result.steps, rec);
  return isStuck(result.steps, threshold) ? { ...out, stoppedBy: "stuck_detected" } : out;
}
