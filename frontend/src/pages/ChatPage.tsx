import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { authAPI } from "../api/client";
import { Composer } from "../chat/Composer";
import { Sidebar } from "../chat/Sidebar";
import { TurnList } from "../chat/TurnList";
import { Welcome } from "../chat/Welcome";
import { useChat } from "../chat/useChat";
import { useUser } from "../components/RequireAuth";

export function ChatPage() {
  const chat = useChat();
  const user = useUser();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const scroll = useRef<HTMLElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const last = chat.state.turns.at(-1);
  useEffect(() => {
    document.title = "배움 · Learning chat";
  }, []);
  useEffect(() => {
    if (scroll.current) scroll.current.scrollTop = scroll.current.scrollHeight;
  }, [chat.state.current, last?.id, last?.status]);
  function suggest(question: string) {
    chat.setQuestion(question);
    input.current?.focus();
  }
  async function logout() {
    try {
      await authAPI.logout();
      await navigate("/login", { replace: true });
    } catch (error) {
      chat.showError(error);
    }
  }
  return (
    <div className="chat-layout">
      <Sidebar
        state={chat.state}
        username={user.username}
        open={sidebarOpen}
        onCreate={() => {
          setSidebarOpen(false);
          void chat.create();
          input.current?.focus();
        }}
        onSelect={(id) => {
          setSidebarOpen(false);
          void chat.select(id);
        }}
        onMore={chat.more}
        onLogout={() => void logout()}
      />
      <main className="chat-main">
        <header className="chat-header">
          <button
            id="toggle-sidebar"
            className="subtle mobile-toggle"
            aria-controls="sidebar"
            aria-expanded={sidebarOpen}
            onClick={() => setSidebarOpen((open) => !open)}
          >
            ☰ 대화
          </button>
          <span id="chat-title">
            {chat.state.conversations.find(
              (item) => item.id === chat.state.current,
            )?.title ?? "새로운 배움"}
          </span>
          <span className="service-badge">학습 도우미</span>
        </header>
        <section
          id="message-scroll"
          ref={scroll}
          className="message-scroll"
          aria-label="대화 내용"
        >
          <button
            id="older-turns"
            className="subtle"
            hidden={!chat.state.beforeId}
            onClick={chat.older}
          >
            이전 메시지 보기
          </button>
          {chat.state.turns.length === 0 && <Welcome onSuggest={suggest} />}
          <TurnList
            turns={chat.state.turns}
            blocked={chat.blocked}
            onRetry={(id) => {
              chat.retry(id);
              input.current?.focus();
            }}
          />
        </section>
        <Composer
          question={chat.question}
          blocked={chat.blocked}
          busy={chat.state.busy}
          status={chat.state.status}
          showRefresh={chat.state.showRefresh}
          inputRef={input}
          onChange={chat.setQuestion}
          onSubmit={() => void chat.submit()}
          onRefresh={() => void chat.refresh()}
        />
      </main>
    </div>
  );
}
