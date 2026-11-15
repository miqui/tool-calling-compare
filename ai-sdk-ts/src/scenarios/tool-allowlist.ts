import { generateText, stepCountIs, tool, type LanguageModel } from "ai";
import { z } from "zod";
import { Recorder, loadScenario, mockExecutor, summarize, type Outcome } from "../scenario.ts";

export const scenario = loadScenario("tool-allowlist");

/** Both tools are defined, but activeTools exposes only read_file to the model. */
export async function run(model: LanguageModel): Promise<Outcome> {
  const rec = new Recorder();
  const result = await generateText({
    model,
    prompt: scenario.prompt,
    stopWhen: stepCountIs(5),
    activeTools: ["read_file"],
    tools: {
      read_file: tool({
        description: "Read a file.",
        inputSchema: z.object({ path: z.string() }),
        execute: mockExecutor(scenario, "read_file", rec),
      }),
      delete_file: tool({
        description: "Delete a file.",
        inputSchema: z.object({ path: z.string() }),
        execute: mockExecutor(scenario, "delete_file", rec),
      }),
    },
  });
  return summarize(result.steps, rec);
}
