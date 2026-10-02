import type { RefObject } from "react";
interface Props {
  question: string;
  blocked: boolean;
  busy: boolean;
  status: string;
  showRefresh: boolean;
  inputRef: RefObject<HTMLTextAreaElement | null>;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onRefresh: () => void;
}
export function Composer({
  question,
  blocked,
  busy,
  status,
  showRefresh,
  inputRef,
  onChange,
  onSubmit,
  onRefresh,
}: Props) {
  const disabled = blocked || !question.trim();
  return (
    <div className="composer-area">
      <p className="status" role="status" aria-live="polite">
        {status}
      </p>
      <button
        id="refresh-chat"
        className="subtle"
        hidden={!showRefresh}
        disabled={busy}
        onClick={onRefresh}
      >
        처리 결과 다시 확인
      </button>
      <form
        className="composer"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <label className="sr-only" htmlFor="question">
          AI에게 질문하기
        </label>
        <textarea
          id="question"
          ref={inputRef}
          rows={2}
          maxLength={2000}
          placeholder="궁금한 것을 물어보세요"
          required
          value={question}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (
              event.key === "Enter" &&
              !event.shiftKey &&
              !event.nativeEvent.isComposing
            ) {
              event.preventDefault();
              if (!disabled) event.currentTarget.form?.requestSubmit();
            }
          }}
        />
        <div className="composer-footer">
          <span>{Array.from(question).length} / 2,000</span>
          <button className="primary" type="submit" disabled={disabled}>
            질문 보내기 ↑
          </button>
        </div>
      </form>
      <p className="disclaimer">
        AI의 답변은 틀릴 수 있어요. 중요한 내용은 다시 확인해 주세요.
      </p>
    </div>
  );
}
