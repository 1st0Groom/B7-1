import { Link, Navigate, Route, Routes } from "react-router-dom";
import { RequireAuth } from "./components/RequireAuth";
import { AuthPage } from "./pages/AuthPage";
import { ChatPage } from "./pages/ChatPage";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/chat" replace />} />
      <Route path="/login" element={<AuthPage key="login" />} />
      <Route path="/signup" element={<AuthPage key="signup" signup />} />
      <Route element={<RequireAuth />}>
        <Route path="/chat" element={<ChatPage />} />
      </Route>
      <Route
        path="*"
        element={
          <main className="welcome">
            <h1>페이지를 찾을 수 없습니다.</h1>
            <Link to="/chat">대화로 돌아가기</Link>
          </main>
        }
      />
    </Routes>
  );
}
