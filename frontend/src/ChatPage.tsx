import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, type Chat } from "./api";
import { ChatMessages } from "./ChatMessages";
import { useChatRequest } from "./useChatRequest";

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
  const pendingRef = useRef<HTMLLIElement>(null);
  const lastChatRef = useRef<HTMLLIElement>(null);
  const scrollTarget = useRef<"pending" | "complete" | null>(null);
  const { pendingQuestion, status, send, cancel } = useChatRequest({
    onSuccess: handleAnswer,
    onUnauthorized: onLogout,
  });
  const busy = pendingQuestion !== null;

  useEffect(() => {
    const behavior = window.matchMedia("(prefers-reduced-motion: reduce)")
      .matches
      ? "auto"
      : "smooth";
    if (scrollTarget.current === "pending" && pendingQuestion !== null) {
      pendingRef.current?.scrollIntoView({ behavior, block: "end" });
      scrollTarget.current = null;
    } else if (
      scrollTarget.current === "complete" &&
      pendingQuestion === null
    ) {
      lastChatRef.current?.scrollIntoView({ behavior, block: "end" });
      scrollTarget.current = null;
    }
  }, [pendingQuestion, chats.length]);

  function handleAnswer(chat: Chat) {
    const pendingRect = pendingRef.current?.getBoundingClientRect();
    scrollTarget.current =
      pendingRect &&
      pendingRect.bottom > 0 &&
      pendingRect.top < window.innerHeight
        ? "complete"
        : null;
    onAsked(chat);
    setQuestion("");
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (busy || !question.trim()) return;
    scrollTarget.current = "pending";
    void send(question);
  }

  async function logout() {
    cancel();
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
      <ChatMessages
        chats={chats}
        pendingQuestion={pendingQuestion}
        lastChatRef={lastChatRef}
        pendingRef={pendingRef}
      />
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
