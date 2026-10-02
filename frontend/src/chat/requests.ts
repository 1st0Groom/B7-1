import { APIError } from "../api/errors";
import type { SendRequest, Turn } from "../api/types";
import type { TurnSender } from "./ports";

export type SendOutcome =
  | { kind: "succeeded"; turn: Turn }
  | { kind: "uncertain" }
  | { kind: "rejected"; error: APIError };

// A transport failure does not prove that the server rejected a request.
export async function submitTurn(
  api: TurnSender,
  id: number,
  payload: SendRequest,
): Promise<SendOutcome> {
  try {
    return { kind: "succeeded", turn: await api.send(id, payload) };
  } catch (error) {
    if (
      !(error instanceof APIError) ||
      ["DB_UNAVAILABLE", "INTERNAL_ERROR"].includes(error.code ?? "")
    )
      return { kind: "uncertain" };
    return { kind: "rejected", error };
  }
}
