import { Output, generateText, stepCountIs, tool, type LanguageModel } from "ai";
import { z } from "zod";
import { Recorder, loadScenario, mockExecutor, summarize, type Outcome } from "../scenario.ts";

export const scenario = loadScenario("structured-output-after-tools");

/** Tools run in earlier steps; `output: Output.object` parses/validates the final step into result.output. */
export async function run(model: LanguageModel): Promise<Outcome> {
  const rec = new Recorder();
  const result = await generateText({
    model,
    prompt: scenario.prompt,
    stopWhen: stepCountIs(5),
    output: Output.object({ schema: z.object({ city: z.string(), temp_c: z.number() }) }),
    tools: {
      get_weather: tool({
        description: "Get current weather for a city.",
        inputSchema: z.object({ city: z.string() }),
        execute: mockExecutor(scenario, "get_weather", rec),
      }),
    },
  });
  return summarize(result.steps, rec, { output: result.output });
}
