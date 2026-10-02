import type {
  Conversation,
  ConversationPage,
  SendRequest,
  Turn,
  TurnPage,
} from "../api/types";

export interface ConversationCatalog {
  list(offset?: number): Promise<ConversationPage>;
  create(): Promise<Conversation>;
}
export interface TurnSender {
  send(id: number, payload: SendRequest): Promise<Turn>;
}
export interface ChatGateway extends ConversationCatalog, TurnSender {
  history(id: number, beforeId?: number | null): Promise<TurnPage>;
}
