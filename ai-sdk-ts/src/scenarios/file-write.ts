import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { generateText, stepCountIs, tool, type LanguageModel } from "ai";
import { z } from "zod";
import { Recorder, loadScenario, summarize, type Outcome, type RunOptions, type ScriptTurn } from "../scenario.ts";

export const scenario = loadScenario("file-write");

/** TS-side mock script (the legacy scenario JSON has none). */
export const script: ScriptTurn[] = [
  {
    finish_reason: "tool_calls",
    tool_calls: [{ name: "write_file", arguments: { path: "notes.txt", content: "hello world" } }],
  },
  { finish_reason: "stop", text: "Created notes.txt." },
];

/** write_file really writes, but only inside `opts.sandbox`. */
export async function run(model: LanguageModel, opts: RunOptions = {}): Promise<Outcome> {
  const sandbox = opts.sandbox ?? "./sandbox";
  mkdirSync(sandbox, { recursive: true });
  const rec = new Recorder();
  const result = await generateText({
    model,
    prompt: scenario.prompt,
    stopWhen: stepCountIs(3),
    tools: {
      write_file: tool({
        description: "Write text to a file inside the sandbox.",
        inputSchema: z.object({ path: z.string(), content: z.string() }),
        execute: async ({ path, content }) => {
          rec.executed.push({ name: "write_file", arguments: { path, content } });
          if (path.includes("..") || path.startsWith("/")) throw new Error("path escapes sandbox");
          writeFileSync(join(sandbox, path), content);
          return { ok: true };
        },
      }),
    },
  });
  return summarize(result.steps, rec);
}
