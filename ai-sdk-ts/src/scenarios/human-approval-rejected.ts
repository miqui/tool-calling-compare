import { type LanguageModel } from "ai";
import { loadScenario, type Outcome, type RunOptions } from "../scenario.ts";
import { runApproval } from "./approval-support.ts";

export const scenario = loadScenario("human-approval-rejected");

/** Human denies the transfer: tool must not execute and the model reports the denial. variant "approve" flips it. */
export async function run(model: LanguageModel, opts: RunOptions = {}): Promise<Outcome> {
  return runApproval(model, scenario, opts.variant === "approve", "transfer_funds");
}
