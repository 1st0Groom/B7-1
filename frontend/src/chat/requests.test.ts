import { expect, it, vi } from "vitest";
import { APIError } from "../api/errors";
import { submitTurn } from "./requests";

it.each([
  new TypeError("offline"),
  new APIError({ error: { code: "DB_UNAVAILABLE" } }, 503),
  new APIError({ error: { code: "INTERNAL_ERROR" } }, 500),
])("does not treat an unknown outcome as a definite failure", async (error) => {
  const api = { send: vi.fn().mockRejectedValue(error) };
  expect(
    await submitTurn(api, 1, {
      question: "question",
      client_request_id: "original",
    }),
  ).toEqual({ kind: "uncertain" });
  expect(api.send).toHaveBeenCalledTimes(1);
});
it("preserves a known rejection for the caller without retrying it", async () => {
  const error = new APIError({ error: { code: "AI_TIMEOUT" } }, 504);
  const api = { send: vi.fn().mockRejectedValue(error) };
  expect(
    await submitTurn(api, 1, {
      question: "question",
      client_request_id: "original",
    }),
  ).toEqual({ kind: "rejected", error });
  expect(api.send).toHaveBeenCalledTimes(1);
});
