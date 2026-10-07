import { useState, type FormEvent } from "react";
import { APIError, api, type Chat } from "./api";

const exampleQuestions = [
  "변수와 함수의 차이가 뭐야?",
  "API가 뭔지 쉽게 설명해줘",
  "Git과 GitHub는 뭐가 달라?",
];

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
    <main className="chat-page">
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
      {chats.length === 0 && (
        <section
          className="example-questions"
          aria-labelledby="example-questions-heading"
        >
          <h2 id="example-questions-heading">무엇을 물어볼지 고민되나요?</h2>
          <p>아래 질문으로 시작해보세요.</p>
          <div className="example-questions-list">
            {exampleQuestions.map((example) => (
              <button
                key={example}
                type="button"
                disabled={busy}
                onClick={() => setQuestion(example)}
              >
                {example}
              </button>
            ))}
          </div>
        </section>
      )}
      <form onSubmit={submit}>
        <label htmlFor="question">질문</label>
        <textarea
          id="question"
          aria-describedby="question-count"
          maxLength={2000}
          required
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
        />
        <p id="question-count">{question.length} / 2000자</p>
        <p role="status">{status}</p>
        <button type="submit" disabled={busy || !question.trim()}>
          질문 보내기
        </button>
      </form>
    </main>
  );
}
