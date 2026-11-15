import { readFileSync } from "node:fs";
import { InvalidToolInputError, NoSuchToolError, type StepResult } from "ai";

export interface Call {
  name: string;
  arguments: Record<string, unknown>;
}

export interface ScriptTurn {
  finish_reason: "stop" | "tool_calls" | "length";
  text?: string;
  tool_calls?: Call[];
}

export interface ToolSpec {
  name: string;
  mock_result?: unknown;
  mock_result_by_args?: Record<string, unknown>;
  mock_result_sequence?: unknown[];
  mock_error?: { message: string };
  requires_approval?: boolean;
}

export interface Scenario {
  id: string;
  prompt: string;
  tools: ToolSpec[];
  stop_condition?: string;
  limits?: { max_steps?: number; max_output_tokens?: number; repeat_threshold?: number };
  mock_llm_script?: ScriptTurn[];
  expect?: Record<string, unknown>;
  [k: string]: unknown;
}

export function loadScenario(id: string): Scenario {
  const url = new URL(`../../scenarios/${id}.json`, import.meta.url);
  return JSON.parse(readFileSync(url, "utf8")) as Scenario;
}

/** Normalised result of one scenario run, comparable with `expect` in the scenario JSON. */
export interface Outcome {
  /** Every tool call the model emitted (including invalid / unknown ones). */
  toolCalls: Call[];
  /** Tool calls whose `execute` actually ran. */
  executed: Call[];
  steps: number;
  finishReason: string;
  text: string;
  toolErrors: number;
  validationErrors: number;
  unknownToolErrors: number;
  stoppedBy: "final_answer" | "max_steps" | "length" | "stuck_detected";
  output?: unknown;
  events?: string[];
}

export interface RunOptions {
  variant?: string;
  /** Directory used by file-write. */
  sandbox?: string;
}

export class Recorder {
  executed: Call[] = [];
}

/** Build an `execute` function that records calls and replays the scenario's mock result/error. */
export function mockExecutor(scenario: Scenario, name: string, rec: Recorder) {
  const spec = scenario.tools.find((t) => t.name === name);
  if (!spec) throw new Error(`scenario ${scenario.id} has no tool ${name}`);
  let n = 0;
  return async (args: Record<string, unknown>): Promise<unknown> => {
    rec.executed.push({ name, arguments: args });
    if (spec.mock_error) throw new Error(spec.mock_error.message);
    if (spec.mock_result_sequence) {
      return spec.mock_result_sequence[Math.min(n++, spec.mock_result_sequence.length - 1)];
    }
    if (spec.mock_result_by_args) {
      return spec.mock_result_by_args[String(Object.values(args)[0])];
    }
    return spec.mock_result;
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- accept steps from any concrete tool set
export type AnySteps = ReadonlyArray<StepResult<any>>;

export function summarize(
  steps: AnySteps,
  rec: Recorder,
  extra: Partial<Outcome> = {},
): Outcome {
  const parts = steps.flatMap((s) => s.content);
  const toolCalls: Call[] = [];
  let toolErrors = 0;
  let validationErrors = 0;
  let unknownToolErrors = 0;
  const invalidIds = new Set<string>();
  for (const p of parts) {
    if (p.type === "tool-call") {
      toolCalls.push({ name: p.toolName, arguments: p.input as Record<string, unknown> });
      // Invalid calls (bad input / unknown tool) are flagged `invalid` and carry the typed error;
      // the matching tool-error part only has the message string.
      if (p.invalid) {
        invalidIds.add(p.toolCallId);
        if (InvalidToolInputError.isInstance(p.error)) validationErrors++;
        else if (NoSuchToolError.isInstance(p.error)) unknownToolErrors++;
      }
    } else if (p.type === "tool-error" && !invalidIds.has(p.toolCallId)) {
      toolErrors++;
    }
  }
  const last = steps[steps.length - 1];
  const finishReason = last?.finishReason ?? "other";
  return {
    toolCalls,
    executed: rec.executed,
    steps: steps.length,
    finishReason,
    text: last?.text ?? "",
    toolErrors,
    validationErrors,
    unknownToolErrors,
    stoppedBy:
      finishReason === "length" ? "length" : finishReason === "tool-calls" ? "max_steps" : "final_answer",
    ...extra,
  };
}
