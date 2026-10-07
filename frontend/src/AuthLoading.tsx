export type AuthLoadReason = "initial" | "signup" | "login";

const messages: Record<AuthLoadReason, string> = {
  initial: "로그인 상태를 확인하는 중...",
  signup: "학습 공간을 준비하는 중...",
  login: "채팅 기록을 불러오는 중...",
};

const descriptions: Record<Exclude<AuthLoadReason, "initial">, string> = {
  signup: "첫 질문을 시작할 준비를 하고 있어요.",
  login: "이전에 공부한 내용을 불러오고 있어요.",
};

export function AuthLoading({ reason }: { reason: AuthLoadReason }) {
  if (reason === "initial") {
    return (
      <p className="initial-status" role="status">
        {messages.initial}
      </p>
    );
  }

  return (
    <main className="loading-page">
      <section className="loading-card" role="status">
        <span className="loading-spinner" aria-hidden="true" />
        <h1>{messages[reason]}</h1>
        <p>{descriptions[reason]}</p>
      </section>
    </main>
  );
}
