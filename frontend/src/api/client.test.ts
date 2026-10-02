import { afterEach, expect, it, vi } from "vitest";
import { authAPI } from "./client";
import { APIError } from "./errors";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});
it("preserves cookie credentials and structured authentication errors", async () => {
  const fetch = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({
        error: {
          code: "INVALID_CREDENTIALS",
          message: "invalid",
          request_id: "request-id",
        },
      }),
      { status: 401 },
    ),
  );
  vi.stubGlobal("fetch", fetch);
  const body = { username: "user", password: "password" };
  await expect(authAPI.login(body)).rejects.toMatchObject({
    status: 401,
    code: "INVALID_CREDENTIALS",
    requestId: "request-id",
  });
  expect(fetch).toHaveBeenCalledWith(
    "/api/auth/login",
    expect.objectContaining({
      credentials: "same-origin",
      body: JSON.stringify(body),
    }),
  );
});
it("accepts a logout response without a JSON body", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response(null, { status: 204 })),
  );
  await expect(authAPI.logout()).resolves.toBeUndefined();
});
it("aborts a stalled request instead of holding the composer indefinitely", async () => {
  vi.useFakeTimers();
  vi.stubGlobal(
    "fetch",
    vi.fn(
      (_url: string, options: RequestInit) =>
        new Promise((_resolve, reject) => {
          options.signal!.addEventListener("abort", () =>
            reject(new DOMException("Aborted", "AbortError")),
          );
        }),
    ),
  );
  const result = authAPI.me();
  const assertion = expect(result).rejects.not.toBeInstanceOf(APIError);
  await vi.advanceTimersByTimeAsync(45000);
  await assertion;
  expect(vi.getTimerCount()).toBe(0);
});
