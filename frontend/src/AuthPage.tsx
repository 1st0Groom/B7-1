import { useState, type FormEvent } from "react";
import { api } from "./api";

export function AuthPage({ onLogin }: { onLogin: () => Promise<void> }) {
  const [signup, setSignup] = useState(false);
  const [status, setStatus] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const credentials = {
      username: String(data.get("username")),
      password: String(data.get("password")),
    };
    try {
      if (signup) await api.signup(credentials);
      await api.login(credentials);
      await onLogin();
    } catch (e) {
      setStatus(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <main>
      <h1>개발 초보자를 위한 AI 학습 챗봇</h1>
      <p>어려운 개발 개념도 쉽게 질문하고, 차근차근 배워보세요.</p>
      <form onSubmit={submit}>
        <h2>{signup ? "회원가입" : "로그인"}</h2>
        <label htmlFor="username">아이디</label>
        <input id="username" name="username" autoComplete="username" required />
        <label htmlFor="password">비밀번호</label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete={signup ? "new-password" : "current-password"}
          required
        />
        <p role="status">{status}</p>
        <button type="submit">{signup ? "회원가입" : "로그인"}</button>
        <button type="button" onClick={() => setSignup(!signup)}>
          {signup ? "로그인으로" : "회원가입으로"}
        </button>
      </form>
    </main>
  );
}
