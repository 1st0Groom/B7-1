import { Brand } from "../components/Brand";
import type { Conversation } from "../api/types";

interface Props {
  conversations: Conversation[];
  currentId: number | null;
  busy: boolean;
  hasMore: boolean;
  username: string;
  open: boolean;
  onCreate: () => void;
  onSelect: (id: number) => void;
  onMore: () => void;
  onLogout: () => void;
}
export function Sidebar({
  conversations,
  currentId,
  busy,
  hasMore,
  username,
  open,
  onCreate,
  onSelect,
  onMore,
  onLogout,
}: Props) {
  return (
    <aside id="sidebar" className={`sidebar${open ? " open" : ""}`}>
      <Brand />
      <button className="new-chat" disabled={busy} onClick={onCreate}>
        ＋ 새 대화
      </button>
      <p className="eyebrow">나의 대화</p>
      <nav aria-label="이전 대화">
        {conversations.map((conversation) => (
          <button
            key={conversation.id}
            className={`conversation${conversation.id === currentId ? " active" : ""}`}
            title={conversation.title}
            aria-current={conversation.id === currentId ? "true" : undefined}
            onClick={() => onSelect(conversation.id)}
          >
            {conversation.title}
          </button>
        ))}
      </nav>
      <button className="subtle" hidden={!hasMore} onClick={onMore}>
        대화 더 보기
      </button>
      <div className="account">
        <span className="avatar" aria-hidden="true">
          나
        </span>
        <span className="username">{username}</span>
        <button className="subtle" onClick={onLogout}>
          로그아웃
        </button>
      </div>
    </aside>
  );
}
