import { generateText, stepCountIs, tool, type LanguageModel } from "ai";
import { z } from "zod";
import { Recorder, loadScenario, mockExecutor, summarize, type Outcome, type ScriptTurn } from "../scenario.ts";

export const scenario = loadScenario("weather-lookup");

/** TS-side mock script (the legacy scenario JSON has none). */
export const script: ScriptTurn[] = [
  { finish_reason: "tool_calls", tool_calls: [{ name: "get_weather", arguments: { city: "Paris" } }] },
  { finish_reason: "stop", text: "It is 18C and cloudy in Paris." },
];

/** Single tool call, then a final answer (stopWhen allows the second step). */
export async function run(model: LanguageModel): Promise<Outcome> {
  const rec = new Recorder();
  const result = await generateText({
    model,
    prompt: scenario.prompt,
    stopWhen: stepCountIs(5),
    tools: {
      get_weather: tool({
        description: "Get current weather for a city.",
        inputSchema: z.object({ city: z.string() }),
        execute: mockExecutor(scenario, "get_weather", rec),
      }),
    },
  });
  return summarize(result.steps, rec);
}
