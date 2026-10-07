import { useEffect, useState } from "react";
import { api, type Chat } from "./api";
import { AuthPage } from "./AuthPage";
import { ChatPage } from "./ChatPage";

type LoadReason = "initial" | "signup" | "login";
const AUTH_LOADING_MIN_MS = 5000;

const loadingMessages: Record<LoadReason, string> = {
  initial: "로그인 상태를 확인하는 중...",
  signup: "학습 공간을 준비하는 중...",
  login: "채팅 기록을 불러오는 중...",
};
const loadingDescriptions: Record<Exclude<LoadReason, "initial">, string> = {
  signup: "첫 질문을 시작할 준비를 하고 있어요.",
  login: "이전에 공부한 내용을 불러오고 있어요.",
};

export function App() {
  const [chats, setChats] = useState<Chat[] | null>(null);
  const [checked, setChecked] = useState(false);
  const [loadingReason, setLoadingReason] = useState<LoadReason>("initial");

  async function load(reason: LoadReason) {
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

  if (!checked) {
    if (loadingReason === "initial") {
      return (
        <p className="initial-status" role="status">
          {loadingMessages.initial}
        </p>
      );
    }
    return (
      <main className="loading-page">
        <section className="loading-card" role="status">
          <span className="loading-spinner" aria-hidden="true" />
          <h1>{loadingMessages[loadingReason]}</h1>
          <p>{loadingDescriptions[loadingReason]}</p>
        </section>
      </main>
    );
  }
  if (!chats) return <AuthPage onLogin={load} />;
  return (
    <ChatPage
      chats={chats}
      onAsked={(chat) => setChats((list) => [...(list ?? []), chat])}
      onLogout={() => setChats(null)}
    />
  );
}
