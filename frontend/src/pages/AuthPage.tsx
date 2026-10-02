import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { authAPI, explain } from "../api/client";
import { Brand } from "../components/Brand";

export function AuthPage({ signup = false }: { signup?: boolean }) {
  const navigate = useNavigate();
  const [search] = useSearchParams();
  const [status, setStatus] = useState(
    search.has("registered") ? "가입이 완료되었습니다. 로그인해 주세요." : "",
  );
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    document.title = `${signup ? "회원가입" : "로그인"} · 배움`;
  }, [signup]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const data = new FormData(event.currentTarget);
    const credentials = {
      username: String(data.get("username")),
      password: String(data.get("password")),
    };
    setBusy(true);
    setStatus("처리 중입니다…");
    try {
      await (signup ? authAPI.signup(credentials) : authAPI.login(credentials));
      await navigate(signup ? "/login?registered=1" : "/chat", {
        replace: true,
      });
    } catch (error) {
      setStatus(explain(error));
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="auth-layout">
      <section className="intro">
        <Brand />
        <div>
          <p className="eyebrow">질문에서 시작하는 이해</p>
          <h1>
            궁금한 순간을,
            <br />
            배움의 순간으로.
          </h1>
          <p className="intro-copy">
            낯선 개념부터 작은 궁금증까지.
            <br />
            질문을 이어가고, 나만의 배움을 차곡차곡 쌓아보세요.
          </p>
          <div className="sample">
            <span>이렇게 시작해 보세요</span>
            <p>“FastAPI의 라우터를 쉬운 예시로 설명해 줘.”</p>
          </div>
        </div>
        <small>
          AI의 답변은 틀릴 수 있어요. 중요한 내용은 다시 확인해 주세요.
        </small>
      </section>
      <section className="auth-panel">
        <form id="auth-form" onSubmit={submit}>
          <p className="eyebrow">
            {signup ? "처음 오셨나요?" : "다시 만나 반가워요"}
          </p>
          <h2>{signup ? "배움을 시작하세요" : "이어서 배워볼까요?"}</h2>
          <p className="muted">
            {signup
              ? "아이디와 비밀번호로 계정을 만들어 주세요."
              : "로그인하고 이전 대화부터 이어가세요."}
          </p>
          <label htmlFor="username">아이디</label>
          <input
            id="username"
            name="username"
            type="text"
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            minLength={3}
            maxLength={32}
            pattern="[A-Za-z0-9_]+"
            placeholder="your_id"
            required
            aria-describedby="username-hint"
          />
          <small id="username-hint">
            영문·숫자·밑줄(_)로 3~32자, 대소문자를 구분하지 않습니다.
          </small>
          <label htmlFor="password">비밀번호</label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete={signup ? "new-password" : "current-password"}
            minLength={10}
            maxLength={128}
            required
            aria-describedby="password-hint"
          />
          <small id="password-hint">
            10~128자. 영문·숫자·특수문자 조합 조건은 없습니다.
          </small>
          <p
            id="auth-status"
            className="status"
            role="status"
            aria-live="polite"
          >
            {status}
          </p>
          <button className="primary" type="submit" disabled={busy}>
            {signup ? "회원가입" : "로그인"} <span aria-hidden="true">→</span>
          </button>
          <p className="auth-switch">
            {signup ? "이미 계정이 있나요?" : "아직 계정이 없나요?"}{" "}
            <Link to={signup ? "/login" : "/signup"}>
              {signup ? "로그인" : "회원가입"}
            </Link>
          </p>
        </form>
      </section>
    </main>
  );
}
