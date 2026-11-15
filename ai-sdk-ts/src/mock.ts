import { MockLanguageModelV3, convertArrayToReadableStream } from "ai/test";
import type { ScriptTurn } from "./scenario.ts";

type GenerateResult = Awaited<ReturnType<MockLanguageModelV3["doGenerate"]>>;
type StreamPart = Awaited<ReturnType<MockLanguageModelV3["doStream"]>>["stream"] extends ReadableStream<infer P>
  ? P
  : never;

const usage = {
  inputTokens: { total: 10, noCache: 10, cacheRead: undefined, cacheWrite: undefined },
  outputTokens: { total: 5, text: 5, reasoning: undefined },
};

const finishReasonOf = (t: ScriptTurn) => {
  const unified = t.finish_reason === "tool_calls" ? "tool-calls" : t.finish_reason;
  return { unified, raw: t.finish_reason } as const;
};

function generateResult(turn: ScriptTurn, turnIndex: number): GenerateResult {
  const content: GenerateResult["content"] = [];
  if (turn.text !== undefined) content.push({ type: "text", text: turn.text });
  (turn.tool_calls ?? []).forEach((c, i) =>
    content.push({
      type: "tool-call",
      toolCallId: `call_${turnIndex}_${i}`,
      toolName: c.name,
      input: JSON.stringify(c.arguments),
    }),
  );
  return { content, finishReason: finishReasonOf(turn), usage, warnings: [] };
}

function streamParts(turn: ScriptTurn, turnIndex: number): StreamPart[] {
  const parts: StreamPart[] = [{ type: "stream-start", warnings: [] }];
  if (turn.text !== undefined) {
    parts.push({ type: "text-start", id: `t${turnIndex}` });
    parts.push({ type: "text-delta", id: `t${turnIndex}`, delta: turn.text });
    parts.push({ type: "text-end", id: `t${turnIndex}` });
  }
  (turn.tool_calls ?? []).forEach((c, i) =>
    parts.push({
      type: "tool-call",
      toolCallId: `call_${turnIndex}_${i}`,
      toolName: c.name,
      input: JSON.stringify(c.arguments),
    }),
  );
  parts.push({ type: "finish", finishReason: finishReasonOf(turn), usage });
  return parts;
}

/** A keyless model that replays `mock_llm_script` one turn per model call (generate or stream). */
export function scriptedModel(script: ScriptTurn[]): MockLanguageModelV3 {
  let i = 0;
  const next = () => {
    const turn = script[i];
    if (!turn) throw new Error(`mock_llm_script exhausted: model called ${i + 1} times, script has ${script.length}`);
    return [turn, i++] as const;
  };
  return new MockLanguageModelV3({
    doGenerate: async () => generateResult(...next()),
    doStream: async () => ({ stream: convertArrayToReadableStream(streamParts(...next())) }),
  });
}
