from fastapi.responses import JSONResponse

ERRORS = {
    "AUTH_REQUIRED": (401, "로그인이 필요합니다."),
    "INVALID_CREDENTIALS": (401, "아이디 또는 비밀번호를 확인해 주세요."),
    "USERNAME_ALREADY_EXISTS": (409, "이미 가입된 아이디입니다."),
    "VALIDATION_ERROR": (422, "입력 형식과 길이를 확인해 주세요."),
    "AI_TIMEOUT": (504, "현재 응답이 지연되고 있어요. 잠시 후 다시 시도해 주세요."),
    "AI_UNAVAILABLE": (502, "AI 응답을 받을 수 없습니다. 잠시 후 다시 시도해 주세요."),
    "AI_RATE_LIMITED": (503, "지금 질문이 많이 몰려 있어요. 잠시 후 다시 시도해 주세요."),
    "AI_QUOTA_EXCEEDED": (503, "AI 서비스의 사용 한도가 소진되었어요. 관리자에게 문의해 주세요."),
    "DB_UNAVAILABLE": (503, "대화를 저장하지 못했습니다. 잠시 후 다시 시도해 주세요."),
    "INTERNAL_ERROR": (500, "오류가 발생했습니다. 잠시 후 다시 시도해 주세요."),
}


class AppError(Exception):
    def __init__(self, code):
        self.code = code
        self.status, self.message = ERRORS[code]


def error_response(exc: AppError):
    return JSONResponse(
        status_code=exc.status, content={"error": {"code": exc.code, "message": exc.message}}
    )
