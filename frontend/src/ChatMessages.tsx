import type { Ref } from "react";
import type { Chat } from "./api";

interface Props {
  chats: Chat[];
  pendingQuestion: string | null;
  lastChatRef: Ref<HTMLLIElement>;
  pendingRef: Ref<HTMLLIElement>;
}

export function ChatMessages({
  chats,
  pendingQuestion,
  lastChatRef,
  pendingRef,
}: Props) {
  return (
    <>
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
    </>
  );
}
