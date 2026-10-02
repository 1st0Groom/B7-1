import { useCallback, useEffect, useRef, useState } from "react";

interface Options {
  conversationId: number | null;
  revision: number;
  pending: boolean;
  paused: boolean;
  refresh: (id: number) => Promise<void>;
  onError: (error: unknown) => void;
  onTimeout: () => void;
}
export function usePendingPolling({
  conversationId,
  revision,
  pending,
  paused,
  refresh,
  onError,
  onTimeout,
}: Options) {
  const deadline = useRef(0);
  const [epoch, setEpoch] = useState(0);
  const restart = useCallback(() => {
    deadline.current = Date.now() + 120000;
    setEpoch((value) => value + 1);
  }, []);
  useEffect(() => {
    if (conversationId === null || !pending || paused) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    function schedule() {
      if (!active) return;
      if (Date.now() >= deadline.current) {
        onTimeout();
        return;
      }
      timer = setTimeout(async () => {
        try {
          await refresh(conversationId!);
          schedule();
        } catch (error) {
          if (active) onError(error);
        }
      }, 2000);
    }
    schedule();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [
    conversationId,
    revision,
    pending,
    paused,
    epoch,
    refresh,
    onError,
    onTimeout,
  ]);
  return restart;
}
