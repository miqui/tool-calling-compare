import { generateText, stepCountIs, tool, type LanguageModel } from "ai";
import { z } from "zod";
import { Recorder, loadScenario, mockExecutor, summarize, type Outcome } from "../scenario.ts";

export const scenario = loadScenario("tool-throws-error");

/** An exception in execute becomes a `tool-error` part (generateText does not throw); the model sees it next step. */
export async function run(model: LanguageModel): Promise<Outcome> {
  const rec = new Recorder();
  const result = await generateText({
    model,
    prompt: scenario.prompt,
    stopWhen: stepCountIs(5),
    tools: {
      fetch_url: tool({
        description: "Fetch a URL.",
        inputSchema: z.object({ url: z.string() }),
        execute: mockExecutor(scenario, "fetch_url", rec),
      }),
    },
  });
  return summarize(result.steps, rec);
}
