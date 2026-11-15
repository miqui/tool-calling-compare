import type { LanguageModel } from "ai";
import type { Outcome, RunOptions } from "../scenario.ts";
import * as weather_lookup from "./weather-lookup.ts";
import * as file_write from "./file-write.ts";
import * as approval_gated_action from "./approval-gated-action.ts";
import * as loop_stop_conditions from "./loop-stop-conditions.ts";
import * as parallel_tool_calls from "./parallel-tool-calls.ts";
import * as sequential_dependent_calls from "./sequential-dependent-calls.ts";
import * as tool_choice_forced from "./tool-choice-forced.ts";
import * as tool_choice_none from "./tool-choice-none.ts";
import * as invalid_args_recovery from "./invalid-args-recovery.ts";
import * as unknown_tool_name from "./unknown-tool-name.ts";
import * as tool_throws_error from "./tool-throws-error.ts";
import * as max_steps_exceeded from "./max-steps-exceeded.ts";
import * as max_output_tokens_truncation from "./max-output-tokens-truncation.ts";
import * as tool_allowlist from "./tool-allowlist.ts";
import * as structured_output_after_tools from "./structured-output-after-tools.ts";
import * as human_approval_rejected from "./human-approval-rejected.ts";
import * as stuck_loop_detection from "./stuck-loop-detection.ts";
import * as streaming_tool_events from "./streaming-tool-events.ts";

export interface ScenarioModule {
  scenario: { id: string; prompt: string };
  run: (model: LanguageModel, opts?: RunOptions) => Promise<Outcome>;
}

export const scenarios: Record<string, ScenarioModule> = {
  "weather-lookup": weather_lookup,
  "file-write": file_write,
  "approval-gated-action": approval_gated_action,
  "loop-stop-conditions": loop_stop_conditions,
  "parallel-tool-calls": parallel_tool_calls,
  "sequential-dependent-calls": sequential_dependent_calls,
  "tool-choice-forced": tool_choice_forced,
  "tool-choice-none": tool_choice_none,
  "invalid-args-recovery": invalid_args_recovery,
  "unknown-tool-name": unknown_tool_name,
  "tool-throws-error": tool_throws_error,
  "max-steps-exceeded": max_steps_exceeded,
  "max-output-tokens-truncation": max_output_tokens_truncation,
  "tool-allowlist": tool_allowlist,
  "structured-output-after-tools": structured_output_after_tools,
  "human-approval-rejected": human_approval_rejected,
  "stuck-loop-detection": stuck_loop_detection,
  "streaming-tool-events": streaming_tool_events,
};
