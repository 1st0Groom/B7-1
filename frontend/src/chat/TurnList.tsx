import type { Turn } from "../api/types";
const failureMessages: Record<string, string> = {
  AI_TIMEOUT: "응답 시간이 초과되었습니다. 다시 시도할 수 있어요.",
  AI_UNAVAILABLE: "AI 응답을 받지 못했습니다. 잠시 후 다시 시도해 주세요.",
  REQUEST_INTERRUPTED: "요청 처리가 중단되었습니다. 다시 시도해 주세요.",
  CONTEXT_TOO_LARGE: "질문이 너무 큽니다. 내용을 줄여 새로 보내 주세요.",
  DB_UNAVAILABLE: "대화를 저장하지 못했습니다. 다시 시도해 주세요.",
  INTERNAL_ERROR: "처리 중 오류가 발생했습니다. 다시 시도해 주세요.",
};
export function TurnList({
  turns,
  blocked,
  onRetry,
}: {
  turns: Turn[];
  blocked: boolean;
  onRetry: (id: number) => void;
}) {
  return (
    <div id="turns">
      {turns.map((turn) => (
        <article className="turn" key={turn.id}>
          <div className="message question">{turn.question}</div>
          <div className="answer-label">✳ 배움</div>
          {turn.status === "succeeded" ? (
            <div className="message answer">{turn.answer}</div>
          ) : turn.status === "pending" ? (
            <div className="pending">답변을 생성하고 있어요…</div>
          ) : (
            <div className="failure">
              {failureMessages[turn.error_code ?? ""] ?? "요청에 실패했습니다."}
              <br />
              <button
                className="subtle"
                disabled={blocked}
                onClick={() => onRetry(turn.id)}
              >
                다시 시도
              </button>
            </div>
          )}
          <time dateTime={turn.created_at}>
            {new Date(turn.created_at).toLocaleString()}
          </time>
        </article>
      ))}
    </div>
  );
}
