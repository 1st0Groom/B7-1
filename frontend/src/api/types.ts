export interface User {
  id: number;
  username: string;
}
export interface Credentials {
  username: string;
  password: string;
}
export interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}
export interface SendRequest {
  question: string;
  client_request_id: string;
}
export interface Turn extends SendRequest {
  id: number;
  conversation_id: number;
  answer: string | null;
  status: "pending" | "succeeded" | "failed";
  error_code: string | null;
  created_at: string;
  completed_at: string | null;
}
export interface TurnPage {
  items: Turn[];
  next_before_id: number | null;
}
export interface ConversationPage {
  items: Conversation[];
  limit: number;
  offset: number;
}
