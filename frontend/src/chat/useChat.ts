import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { APIError, conversationsAPI, explain } from "../api/client";
import type { SendRequest } from "../api/types";
import {
  chatReducer,
  initialState,
  isBlocked,
  isPending,
  type Action,
  type ChatState,
} from "./state";

export function useChat() {
  const navigate = useNavigate();
  const [state, setState] = useState(initialState);
  const [question, setQuestion] = useState("");
  const [pollEpoch, setPollEpoch] = useState(0);
  const current = useRef(state);
  const mounted = useRef(false);
  const listRevision = useRef(0);
  const deadline = useRef(0);

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
      if (error instanceof APIError && error.status === 401)
        void navigate("/login", { replace: true });
      else patch({ status: explain(error) });
    },
    [navigate, patch],
  );
  const resetPolling = useCallback(() => {
    deadline.current = Date.now() + 120000;
    if (mounted.current) setPollEpoch((epoch) => epoch + 1);
  }, []);
  const loadConversations = useCallback(
    async (append = false) => {
      const revision = ++listRevision.current;
      const page = await conversationsAPI.list(
        append ? current.current.conversations.length : 0,
      );
      if (!mounted.current || revision !== listRevision.current) return;
      patch({
        conversations: append
          ? [...current.current.conversations, ...page.items]
          : page.items,
        hasMore: page.items.length === 100,
      });
    },
    [patch],
  );
  const refreshTurns = useCallback(
    async (id: number, older = false) => {
      const snapshot = current.current;
      const page = await conversationsAPI.history(
        id,
        older ? snapshot.beforeId : null,
      );
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
    [dispatch],
  );

  useEffect(() => {
    mounted.current = true;
    void loadConversations().catch(showError);
    return () => {
      mounted.current = false;
      listRevision.current++;
    };
  }, [loadConversations, showError]);

  // Each completed read schedules the next one; switching pages cancels the timer.
  useEffect(() => {
    const id = state.current;
    if (id === null || !isPending(state) || state.busy) return;
    if (Date.now() >= deadline.current) {
      patch({
        status: "아직 처리 상태를 확인 중입니다. 잠시 후 다시 확인해 주세요.",
        showRefresh: true,
      });
      return;
    }
    let active = true;
    const timer = setTimeout(() => {
      void refreshTurns(id).catch((error) => {
        if (active) {
          showError(error);
          patch({ showRefresh: true });
        }
      });
    }, 2000);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [
    state.current,
    state.revision,
    state.turns,
    state.busy,
    pollEpoch,
    refreshTurns,
    patch,
    showError,
  ]);

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
    const conversation = await conversationsAPI.create();
    await loadConversations();
    await select(conversation.id);
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
    try {
      const turn = await conversationsAPI.send(id, payload);
      dispatch({ type: "result", id, turn });
      if (mounted.current && current.current.current === id) {
        setQuestion((value) =>
          value.trim() === payload.question ? "" : value,
        );
        patch({ status: "" });
      }
    } catch (error) {
      if (
        !(error instanceof APIError) ||
        ["DB_UNAVAILABLE", "INTERNAL_ERROR"].includes(error.code ?? "")
      ) {
        dispatch({ type: "uncertain", id, payload });
        if (current.current.current === id)
          patch({
            status: "연결이 끊겨 처리 결과를 확인하고 있어요.",
            showRefresh: true,
          });
      } else if (current.current.current === id) showError(error);
    } finally {
      if (mounted.current) {
        resetPolling();
        if (current.current.current === id) {
          try {
            await refreshTurns(id);
          } catch (error) {
            showError(error);
            patch({ showRefresh: true });
          }
        }
        try {
          await loadConversations();
        } catch (error) {
          showError(error);
        }
      }
    }
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
    more: () => void loadConversations(true).catch(showError),
  };
}
