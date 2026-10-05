export interface Chat {
  id: number;
  question: string;
  answer: string;
  created_at: string;
}
interface Credentials {
  username: string;
  password: string;
}

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function request<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new APIError("서버와 연결할 수 없습니다.", 0);
  }
  // Error responses from proxies or missing routes may not be JSON.
  const data = await response.json().catch(() => undefined);
  if (!response.ok)
    throw new APIError(
      data?.error?.message ??
        `요청을 처리할 수 없습니다. (HTTP ${response.status})`,
      response.status,
    );
  return data as T;
}

export const api = {
  signup: (body: Credentials) => request("/auth/signup", "POST", body),
  login: (body: Credentials) => request("/auth/login", "POST", body),
  logout: () => request("/auth/logout", "POST"),
  chats: () => request<Chat[]>("/me/chats"),
  ask: (question: string) => request<Chat>("/chat", "POST", { question }),
};
