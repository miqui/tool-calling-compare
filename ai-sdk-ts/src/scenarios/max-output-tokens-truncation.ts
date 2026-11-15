import { generateText, stepCountIs, tool, type LanguageModel } from "ai";
import { z } from "zod";
import { Recorder, loadScenario, mockExecutor, summarize, type Outcome } from "../scenario.ts";

export const scenario = loadScenario("max-output-tokens-truncation");

/** maxOutputTokens caps the response; finishReason "length" means no (partial) tool call is executed. */
export async function run(model: LanguageModel): Promise<Outcome> {
  const rec = new Recorder();
  const result = await generateText({
    model,
    prompt: scenario.prompt,
    maxOutputTokens: scenario.limits?.max_output_tokens ?? 16,
    stopWhen: stepCountIs(5),
    tools: {
      write_file: tool({
        description: "Write text to a file.",
        inputSchema: z.object({ path: z.string(), content: z.string() }),
        execute: mockExecutor(scenario, "write_file", rec),
      }),
    },
  });
  return summarize(result.steps, rec);
}
