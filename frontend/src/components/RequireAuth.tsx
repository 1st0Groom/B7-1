import { useEffect, useState } from "react";
import { Navigate, Outlet, useOutletContext } from "react-router-dom";
import { APIError, authAPI, explain } from "../api/client";
import type { User } from "../api/types";

export function RequireAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    authAPI
      .me()
      .then((value) => {
        if (active) setUser(value);
      })
      .catch((error) => {
        if (active) setError(error);
      });
    return () => {
      active = false;
    };
  }, [attempt]);
  if (error instanceof APIError && error.status === 401)
    return <Navigate to="/login" replace />;
  if (error)
    return (
      <main className="welcome">
        <p role="alert">{explain(error)}</p>
        <button
          className="primary"
          onClick={() => {
            setError(null);
            setAttempt((value) => value + 1);
          }}
        >
          다시 확인
        </button>
      </main>
    );
  if (!user)
    return (
      <p className="welcome" role="status">
        로그인 상태를 확인하고 있어요…
      </p>
    );
  return <Outlet context={user} />;
}
export function useUser() {
  return useOutletContext<User>();
}
