import type {
  Conversation,
  ConversationPage,
  Credentials,
  SendRequest,
  Turn,
  TurnPage,
  User,
} from "./types";

import { APIError } from "./errors";

async function request<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 45000);
  try {
    const response = await fetch(`/api${path}`, {
      method,
      credentials: "same-origin",
      signal: controller.signal,
      ...(body === undefined
        ? {}
        : {
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          }),
    });
    const data = response.status === 204 ? undefined : await response.json();
    if (!response.ok) throw new APIError(data, response.status);
    return data as T;
  } finally {
    clearTimeout(timer);
  }
}
export const authAPI = {
  me: () => request<User>("/me"),
  signup: (body: Credentials) => request<User>("/auth/signup", "POST", body),
  login: (body: Credentials) => request<User>("/auth/login", "POST", body),
  logout: () => request<void>("/auth/logout", "POST"),
};
export const conversationsAPI = {
  create: () => request<Conversation>("/conversations", "POST", {}),
  list: (offset = 0) =>
    request<ConversationPage>(`/conversations?limit=100&offset=${offset}`),
  history: (id: number, beforeId: number | null = null) =>
    request<TurnPage>(
      `/conversations/${id}/turns?limit=50${beforeId ? `&before_id=${beforeId}` : ""}`,
    ),
  send: (id: number, body: SendRequest) =>
    request<Turn>(`/conversations/${id}/messages`, "POST", body),
};
