import { describe, expect, it } from "vitest";
import type { Turn, TurnPage } from "../api/types";
import { chatReducer, initialState, isBlocked } from "./state";

function turn(
  id: number,
  status: Turn["status"] = "succeeded",
  key = `request-${id}`,
): Turn {
  return {
    id,
    conversation_id: 1,
    status,
    client_request_id: key,
    question: `question ${id}`,
    answer: status === "succeeded" ? "answer" : null,
    error_code: null,
    created_at: "2026-10-02T00:00:00Z",
    completed_at: null,
  };
}
describe("conversation state", () => {
  it("ignores late history from a different conversation and a previous visit", () => {
    let state = chatReducer(initialState(), { type: "select", id: 1 });
    const revision = state.revision;
    const response = {
      type: "history" as const,
      id: 1,
      revision,
      page: { items: [turn(1)], next_before_id: null },
      older: false,
    };
    state = chatReducer(state, { type: "select", id: 2 });
    expect(chatReducer(state, response)).toBe(state);
    state = chatReducer(state, { type: "select", id: 1 });
    expect(chatReducer(state, response)).toBe(state);
    expect(
      chatReducer(state, { ...response, revision: state.revision }).turns,
    ).toEqual([turn(1)]);
  });
  it("merges overlapping history without losing older pages or downgrading completed turns", () => {
    let state = chatReducer(initialState(), { type: "select", id: 1 });
    const history = (items: Turn[], next: number | null, older = false) => {
      state = chatReducer(state, {
        type: "history",
        id: 1,
        revision: state.revision,
        page: { items, next_before_id: next },
        older,
      });
    };
    history([turn(3), turn(4, "pending")], 3);
    expect(isBlocked(state)).toBe(true);
    history([turn(1), turn(2), turn(3)], null, true);
    history([turn(3), turn(4)], 3);
    history([turn(4, "pending")], 4);
    expect(state.turns.map((item) => item.id)).toEqual([1, 2, 3, 4]);
    expect(state.beforeId).toBeNull();
    expect(isBlocked(state)).toBe(false);
  });
  it("requires the exact request ID to resolve an uncertain outcome", () => {
    let state = chatReducer(initialState(), { type: "select", id: 1 });
    state = chatReducer(state, {
      type: "uncertain",
      id: 1,
      payload: { question: "question", client_request_id: "lost" },
    });
    const history = (page: TurnPage) => {
      state = chatReducer(state, {
        type: "history",
        id: 1,
        revision: state.revision,
        page,
        older: false,
      });
    };
    history({ items: [turn(1)], next_before_id: null });
    expect(isBlocked(state)).toBe(true);
    history({ items: [turn(2, "pending", "lost")], next_before_id: null });
    expect(state.uncertain[1]).toBeUndefined();
    expect(isBlocked(state)).toBe(true);
    history({ items: [turn(2, "succeeded", "lost")], next_before_id: null });
    expect(isBlocked(state)).toBe(false);
  });
  it("keeps a late send result out of another conversation", () => {
    let state = chatReducer(initialState(), { type: "select", id: 2 });
    state = chatReducer(state, {
      type: "uncertain",
      id: 1,
      payload: { question: "question", client_request_id: "lost" },
    });
    state = chatReducer(state, { type: "result", id: 1, turn: turn(1) });
    expect(state.turns).toEqual([]);
    expect(state.uncertain[1]).toBeUndefined();
    state = chatReducer(state, {
      type: "result",
      id: 2,
      turn: turn(2, "pending"),
    });
    state = chatReducer(state, { type: "result", id: 2, turn: turn(2) });
    expect(state.turns).toHaveLength(1);
    expect(isBlocked(state)).toBe(false);
  });
});
