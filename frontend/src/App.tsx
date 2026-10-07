import { useEffect, useState } from "react";
import { api, type Chat } from "./api";
import { AuthPage } from "./AuthPage";
import { ChatPage } from "./ChatPage";
import { AuthLoading, type AuthLoadReason } from "./AuthLoading";

const AUTH_LOADING_MIN_MS = 5000;

export function App() {
  const [chats, setChats] = useState<Chat[] | null>(null);
  const [checked, setChecked] = useState(false);
  const [loadingReason, setLoadingReason] = useState<AuthLoadReason>("initial");

  async function load(reason: AuthLoadReason) {
    const startedAt = performance.now();
    setLoadingReason(reason);
    setChecked(false);
    try {
      setChats(await api.chats());
    } catch {
      setChats(null);
    } finally {
      if (reason !== "initial") {
        const remaining = AUTH_LOADING_MIN_MS - (performance.now() - startedAt);
        if (remaining > 0) {
          await new Promise<void>((resolve) => setTimeout(resolve, remaining));
        }
      }
      setChecked(true);
    }
  }
  useEffect(() => {
    void load("initial");
  }, []);

  if (!checked) return <AuthLoading reason={loadingReason} />;
  if (!chats) return <AuthPage onLogin={load} />;
  return (
    <ChatPage
      chats={chats}
      onAsked={(chat) => setChats((list) => [...(list ?? []), chat])}
      onLogout={() => setChats(null)}
    />
  );
}
