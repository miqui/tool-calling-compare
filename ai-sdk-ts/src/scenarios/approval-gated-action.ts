import { type LanguageModel } from "ai";
import { loadScenario, type Outcome, type RunOptions, type ScriptTurn } from "../scenario.ts";
import { runApproval } from "./approval-support.ts";

export const scenario = loadScenario("approval-gated-action");

/** TS-side mock script (the legacy scenario JSON has none). */
export const script = (approve: boolean): ScriptTurn[] => [
  { finish_reason: "tool_calls", tool_calls: [{ name: "delete_file", arguments: { path: "old-report.txt" } }] },
  {
    finish_reason: "stop",
    text: approve ? "Deleted old-report.txt." : "The deletion was denied, so I did not delete it.",
  },
];

/** variant: "approve" (default) | "deny". delete_file's mock result is supplied here (legacy JSON has none). */
export async function run(model: LanguageModel, opts: RunOptions = {}): Promise<Outcome> {
  const withMock = { ...scenario, tools: [{ name: "delete_file", mock_result: { ok: true } }] };
  return runApproval(model, withMock, opts.variant !== "deny", "delete_file");
}
