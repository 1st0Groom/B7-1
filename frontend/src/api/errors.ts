interface ErrorBody {
  error?: { code?: string; message?: string; request_id?: string };
}
export class APIError extends Error {
  code?: string;
  requestId?: string;
  constructor(
    data: ErrorBody,
    public status: number,
  ) {
    super(data.error?.message || "요청을 처리할 수 없습니다.");
    this.code = data.error?.code;
    this.requestId = data.error?.request_id;
  }
}
export function explain(error: unknown): string {
  return error instanceof APIError
    ? error.message + (error.requestId ? ` (요청 ID: ${error.requestId})` : "")
    : "서버와 연결할 수 없습니다. 연결 상태를 확인해 주세요.";
}
