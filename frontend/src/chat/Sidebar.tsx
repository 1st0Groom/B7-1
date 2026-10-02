import { Brand } from "../components/Brand";
import type { ChatState } from "./state";

interface Props {
  state: ChatState;
  username: string;
  open: boolean;
  onCreate: () => void;
  onSelect: (id: number) => void;
  onMore: () => void;
  onLogout: () => void;
}
export function Sidebar({
  state,
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
      <button
        id="new-chat"
        className="new-chat"
        disabled={state.busy}
        onClick={onCreate}
      >
        ＋ 새 대화
      </button>
      <p className="eyebrow">나의 대화</p>
      <nav id="conversations" aria-label="이전 대화">
        {state.conversations.map((conversation) => (
          <button
            key={conversation.id}
            className={`conversation${conversation.id === state.current ? " active" : ""}`}
            title={conversation.title}
            aria-current={
              conversation.id === state.current ? "true" : undefined
            }
            onClick={() => onSelect(conversation.id)}
          >
            {conversation.title}
          </button>
        ))}
      </nav>
      <button
        id="more-conversations"
        className="subtle"
        hidden={!state.hasMore}
        onClick={onMore}
      >
        대화 더 보기
      </button>
      <div className="account">
        <span className="avatar" aria-hidden="true">
          나
        </span>
        <span className="username">{username}</span>
        <button id="logout" className="subtle" onClick={onLogout}>
          로그아웃
        </button>
      </div>
    </aside>
  );
}
