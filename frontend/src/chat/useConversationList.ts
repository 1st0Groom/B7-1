import { useCallback, useEffect, useRef, useState } from "react";
import type { Conversation } from "../api/types";
import type { ConversationCatalog } from "./ports";

export function useConversationList(
  api: Pick<ConversationCatalog, "list">,
  onError: (error: unknown) => void,
) {
  const [items, setItems] = useState<Conversation[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const itemsRef = useRef(items);
  const revision = useRef(0);
  const mounted = useRef(false);
  const load = useCallback(
    async (append = false) => {
      const visit = ++revision.current;
      const knownIds = new Set(itemsRef.current.map((item) => item.id));
      const page = await api
        .list(append ? itemsRef.current.length : 0)
        .catch((error: unknown) => {
          if (mounted.current && visit === revision.current) throw error;
        });
      if (!page || !mounted.current || visit !== revision.current) return;
      // Keep conversations created locally after this list request started.
      const combined = append
        ? [...itemsRef.current, ...page.items]
        : [
            ...itemsRef.current.filter((item) => !knownIds.has(item.id)),
            ...page.items,
          ];
      itemsRef.current = [
        ...new Map(combined.map((item) => [item.id, item])).values(),
      ];
      setItems(itemsRef.current);
      setHasMore(page.items.length === page.limit);
    },
    [api],
  );
  useEffect(() => {
    mounted.current = true;
    void load().catch((error) => {
      if (mounted.current) onError(error);
    });
    return () => {
      mounted.current = false;
      revision.current++;
    };
  }, [load, onError]);
  const add = useCallback((conversation: Conversation) => {
    if (!mounted.current) return;
    itemsRef.current = [
      conversation,
      ...itemsRef.current.filter((item) => item.id !== conversation.id),
    ];
    setItems(itemsRef.current);
  }, []);
  return { items, hasMore, load, add };
}
