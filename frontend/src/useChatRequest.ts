import { useEffect, useRef, useState } from "react";
import { APIError, api, type Chat } from "./api";

const MIN_PENDING_DISPLAY_MS = 3000;

interface Options {
  onSuccess: (chat: Chat) => void;
  onUnauthorized: () => void;
}

export function useChatRequest({ onSuccess, onUnauthorized }: Options) {
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const activeRequest = useRef<AbortController | null>(null);

  useEffect(() => () => activeRequest.current?.abort(), []);

  function cancel() {
    activeRequest.current?.abort();
  }

  async function send(question: string) {
    if (activeRequest.current) return;
    const controller = new AbortController();
    activeRequest.current = controller;
    const startedAt = performance.now();
    setPendingQuestion(question);
    setStatus("");

    try {
      const chat = await api.ask(question, controller.signal);
      const remaining =
        MIN_PENDING_DISPLAY_MS - (performance.now() - startedAt);
      if (remaining > 0) {
        await new Promise<void>((resolve) => setTimeout(resolve, remaining));
      }
      if (!controller.signal.aborted) onSuccess(chat);
    } catch (error) {
      if (controller.signal.aborted) return;
      if (error instanceof APIError && error.status === 401) {
        onUnauthorized();
      } else {
        setStatus(error instanceof Error ? error.message : String(error));
      }
    } finally {
      activeRequest.current = null;
      if (!controller.signal.aborted) setPendingQuestion(null);
    }
  }

  return { pendingQuestion, status, send, cancel };
}
