import { stepCountIs, streamText, tool, type LanguageModel } from "ai";
import { z } from "zod";
import { Recorder, loadScenario, mockExecutor, summarize, type Outcome } from "../scenario.ts";

export const scenario = loadScenario("streaming-tool-events");

const INTERESTING = new Set(["tool-call", "tool-result", "text-delta", "finish"]);

/** Consume fullStream and record the ordered event types (consecutive duplicates collapsed). */
export async function run(model: LanguageModel): Promise<Outcome> {
  const rec = new Recorder();
  const result = streamText({
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
  const events: string[] = [];
  for await (const part of result.fullStream) {
    if (INTERESTING.has(part.type) && events[events.length - 1] !== part.type) events.push(part.type);
  }
  return summarize(await result.steps, rec, { events });
}
