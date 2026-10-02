import { useCallback, useEffect, useRef, useState } from "react";
import { APIError, explain } from "../api/errors";
import type { SendRequest } from "../api/types";
import {
  chatReducer,
  initialState,
  isBlocked,
  isPending,
  type Action,
  type ChatState,
} from "./state";

import type { ChatGateway } from "./ports";
import { submitTurn } from "./requests";
import { useConversationList } from "./useConversationList";
import { usePendingPolling } from "./usePendingPolling";

export function useChat(api: ChatGateway, onUnauthorized: () => void) {
  const [state, setState] = useState(initialState);
  const [question, setQuestion] = useState("");
  const current = useRef(state);
  const mounted = useRef(false);

  // Async actions see the latest state immediately, including the busy lock.
  const dispatch = useCallback((action: Action) => {
    if (!mounted.current) return;
    current.current = chatReducer(current.current, action);
    setState(current.current);
  }, []);
  const patch = useCallback(
    (patch: Partial<ChatState>) => dispatch({ type: "patch", patch }),
    [dispatch],
  );
  const showError = useCallback(
    (error: unknown) => {
      if (!mounted.current) return;
      if (error instanceof APIError && error.status === 401) onUnauthorized();
      else patch({ status: explain(error) });
    },
    [onUnauthorized, patch],
  );
  const conversations = useConversationList(api, showError);
  const refreshTurns = useCallback(
    async (id: number, older = false) => {
      const snapshot = current.current;
      const page = await api.history(id, older ? snapshot.beforeId : null);
      if (
        !mounted.current ||
        current.current.current !== id ||
        current.current.revision !== snapshot.revision
      )
        return;
      const unresolved = current.current.uncertain[id];
      dispatch({
        type: "history",
        id,
        revision: snapshot.revision,
        page,
        older,
      });
      if (unresolved && !current.current.uncertain[id]) {
        setQuestion((value) =>
          value.trim() === unresolved.question ? "" : value,
        );
      }
    },
    [api, dispatch],
  );

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const pollError = useCallback(
    (error: unknown) => {
      showError(error);
      patch({ showRefresh: true });
    },
    [showError, patch],
  );
  const pollTimeout = useCallback(
    () =>
      patch({
        status: "아직 처리 상태를 확인 중입니다. 잠시 후 다시 확인해 주세요.",
        showRefresh: true,
      }),
    [patch],
  );
  const resetPolling = usePendingPolling({
    conversationId: state.current,
    revision: state.revision,
    pending: isPending(state),
    paused: state.busy,
    refresh: refreshTurns,
    onError: pollError,
    onTimeout: pollTimeout,
  });

  async function select(id: number) {
    resetPolling();
    dispatch({ type: "select", id });
    const revision = current.current.revision;
    try {
      await refreshTurns(id);
    } catch (error) {
      if (
        current.current.current === id &&
        current.current.revision === revision
      ) {
        showError(error);
        patch({ showRefresh: true });
      }
    }
  }
  async function create() {
    const conversation = await api.create();
    conversations.add(conversation);
    resetPolling();
    dispatch({ type: "select", id: conversation.id });
    return conversation.id;
  }
  async function withBusy(action: () => Promise<unknown>) {
    if (current.current.busy) return;
    patch({ busy: true });
    try {
      await action();
    } catch (error) {
      showError(error);
    } finally {
      patch({ busy: false });
    }
  }
  async function send(id: number, payload: SendRequest) {
    patch({ status: "답변을 생성하고 있어요…" });
    const outcome = await submitTurn(api, id, payload);
    if (!mounted.current) return;
    resetPolling();
    if (outcome.kind === "succeeded") {
      dispatch({ type: "result", id, turn: outcome.turn });
      if (current.current.current === id) {
        setQuestion((value) =>
          value.trim() === payload.question ? "" : value,
        );
        patch({ status: "" });
      }
    } else {
      if (outcome.kind === "uncertain") {
        dispatch({ type: "uncertain", id, payload });
        if (current.current.current === id)
          patch({
            status: "연결이 끊겨 처리 결과를 확인하고 있어요.",
            showRefresh: true,
          });
      } else if (outcome.error.status === 401) {
        showError(outcome.error);
        return;
      } else if (current.current.current === id) showError(outcome.error);
      // Failed requests can also have a persisted turn; fetch it for recovery/retry.
      if (current.current.current === id) {
        try {
          await refreshTurns(id);
        } catch (error) {
          if (
            (error instanceof APIError && error.status === 401) ||
            !current.current.status
          )
            showError(error);
          patch({ showRefresh: true });
        }
      }
    }
    const revision = current.current.revision;
    void conversations.load().catch((error: unknown) => {
      if (!mounted.current) return;
      if (error instanceof APIError && error.status === 401) showError(error);
      else if (current.current.revision === revision && !current.current.status)
        patch({
          status: `대화 목록을 새로 고치지 못했습니다. ${explain(error)}`,
        });
    });
  }
  function submit() {
    if (isBlocked(current.current) || !question.trim()) return;
    const payload = {
      question: question.trim(),
      client_request_id: crypto.randomUUID(),
    };
    return withBusy(async () =>
      send(current.current.current ?? (await create()), payload),
    );
  }
  function refresh() {
    const id = current.current.current;
    if (id === null) return;
    return withBusy(async () => {
      resetPolling();
      await refreshTurns(id);
      const unresolved = current.current.uncertain[id];
      // Read before resubmitting, and preserve the original idempotency key.
      if (current.current.current === id && unresolved)
        await send(id, unresolved);
    });
  }
  function retry(id: number) {
    const turn = current.current.turns.find((item) => item.id === id);
    if (isBlocked(current.current) || !turn) return;
    setQuestion(turn.question);
    patch({ status: "질문을 확인한 뒤 보내 주세요. 새 요청으로 처리됩니다." });
  }
  return {
    state,
    conversations: conversations.items,
    hasMore: conversations.hasMore,
    question,
    setQuestion,
    blocked: isBlocked(state),
    select,
    submit,
    refresh,
    retry,
    showError,
    create: () => withBusy(create),
    older: () => {
      if (state.current !== null)
        void refreshTurns(state.current, true).catch(showError);
    },
    more: () => void conversations.load(true).catch(showError),
  };
}
