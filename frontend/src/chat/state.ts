import type { Conversation, SendRequest, Turn, TurnPage } from "../api/types";

export interface ChatState {
  current: number | null;
  revision: number;
  conversations: Conversation[];
  hasMore: boolean;
  turns: Turn[];
  beforeId: number | null;
  busy: boolean;
  uncertain: Record<number, SendRequest>;
  status: string;
  showRefresh: boolean;
}
export function initialState(): ChatState {
  return {
    current: null,
    revision: 0,
    conversations: [],
    hasMore: false,
    turns: [],
    beforeId: null,
    busy: false,
    uncertain: {},
    status: "",
    showRefresh: false,
  };
}
export function isPending(state: ChatState) {
  return state.turns.some((turn) => turn.status === "pending");
}
export function isBlocked(state: ChatState) {
  return (
    state.busy ||
    isPending(state) ||
    (state.current !== null && !!state.uncertain[state.current])
  );
}
export type Action =
  | { type: "select"; id: number }
  | { type: "patch"; patch: Partial<ChatState> }
  | {
      type: "history";
      id: number;
      revision: number;
      page: TurnPage;
      older: boolean;
    }
  | { type: "result"; id: number; turn: Turn }
  | { type: "uncertain"; id: number; payload: SendRequest };

// Pure transitions keep pagination, stale responses and request recovery testable.
export function chatReducer(state: ChatState, action: Action): ChatState {
  switch (action.type) {
    case "patch":
      return { ...state, ...action.patch };
    case "select":
      return {
        ...state,
        current: action.id,
        revision: state.revision + 1,
        turns: [],
        beforeId: null,
        status: "",
        showRefresh: !!state.uncertain[action.id],
      };
    case "uncertain":
      return {
        ...state,
        uncertain: { ...state.uncertain, [action.id]: action.payload },
      };
    case "result": {
      const uncertain = { ...state.uncertain };
      delete uncertain[action.id];
      if (state.current !== action.id) return { ...state, uncertain };
      return {
        ...state,
        uncertain,
        turns: mergeTurns(state.turns, [action.turn]),
      };
    }
    case "history": {
      if (state.current !== action.id || state.revision !== action.revision)
        return state;
      const turns = mergeTurns(state.turns, action.page.items);
      const uncertain = { ...state.uncertain };
      const recovered = turns.some(
        (turn) =>
          turn.client_request_id === uncertain[action.id]?.client_request_id,
      );
      if (recovered) delete uncertain[action.id];
      return {
        ...state,
        turns,
        uncertain,
        beforeId:
          action.older || state.turns.length === 0
            ? action.page.next_before_id
            : state.beforeId,
        status: recovered ? "" : state.status,
        showRefresh: !!uncertain[action.id],
      };
    }
  }
}
function mergeTurns(existing: Turn[], incoming: Turn[]): Turn[] {
  const byId = new Map(existing.map((turn) => [turn.id, turn]));
  for (const turn of incoming) {
    // An older GET response must never change a completed turn back to pending.
    if (
      byId.get(turn.id)?.status !== "pending" &&
      byId.has(turn.id) &&
      turn.status === "pending"
    )
      continue;
    byId.set(turn.id, turn);
  }
  return [...byId.values()].sort((a, b) => a.id - b.id);
}
