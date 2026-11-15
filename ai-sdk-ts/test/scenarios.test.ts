import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import type { MockLanguageModelV3 } from "ai/test";
import { scriptedModel } from "../src/mock.ts";
import { scenarios } from "../src/scenarios/index.ts";
import * as approvalGated from "../src/scenarios/approval-gated-action.ts";
import * as fileWrite from "../src/scenarios/file-write.ts";
import * as loopStop from "../src/scenarios/loop-stop-conditions.ts";
import * as weather from "../src/scenarios/weather-lookup.ts";
import { loadScenario, type Call, type Outcome, type ScriptTurn } from "../src/scenario.ts";

const key = (c: Call) => JSON.stringify([c.name, c.arguments]);

/** Assert every `expect` assertion in the scenario JSON that the Outcome can answer. */
function assertExpect(expect: Record<string, unknown>, o: Outcome, model: MockLanguageModelV3) {
  const calls = (v: unknown) => v as Call[];
  if ("tool_calls" in expect) {
    const want = calls(expect.tool_calls).map(key);
    const got = o.toolCalls.map(key);
    if (expect.tool_calls_ordering === "unordered") assert.deepEqual([...got].sort(), [...want].sort());
    else assert.deepEqual(got, want);
  }
  if ("executed_tool_calls" in expect) assert.deepEqual(o.executed.map(key), calls(expect.executed_tool_calls).map(key));
  if ("steps" in expect) assert.equal(o.steps, expect.steps);
  if ("tool_call_count" in expect) assert.equal(o.toolCalls.length, expect.tool_call_count);
  if ("tool_errors" in expect) assert.equal(o.toolErrors, expect.tool_errors);
  if ("validation_errors" in expect) assert.equal(o.validationErrors, expect.validation_errors);
  if ("unknown_tool_errors" in expect) assert.equal(o.unknownToolErrors, expect.unknown_tool_errors);
  if ("stopped_by" in expect) assert.equal(o.stoppedBy, expect.stopped_by);
  for (const s of (expect.final_answer_contains as string[] | undefined) ?? []) assert.ok(o.text.includes(s), `text has ${s}`);
  if ("final_output" in expect) assert.deepEqual(o.output, expect.final_output);
  if ("event_order" in expect) assert.deepEqual(o.events, expect.event_order);
  if (expect.final_answer_mentions_denial) assert.match(o.text, /denied/i);
  if ("partial_tool_call_executed" in expect) assert.equal(o.executed.length > 0, expect.partial_tool_call_executed);
  if ("tools_exposed" in expect) {
    const exposed = (model.doGenerateCalls[0]?.tools ?? []).map((t) => t.name);
    assert.deepEqual(exposed, expect.tools_exposed);
  }
}

// Scenarios with a mock_llm_script and expect; driven generically.
const generic = Object.keys(scenarios).filter((id) => {
  const s = loadScenario(id);
  return s.mock_llm_script && s.expect && !["tool-choice-forced", "human-approval-rejected"].includes(id);
});

for (const id of generic) {
  test(`${id}: follows mock_llm_script and meets expect`, async () => {
    const s = loadScenario(id);
    assert.equal(scenarios[id]?.scenario.prompt, s.prompt);
    const model = scriptedModel(s.mock_llm_script as ScriptTurn[]);
    const outcome = await scenarios[id]!.run(model);
    assertExpect(s.expect!, outcome, model);
  });
}

test("tool-choice-none: model receives toolChoice none", async () => {
  const model = scriptedModel(loadScenario("tool-choice-none").mock_llm_script!);
  await scenarios["tool-choice-none"]!.run(model);
  assert.deepEqual(model.doGenerateCalls[0]?.toolChoice, { type: "none" });
});

test("max-output-tokens-truncation: maxOutputTokens forwarded, finishReason length", async () => {
  const model = scriptedModel(loadScenario("max-output-tokens-truncation").mock_llm_script!);
  const o = await scenarios["max-output-tokens-truncation"]!.run(model);
  assert.equal(model.doGenerateCalls[0]?.maxOutputTokens, 16);
  assert.equal(o.finishReason, "length");
});

test("invalid-args-recovery: invalid input never reaches execute", async () => {
  const model = scriptedModel(loadScenario("invalid-args-recovery").mock_llm_script!);
  const o = await scenarios["invalid-args-recovery"]!.run(model);
  assert.equal(o.executed.length, 1);
  assert.equal(o.executed[0]?.arguments.minutes, 5);
});

test("tool-choice-forced: base, required and forced-tool variants", async () => {
  const s = loadScenario("tool-choice-forced");
  const base = scriptedModel(s.mock_llm_script!);
  assertExpect(s.expect!, await scenarios["tool-choice-forced"]!.run(base), base);
  assert.deepEqual(base.doGenerateCalls[0]?.toolChoice, { type: "auto" });

  const req = scriptedModel(s.mock_llm_script!);
  const reqOut = await scenarios["tool-choice-forced"]!.run(req, { variant: "required" });
  assert.deepEqual(req.doGenerateCalls[0]?.toolChoice, { type: "required" });
  assert.deepEqual(req.doGenerateCalls[1]?.toolChoice, { type: "auto" }); // forced only on step 0
  assert.ok(reqOut.toolCalls.length > 0);

  const forced = scriptedModel(s.mock_llm_script!);
  const out = await scenarios["tool-choice-forced"]!.run(forced, { variant: "tool" });
  assert.deepEqual(forced.doGenerateCalls[0]?.toolChoice, { type: "tool", toolName: "log_greeting" });
  assert.equal(out.toolCalls[0]?.name, "log_greeting");
});

test("human-approval-rejected: denied tool is not executed, model reports denial", async () => {
  const s = loadScenario("human-approval-rejected");
  const model = scriptedModel(s.mock_llm_script!);
  const o = await scenarios["human-approval-rejected"]!.run(model);
  assertExpect(s.expect!, o, model);
  assert.equal(model.doGenerateCalls.length, 2);
});

test("human-approval-rejected: approve variant executes the tool", async () => {
  const model = scriptedModel(loadScenario("human-approval-rejected").mock_llm_script!);
  const o = await scenarios["human-approval-rejected"]!.run(model, { variant: "approve" });
  assert.equal(o.executed.length, 1);
});

for (const approve of [true, false]) {
  test(`approval-gated-action: ${approve ? "approve" : "deny"}`, async () => {
    const model = scriptedModel(approvalGated.script(approve));
    const o = await approvalGated.run(model, { variant: approve ? "approve" : "deny" });
    assert.equal(o.executed.length, approve ? 1 : 0);
    if (!approve) assert.match(o.text, /denied/i);
  });
}

test("weather-lookup: tool called, answer uses result", async () => {
  const o = await weather.run(scriptedModel(weather.script));
  assert.deepEqual(o.toolCalls, [{ name: "get_weather", arguments: { city: "Paris" } }]);
  assert.ok(o.text.includes("18"));
});

test("file-write: writes notes.txt in sandbox", async () => {
  const sandbox = mkdtempSync(join(tmpdir(), "aisdk-sandbox-"));
  const o = await fileWrite.run(scriptedModel(fileWrite.script), { sandbox });
  assert.equal(readFileSync(join(sandbox, "notes.txt"), "utf8"), "hello world");
  assert.equal(o.executed.length, 1);
});

test("loop-stop-conditions: stopWhen caps at 3 steps", async () => {
  const o = await loopStop.run(scriptedModel(loopStop.script));
  assert.equal(o.stoppedBy, "max_steps");
  assert.equal(o.toolCalls.length, 3);
  assert.deepEqual(
    o.executed.length,
    3,
  );
});

test("loop-stop-conditions: hasToolCall variant stops after first call", async () => {
  const o = await loopStop.run(scriptedModel(loopStop.script), { variant: "has-tool-call" });
  assert.equal(o.steps, 1);
});
