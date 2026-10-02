from fastapi import Request
from fastapi.responses import JSONResponse

MESSAGES = {
    "AUTH_REQUIRED": "로그인이 필요합니다.",
    "INVALID_CREDENTIALS": "아이디 또는 비밀번호를 확인해 주세요.",
    "USERNAME_ALREADY_EXISTS": "이미 가입된 아이디입니다.",
    "ORIGIN_REJECTED": "요청 출처를 확인할 수 없습니다.",
    "VALIDATION_ERROR": "입력 형식과 길이를 확인해 주세요.",
    "CONVERSATION_NOT_FOUND": "대화를 찾을 수 없습니다.",
    "CHAT_IN_PROGRESS": "답변을 생성하고 있습니다. 기록을 다시 확인해 주세요.",
    "IDEMPOTENCY_CONFLICT": "같은 요청 ID로 다른 질문을 보낼 수 없습니다.",
    "AI_TIMEOUT": "현재 응답이 지연되고 있어요. 잠시 후 다시 시도해 주세요.",
    "AI_UNAVAILABLE": "AI 응답을 받을 수 없습니다. 잠시 후 다시 시도해 주세요.",
    "CONTEXT_TOO_LARGE": "질문이 모델의 입력 한도를 넘었습니다. 내용을 줄여 주세요.",
    "REQUEST_INTERRUPTED": "요청 처리가 중단되었습니다. 다시 시도해 주세요.",
    "DB_UNAVAILABLE": "저장 결과를 확인할 수 없습니다. 기록을 다시 조회해 주세요.",
    "RATE_LIMITED": "요청이 많습니다. 잠시 후 다시 시도해 주세요.",
    "INTERNAL_ERROR": "오류가 발생했습니다. 요청 ID와 함께 문의해 주세요.",
    "UNSUPPORTED_MEDIA_TYPE": "JSON 형식으로 요청해 주세요.",
    "REQUEST_TOO_LARGE": "요청 크기가 너무 큽니다.",
}
STATUS = {
    "AI_TIMEOUT": 504,
    "AI_UNAVAILABLE": 502,
    "CONTEXT_TOO_LARGE": 422,
    "REQUEST_INTERRUPTED": 409,
    "DB_UNAVAILABLE": 503,
    "INTERNAL_ERROR": 500,
}


class AppError(Exception):
    def __init__(self, code, status=None, turn_id=None, headers=None):
        self.code = code
        self.status = status or STATUS.get(code, 400)
        self.turn_id = turn_id
        self.headers = headers


def error_response(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status,
        headers=exc.headers,
        content={
            "error": {
                "code": exc.code,
                "message": MESSAGES.get(exc.code, "요청을 처리할 수 없습니다."),
                "request_id": getattr(request.state, "request_id", None),
                "turn_id": exc.turn_id,
            }
        },
    )
