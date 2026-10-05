import { useEffect, useState } from "react";
import { api, type Chat } from "./api";
import { AuthPage } from "./AuthPage";
import { ChatPage } from "./ChatPage";

export function App() {
  const [chats, setChats] = useState<Chat[] | null>(null);
  const [checked, setChecked] = useState(false);

  async function load() {
    try {
      setChats(await api.chats());
    } catch {
      setChats(null);
    } finally {
      setChecked(true);
    }
  }
  useEffect(() => {
    void load();
  }, []);

  if (!checked) return null;
  if (!chats) return <AuthPage onLogin={load} />;
  return (
    <ChatPage
      chats={chats}
      onAsked={(chat) => setChats((list) => [...(list ?? []), chat])}
      onLogout={() => setChats(null)}
    />
  );
}
