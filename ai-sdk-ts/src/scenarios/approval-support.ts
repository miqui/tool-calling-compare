import { generateText, stepCountIs, tool, type LanguageModel, type ModelMessage } from "ai";
import { z } from "zod";
import { Recorder, mockExecutor, summarize, type Outcome, type Scenario } from "../scenario.ts";

const toolInput = (name: string) =>
  name === "transfer_funds"
    ? z.object({ account: z.string(), amount: z.number() })
    : z.object({ path: z.string() });

/**
 * Two-call approval flow (AI SDK v6): generateText does not pause; with `needsApproval` it returns a
 * `tool-approval-request` content part. We append a `tool-approval-response` and call generateText again.
 */
export async function runApproval(
  model: LanguageModel,
  scenario: Scenario,
  approve: boolean,
  toolName: string,
): Promise<Outcome> {
  const rec = new Recorder();
  const tools = {
    [toolName]: tool({
      description: "Needs human approval before it runs.",
      inputSchema: toolInput(toolName),
      needsApproval: true,
      execute: mockExecutor(scenario, toolName, rec),
    }),
  };
  const messages: ModelMessage[] = [{ role: "user", content: scenario.prompt }];

  const first = await generateText({ model, tools, messages, stopWhen: stepCountIs(5) });
  messages.push(...first.response.messages);
  const requests = first.content.filter((p) => p.type === "tool-approval-request");
  messages.push({
    role: "tool",
    content: requests.map((r) => ({
      type: "tool-approval-response" as const,
      approvalId: r.approvalId,
      approved: approve,
      reason: approve ? "operator approved" : "operator denied",
    })),
  });

  // Approved -> tool executes; denied -> model sees an execution-denied tool result.
  const second = await generateText({ model, tools, messages, stopWhen: stepCountIs(5) });

  const out = summarize([...first.steps, ...second.steps], rec);
  return { ...out, text: second.text, stoppedBy: "final_answer", finishReason: second.finishReason };
}
