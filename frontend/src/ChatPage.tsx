import { useEffect, useRef, useState, type FormEvent } from "react";
import { APIError, api, type Chat } from "./api";

const exampleQuestions = [
  "변수와 함수의 차이가 뭐야?",
  "API가 뭔지 쉽게 설명해줘",
  "Git과 GitHub는 뭐가 달라?",
];
const MIN_PENDING_DISPLAY_MS = 3000;

interface Props {
  chats: Chat[];
  onAsked: (chat: Chat) => void;
  onLogout: () => void;
}

export function ChatPage({ chats, onAsked, onLogout }: Props) {
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const pendingRef = useRef<HTMLLIElement>(null);
  const lastChatRef = useRef<HTMLLIElement>(null);
  const scrollTarget = useRef<"pending" | "complete" | null>(null);

  useEffect(() => {
    if (scrollTarget.current === "pending" && pendingQuestion !== null) {
      pendingRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
      scrollTarget.current = null;
    } else if (
      scrollTarget.current === "complete" &&
      pendingQuestion === null
    ) {
      lastChatRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
      scrollTarget.current = null;
    }
  }, [pendingQuestion, chats.length]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy || !question.trim()) return;
    const submittedQuestion = question;
    const pendingStartedAt = performance.now();
    scrollTarget.current = "pending";
    setPendingQuestion(submittedQuestion);
    setBusy(true);
    setStatus("");
    try {
      const chat = await api.ask(submittedQuestion);
      const remaining =
        MIN_PENDING_DISPLAY_MS - (performance.now() - pendingStartedAt);
      if (remaining > 0) {
        await new Promise<void>((resolve) => setTimeout(resolve, remaining));
      }
      const pendingRect = pendingRef.current?.getBoundingClientRect();
      scrollTarget.current =
        pendingRect &&
        pendingRect.bottom > 0 &&
        pendingRect.top < window.innerHeight
          ? "complete"
          : null;
      onAsked(chat);
      setQuestion("");
    } catch (e) {
      if (e instanceof APIError && e.status === 401) return onLogout();
      setStatus(e instanceof Error ? e.message : String(e));
    } finally {
      setPendingQuestion(null);
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
      {chats.length > 0 && (
        <section className="learning-history" aria-labelledby="history-heading">
          <h2 id="history-heading">
            <span aria-hidden="true">📚 </span>나의 학습 기록
          </h2>
          <p>이전에 공부한 내용을 다시 확인해보세요.</p>
          <ol>
            {chats.map((chat, index) => (
              <li
                key={chat.id}
                ref={index === chats.length - 1 ? lastChatRef : null}
              >
                <span className="message-label">나</span>
                <p>{chat.question}</p>
                <span className="message-label">AI 학습 도우미</span>
                <p className="answer">{chat.answer}</p>
                <time dateTime={chat.created_at}>
                  {new Date(chat.created_at).toLocaleString()}
                </time>
              </li>
            ))}
          </ol>
        </section>
      )}
      {pendingQuestion !== null && (
        <ol className="pending-conversation" aria-label="전송 중인 질문">
          <li ref={pendingRef}>
            <span className="message-label">나</span>
            <p>{pendingQuestion}</p>
            <span className="message-label">AI 학습 도우미</span>
            <p className="answer pending-answer" role="status">
              <span className="pending-spinner" aria-hidden="true" />
              답변을 만들고 있어요...
            </p>
          </li>
        </ol>
      )}
      {chats.length === 0 && pendingQuestion === null && (
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
          disabled={busy}
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
