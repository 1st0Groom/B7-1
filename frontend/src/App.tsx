import { useEffect, useState } from "react";
import { APIError, api, type Chat } from "./api";
import { AuthPage } from "./AuthPage";
import { ChatPage } from "./ChatPage";

export function App() {
  const [chats, setChats] = useState<Chat[] | null>(null);
  const [checked, setChecked] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    try {
      setChats(await api.chats());
    } catch (e) {
      setChats(null);
      if (!(e instanceof APIError && e.status === 401))
        setError(e instanceof Error ? e.message : String(e));
    } finally {
      setChecked(true);
    }
  }
  useEffect(() => {
    void load();
  }, []);

  if (!checked) return null;
  if (!chats) return <AuthPage error={error} onLogin={load} />;
  return (
    <ChatPage
      chats={chats}
      onAsked={(chat) => setChats((list) => [...(list ?? []), chat])}
      onLogout={() => setChats(null)}
    />
  );
}
