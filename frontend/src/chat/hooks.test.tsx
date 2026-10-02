// @vitest-environment jsdom
import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { APIError } from "../api/errors";
import type { ConversationPage, TurnPage } from "../api/types";
import type { ChatGateway } from "./ports";
import { useChat } from "./useChat";
import { useConversationList } from "./useConversationList";
import { usePendingPolling } from "./usePendingPolling";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, resolve, reject };
}
afterEach(() => {
  cleanup();
  vi.useRealTimers();
});
const page = (id: number): ConversationPage => ({
  items: [{ id, title: String(id), created_at: "", updated_at: "" }],
  offset: 0,
  limit: 100,
});

it("ignores an old list response after refreshing and ignores completion after unmount", async () => {
  const old = deferred<ConversationPage>();
  const newer = deferred<ConversationPage>();
  const last = deferred<ConversationPage>();
  const api = {
    list: vi
      .fn()
      .mockReturnValueOnce(old.promise)
      .mockReturnValueOnce(newer.promise)
      .mockReturnValueOnce(last.promise),
  };
  const onError = vi.fn();
  const { result, unmount } = renderHook(() =>
    useConversationList(api, onError),
  );
  let refreshing: Promise<void>;
  act(() => {
    refreshing = result.current.load();
  });
  await act(async () => {
    newer.resolve(page(2));
    await refreshing;
  });
  await act(async () => {
    old.resolve(page(1));
    await old.promise;
  });
  expect(result.current.items.map((item) => item.id)).toEqual([2]);
  act(() => {
    refreshing = result.current.load();
  });
  unmount();
  await act(async () => {
    last.resolve(page(3));
    await refreshing;
  });
  expect(result.current.items.map((item) => item.id)).toEqual([2]);
  expect(onError).not.toHaveBeenCalled();
});

it("stops polling on unmount even when an in-flight read completes later", async () => {
  vi.useFakeTimers();
  const pending = deferred<void>();
  const refresh = vi.fn().mockReturnValue(pending.promise);
  const onError = vi.fn();
  const onTimeout = vi.fn();
  const { result, unmount } = renderHook(() =>
    usePendingPolling({
      conversationId: 1,
      revision: 1,
      pending: true,
      paused: false,
      refresh,
      onError,
      onTimeout,
    }),
  );
  act(() => result.current());
  await act(() => vi.advanceTimersByTimeAsync(2000));
  expect(refresh).toHaveBeenCalledTimes(1);
  unmount();
  await act(async () => {
    pending.resolve();
    await pending.promise;
  });
  await vi.advanceTimersByTimeAsync(10000);
  expect(refresh).toHaveBeenCalledTimes(1);
  expect(vi.getTimerCount()).toBe(0);
});

it("polls the selected conversation and stops after the time budget", async () => {
  vi.useFakeTimers();
  const refresh = vi.fn().mockResolvedValue(undefined);
  const onTimeout = vi.fn();
  const onError = vi.fn();
  const { result, rerender } = renderHook(
    ({ id }) =>
      usePendingPolling({
        conversationId: id,
        revision: id,
        pending: true,
        paused: false,
        refresh,
        onTimeout,
        onError,
      }),
    { initialProps: { id: 1 } },
  );
  act(() => result.current());
  rerender({ id: 2 });
  await act(() => vi.advanceTimersByTimeAsync(2000));
  expect(refresh).toHaveBeenCalledWith(2);
  expect(refresh).not.toHaveBeenCalledWith(1);
  onTimeout.mockClear();
  await act(() => vi.advanceTimersByTimeAsync(120000));
  expect(onTimeout).toHaveBeenCalledTimes(1);
  expect(vi.getTimerCount()).toBe(0);
});

it("recovers an uncertain send through an injected gateway with the original UUID", async () => {
  const history: TurnPage = { items: [], next_before_id: null };
  const api: ChatGateway = {
    list: vi.fn().mockResolvedValue(page(1)),
    create: vi.fn().mockResolvedValue(page(1).items[0]),
    history: vi.fn().mockImplementation(async () => history),
    send: vi
      .fn()
      .mockRejectedValueOnce(new TypeError("offline"))
      .mockImplementation(async (_id, payload) => {
        const turn = {
          ...payload,
          id: 1,
          conversation_id: 1,
          status: "succeeded" as const,
          answer: "answer",
          error_code: null,
          created_at: "",
          completed_at: null,
        };
        history.items = [turn];
        return turn;
      }),
  };
  const onUnauthorized = vi.fn();
  const { result } = renderHook(() => useChat(api, onUnauthorized));
  await act(async () => {
    await result.current.select(1);
  });
  act(() => result.current.setQuestion("question"));
  await act(async () => {
    await result.current.submit();
  });
  expect(result.current.blocked).toBe(true);
  const original = vi.mocked(api.send).mock.calls[0][1];
  await act(async () => {
    await result.current.refresh();
  });
  expect(vi.mocked(api.send).mock.calls[1][1]).toEqual(original);
  expect(result.current.state.turns).toHaveLength(1);
  expect(result.current.blocked).toBe(false);
  expect(result.current.question).toBe("");
});

function successfulGateway(): ChatGateway {
  return {
    list: vi.fn().mockResolvedValue(page(1)),
    create: vi.fn().mockResolvedValue(page(1).items[0]),
    history: vi.fn().mockResolvedValue({ items: [], next_before_id: null }),
    send: vi.fn().mockImplementation(async (id, payload) => ({
      ...payload,
      id: 1,
      conversation_id: id,
      status: "succeeded",
      answer: "answer",
      error_code: null,
      created_at: "",
      completed_at: null,
    })),
  };
}

it("sends the first question without waiting for a list read or fetching empty history", async () => {
  const api = successfulGateway();
  const initialList = deferred<ConversationPage>();
  vi.mocked(api.list).mockReturnValueOnce(initialList.promise);
  const onUnauthorized = vi.fn();
  const { result } = renderHook(() => useChat(api, onUnauthorized));
  act(() => result.current.setQuestion("first question"));
  await act(async () => {
    await result.current.submit();
  });
  expect(api.create).toHaveBeenCalledTimes(1);
  expect(api.send).toHaveBeenCalledTimes(1);
  expect(api.history).not.toHaveBeenCalled();
  // Initial page load plus one refresh for the server-generated conversation title.
  expect(api.list).toHaveBeenCalledTimes(2);
  expect(result.current.state.turns[0].answer).toBe("answer");
  expect(result.current.question).toBe("");
  expect(result.current.blocked).toBe(false);
  await act(async () => {
    initialList.resolve(page(2));
    await initialList.promise;
  });
  expect(result.current.conversations.map((item) => item.id)).toEqual([1]);
});

it("keeps a newly created conversation when an older list snapshot arrives", async () => {
  const initialList = deferred<ConversationPage>();
  const api = successfulGateway();
  vi.mocked(api.list).mockReturnValueOnce(initialList.promise);
  const onUnauthorized = vi.fn();
  const { result } = renderHook(() => useChat(api, onUnauthorized));
  await act(async () => {
    await result.current.create();
  });
  expect(result.current.conversations.map((item) => item.id)).toEqual([1]);
  expect(api.list).toHaveBeenCalledTimes(1);
  expect(api.history).not.toHaveBeenCalled();
  await act(async () => {
    initialList.resolve(page(2));
    await initialList.promise;
  });
  expect(result.current.conversations.map((item) => item.id)).toEqual([1, 2]);
});

it("keeps a confirmed answer when refreshing the conversation list fails", async () => {
  const api = successfulGateway();
  vi.mocked(api.list)
    .mockResolvedValueOnce(page(1))
    .mockRejectedValue(new TypeError("offline"));
  const onUnauthorized = vi.fn();
  const { result } = renderHook(() => useChat(api, onUnauthorized));
  act(() => result.current.setQuestion("question"));
  await act(async () => {
    await result.current.submit();
  });
  expect(result.current.state.turns[0].status).toBe("succeeded");
  expect(result.current.state.status).toContain(
    "대화 목록을 새로 고치지 못했습니다.",
  );
  expect(result.current.state.showRefresh).toBe(false);
  expect(result.current.blocked).toBe(false);
  expect(api.history).not.toHaveBeenCalled();
});

it("preserves the send error when history and list recovery also fail", async () => {
  const api = successfulGateway();
  vi.mocked(api.list)
    .mockResolvedValueOnce(page(1))
    .mockRejectedValue(new TypeError("offline"));
  vi.mocked(api.history).mockRejectedValue(new TypeError("offline"));
  vi.mocked(api.send).mockRejectedValue(
    new APIError(
      { error: { code: "AI_TIMEOUT", message: "답변 시간 초과" } },
      504,
    ),
  );
  const onUnauthorized = vi.fn();
  const { result } = renderHook(() => useChat(api, onUnauthorized));
  act(() => result.current.setQuestion("question"));
  await act(async () => {
    await result.current.submit();
  });
  expect(result.current.state.status).toBe("답변 시간 초과");
  expect(result.current.state.showRefresh).toBe(true);
  expect(api.history).toHaveBeenCalledTimes(1);
});

it("allows another send while the previous conversation list refresh is pending", async () => {
  const api = successfulGateway();
  const slowList = deferred<ConversationPage>();
  vi.mocked(api.list)
    .mockResolvedValueOnce(page(1))
    .mockReturnValueOnce(slowList.promise)
    .mockResolvedValue(page(1));
  const onUnauthorized = vi.fn();
  const { result } = renderHook(() => useChat(api, onUnauthorized));
  act(() => result.current.setQuestion("first"));
  await act(async () => {
    await result.current.submit();
  });
  expect(result.current.blocked).toBe(false);
  expect(result.current.state.turns[0].answer).toBe("answer");
  act(() => result.current.setQuestion("second"));
  await act(async () => {
    await result.current.submit();
  });
  expect(api.send).toHaveBeenCalledTimes(2);
  expect(vi.mocked(api.send).mock.calls[1][1].question).toBe("second");
  await act(async () => {
    slowList.reject(new TypeError("old list failed"));
    await slowList.promise.catch(() => {});
  });
  expect(result.current.state.status).toBe("");
});

it("does not report a background list failure after unmount", async () => {
  const api = successfulGateway();
  const slowList = deferred<ConversationPage>();
  vi.mocked(api.list)
    .mockResolvedValueOnce(page(1))
    .mockReturnValueOnce(slowList.promise);
  const onUnauthorized = vi.fn();
  const { result, unmount } = renderHook(() => useChat(api, onUnauthorized));
  act(() => result.current.setQuestion("question"));
  await act(async () => {
    await result.current.submit();
  });
  unmount();
  await act(async () => {
    slowList.reject(new APIError({}, 401));
    await slowList.promise.catch(() => {});
  });
  expect(onUnauthorized).not.toHaveBeenCalled();
});

it("uses the returned page size when deciding whether more conversations exist", async () => {
  const api = { list: vi.fn().mockResolvedValue({ ...page(1), limit: 1 }) };
  const onError = vi.fn();
  const { result } = renderHook(() => useConversationList(api, onError));
  await act(async () => {});
  expect(result.current.hasMore).toBe(true);
  api.list.mockResolvedValue({ items: [], offset: 1, limit: 1 });
  await act(async () => {
    await result.current.load(true);
  });
  expect(api.list).toHaveBeenLastCalledWith(1);
  expect(result.current.hasMore).toBe(false);
});
