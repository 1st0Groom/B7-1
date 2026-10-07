import { useState, type FormEvent } from "react";
import { APIError, api, type Chat } from "./api";

interface Props {
  chats: Chat[];
  onAsked: (chat: Chat) => void;
  onLogout: () => void;
}

export function ChatPage({ chats, onAsked, onLogout }: Props) {
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setStatus("답변을 생성하고 있어요…");
    try {
      onAsked(await api.ask(question));
      setQuestion("");
      setStatus("");
    } catch (e) {
      if (e instanceof APIError && e.status === 401) return onLogout();
      setStatus(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    await api.logout().catch(() => {});
    onLogout();
  }

  return (
    <main>
      <header>
        <div>
          <h1>개발 초보자를 위한 AI 학습 챗봇</h1>
          <p>어려운 개발 개념도 쉽게 질문하고, 차근차근 배워보세요.</p>
        </div>
        <button onClick={() => void logout()}>로그아웃</button>
      </header>
      <ol>
        {chats.map((chat) => (
          <li key={chat.id}>
            <p>{chat.question}</p>
            <p className="answer">{chat.answer}</p>
            <time dateTime={chat.created_at}>
              {new Date(chat.created_at).toLocaleString()}
            </time>
          </li>
        ))}
      </ol>
      <form onSubmit={submit}>
        <label htmlFor="question">질문</label>
        <textarea
          id="question"
          maxLength={2000}
          required
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
        />
        <p role="status">{status}</p>
        <button type="submit" disabled={busy || !question.trim()}>
          질문 보내기
        </button>
      </form>
    </main>
  );
}
