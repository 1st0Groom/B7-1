# 배움 · B7-1 AI 챗봇

로그인한 사용자가 OpenAI에 질문하고, 문맥을 이어가며 대화를 다시 조회하는 FastAPI 웹 앱입니다. React + TypeScript 화면과 API를 같은 FastAPI 서버에서 제공하고 SQLite에 계정·세션·대화를 저장합니다.

- 대상: 개념 설명과 질의응답이 필요한 학습자
- 핵심 흐름: 회원가입 → 로그인 → 질문 → 답변 → 후속 질문 → 재로그인 후 기록 조회
- 설계·ERD·API 예시: [설계 문서](docs/design.md)
- 과제 기준: [B7-1](docs/B7-1.md)
- 팀 역할·기여 기록: [팀 문서](docs/team.md)
- **외부 서비스 URL: 배포 후 기록 필요**
- **제출용 GitHub URL: 저장소 공개 범위 확인 후 기록 필요**

## 로컬 실행

Python 3.12, [uv](https://docs.astral.sh/uv/), Node.js 24, pnpm 12.3.4를 사용합니다. Python 의존성은 `uv.lock`, 프런트 의존성은 `frontend/pnpm-lock.yaml`에 고정되어 있습니다.

```bash
npm install --global pnpm@12.3.4
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
uv sync --frozen --extra dev
# .env가 이미 있다면 복사하지 않습니다.
cp .env.example .env
# .env의 OPENAI_API_KEY와 AI_MODEL을 설정합니다.
mkdir -p data
uv run --frozen alembic upgrade head
uv run --frozen uvicorn app.main:create_app --factory --reload --no-access-log
```

`http://localhost:8000`에서 아이디와 비밀번호로 가입하고 로그인합니다. 새 아이디는 영문·숫자·밑줄(`_`) 3~32자이며 대소문자를 구분하지 않습니다. 비밀번호는 조합 조건 없이 10~128자이며 공백도 그대로 취급합니다. `APP_ORIGIN`과 브라우저 주소는 정확히 같아야 합니다. `127.0.0.1`로 접근하려면 `.env`의 `APP_ORIGIN`도 변경하세요.

OpenAI는 [공식 Python SDK](https://developers.openai.com/api/docs/libraries)와 Responses API로 호출합니다. 키가 없거나 모델명이 비어 있으면 시작에 실패합니다. 테스트용 가짜 응답은 테스트 코드에만 있으며 운영 앱에는 없습니다. OpenAI 계정에서 사용 가능한 텍스트 모델을 `AI_MODEL`에 입력하고 실제 질문으로 연결을 검증하세요. 답변은 한 번에 표시되며 스트리밍은 지원하지 않습니다.

## 프런트 개발 (자동 반영)

일반 실행은 `http://localhost:8000`에서 빌드한 화면을 제공합니다. 프런트 코드를 수정한 뒤 `pnpm --dir frontend build`를 다시 실행하면 됩니다. Vite의 자동 반영을 사용하려면 터미널 두 개에서 실행하세요.

```bash
# 터미널 1: 개발용 출처를 명령에만 적용 (.env 수정 불필요)
APP_ORIGIN=http://localhost:5173 uv run --frozen uvicorn app.main:create_app --factory --reload --no-access-log

# 터미널 2
pnpm --dir frontend dev
```

이때 브라우저는 **`http://localhost:5173`**으로 접속합니다. Vite가 `/api`를 FastAPI 8000으로 프록시하므로 쿠키 인증을 그대로 사용합니다. 8000을 사용하는 기존 서버가 있으면 먼저 종료하세요. 개발을 마친 뒤 일반 실행 명령으로 돌아오면 `.env`의 `APP_ORIGIN`을 다시 사용합니다.

운영 Docker 빌드는 Node 단계에서 React를 빌드하고 결과만 Python 이미지에 복사합니다. 인스턴스에는 Node/pnpm 설치나 별도 프런트 서버가 필요하지 않습니다. OpenAI 키는 서버 `.env`에만 두며 `VITE_` 변수로 전달하지 않습니다.

## 환경 변수

| 이름 | 기본값 / 용도 |
| --- | --- |
| `APP_ENV` | `development`; 운영 Compose는 `production` 강제 |
| `APP_ORIGIN` | `http://localhost:8000`; 상태 변경 요청의 Origin 비교 기준 |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/app.db`; Compose는 `/data/app.db` |
| `OPENAI_API_KEY` | 필수. 서버에서만 사용하는 OpenAI API 키 |
| `AI_MODEL` | 필수. 계정에서 사용 가능한 OpenAI 모델 ID |
| `AI_TIMEOUT_SECONDS` | `30`; 0 초과 30 이하, SDK 재시도 없음 |
| `AI_MAX_OUTPUT_TOKENS` | `1000`; 16~1,000 |
| `AI_CONTEXT_WINDOW_TOKENS` | `8192`; 입력·출력 합산 예산. 선택 모델의 실제 한도 이하로 설정 |
| `AI_TOKEN_ENCODING` | 비어 있으면 모델명으로 tiktoken 인코딩 추론. 미지원 모델이면 적합한 인코딩을 명시 |
| `CHAT_CONTEXT_TURNS` | `5`; 최근 성공 문답 최대 5쌍 |
| `CHAT_CONTEXT_MAX_CHARS` | `12000`; 과거 문답의 문자 수 합계 |
| `SESSION_TTL_SECONDS` | `86400`; 발급부터 고정 만료, 최대 24시간 |
| `COOKIE_SECURE` | 로컬 `false`; 운영 Compose는 `true` 강제 |
| `LOG_LEVEL` | `INFO` |
| `APP_DOMAIN` | 운영 도메인, 예: `chat.example.com`; 스킴·경로 제외 |

문맥은 tiktoken으로 본문 토큰을 계산하고 메시지별 여유 및 출력 예산을 예약합니다. API의 정확한 토큰 집계와는 차이가 있을 수 있으므로 보수적인 예산을 사용하세요. 추론 모델의 출력 예산에는 내부 추론이 포함될 수 있습니다. 응답이 `completed` 상태가 아니거나 표시할 텍스트가 없으면 성공으로 저장하지 않습니다.

`.env`, DB·WAL·백업·로그·쿠키 파일은 Git과 이미지 빌드에서 제외합니다. 키를 README, 이슈, 스크린샷에 넣지 마세요. 질문과 답변은 DB에 저장하고 운영 로그에는 요청 ID·상태·식별자만 남깁니다.

## 인스턴스 배포

Linux 인스턴스 1대, Docker Engine + Compose, 인스턴스를 가리키는 도메인이 필요합니다. Caddy가 HTTPS 인증서를 발급하므로 외부 80/443 접근을 열고 SSH는 관리 대상에 제한합니다. 앱 8000 포트는 외부에 공개하지 않습니다.

```bash
cp .env.example .env
# OPENAI_API_KEY, AI_MODEL, APP_DOMAIN을 실제 값으로 설정합니다.
# Compose가 APP_ENV, APP_ORIGIN, COOKIE_SECURE, DATABASE_URL을 운영 값으로 덮어씁니다.
mkdir -p backups
sudo chown 10001:10001 backups
chmod 700 backups
docker compose config --quiet
docker compose up --build -d
docker compose ps
docker compose logs --tail=100 app
```

- `migrate`: 같은 이미지로 Alembic을 먼저 실행하는 일회성 서비스
- `app`: UID 10001로 실행, Uvicorn worker 1개, SQLite `/data` 영속 볼륨
- `caddy`: HTTPS와 앱 프록시, 인증서 영속 볼륨
- `172.29.71.0/24`: Compose 전용 네트워크. 앱은 Caddy의 `172.29.71.2`에서 온 프록시 헤더만 신뢰합니다. 기존 네트워크와 겹치면 서브넷·두 고정 주소·`--forwarded-allow-ips`를 함께 변경하세요.

배포 후 `https://도메인/health/ready`, 가입·로그인·실제 AI 질문, 컨테이너 재시작 후 대화 조회를 외부 네트워크에서 확인합니다. health는 OpenAI를 호출하지 않으므로 실제 키·모델의 사용 가능 여부를 보장하지 않습니다. API 키와 모델을 설정하기 전에는 운영 연결 검증이 완료된 상태가 아닙니다.

업데이트 시 앱을 중지하고 백업·마이그레이션을 완료한 뒤 시작합니다.

```bash
# 서버의 소스 코드를 원하는 버전으로 갱신한 뒤 실행
docker compose build
docker compose exec app python scripts/backup.py /data/app.db /backups/before-update.db
docker compose stop app
docker compose run --rm migrate
docker compose up -d
```

백업 파일명은 매번 새 이름을 사용합니다. `scripts/backup.py`는 SQLite backup API와 `integrity_check`를 사용합니다. 복원은 앱을 멈춘 상태에서 백업을 별도 데이터 볼륨에 복원하고, 해당 스키마와 호환되는 앱으로 먼저 검증한 뒤 운영에 적용하세요. 실행 중인 `.db`만 복사하거나 WAL 파일을 임의로 지우지 마세요. `docker compose down -v`는 대화·계정·인증서 볼륨까지 삭제하므로 일반 종료에는 사용하지 않습니다.

현재 배포는 단일 인스턴스·단일 worker용입니다. 시작할 때 남은 `pending`을 실패로 복구하므로 같은 DB에 여러 앱 프로세스를 띄우지 마세요. 로그인 IP당 분당 10회, 질문 사용자당 분당 10회 제한은 메모리에 있으며 재시작하면 초기화됩니다. 회원가입도 IP당 분당 10회, 대화 생성은 사용자당 분당 30회 제한합니다.

## API 및 DB 확인

모든 상태 변경 API는 정확한 `Origin`이 필요하고, 본문이 있으면 `Content-Type: application/json`이어야 합니다. 사용자는 세션 쿠키에서 결정합니다. 타인의 대화는 `404`, 미인증 API는 `401`을 반환합니다. 요청·응답의 전체 스키마는 `/openapi.json`, 의미와 예시는 [설계의 API 계약](docs/design.md#8-api-계약)을 참고하세요.

| 메서드 | 경로 | 동작 |
| --- | --- | --- |
| POST | `/api/auth/signup` | `{username, password}`로 가입 |
| POST | `/api/auth/login` | `{username, password}`로 로그인 및 세션 쿠키 발급 |
| POST | `/api/auth/logout` | 세션 폐기 |
| GET | `/api/me` | 현재 사용자 |
| POST | `/api/conversations` | `{}`로 새 대화 생성 |
| GET | `/api/conversations?limit=20&offset=0` | 내 대화 목록 |
| GET | `/api/conversations/{id}/turns?limit=50&before_id=100` | 대화 기록, 성공·실패·대기 포함 |
| POST | `/api/conversations/{id}/messages` | `{question, client_request_id}`로 질문 |
| GET | `/api/me/chats?limit=20&before_id=100` | 내 전체 문답 조회 |
| GET | `/health/live`, `/health/ready` | 프로세스 및 DB 준비 상태 |

같은 대화의 같은 UUID·질문은 저장 결과를 재사용하며 AI를 재호출하지 않습니다. 진행 중인 요청은 `409 CHAT_IN_PROGRESS`, 다른 질문에 같은 키를 쓰면 `409 IDEMPOTENCY_CONFLICT`입니다. 실패 후 새로 질문할 때는 새 UUID를 사용합니다. 프런트는 통신 오류가 나면 먼저 기록을 확인하고, 여전히 불명확하면 사용자가 결과 확인 버튼을 눌러 **같은 UUID**로 확인하도록 합니다. 진행 중인 기록은 2초 간격으로 최대 120초 재조회하고 이후 수동 확인으로 전환합니다.

로컬 평가 예시(예시 비밀번호는 운영 계정에 사용하지 마세요):

```bash
curl -sS http://localhost:8000/api/auth/signup \
  -H 'Origin: http://localhost:8000' -H 'Content-Type: application/json' \
  -d '{"username":"reviewer","password":"local-review-only-123"}'
curl -sS -c cookies.txt http://localhost:8000/api/auth/login \
  -H 'Origin: http://localhost:8000' -H 'Content-Type: application/json' \
  -d '{"username":"reviewer","password":"local-review-only-123"}'
curl -sS -b cookies.txt http://localhost:8000/api/conversations \
  -H 'Origin: http://localhost:8000' -H 'Content-Type: application/json' -d '{}'
# 응답의 대화 ID를 사용합니다. 아래 1은 예시입니다.
curl -sS -b cookies.txt http://localhost:8000/api/conversations/1/messages \
  -H 'Origin: http://localhost:8000' -H 'Content-Type: application/json' \
  -d '{"question":"FastAPI에서 라우터가 뭐야?","client_request_id":"83961cc9-28b5-45ea-8c2b-e6b85cf9f833"}'
curl -sS -b cookies.txt http://localhost:8000/api/me/chats
sqlite3 data/app.db '.parameter init' '.parameter set :user_id 1' '.read scripts/check_logs.sql'
```

`users → conversations → chat_turns` 관계로 사용자별 로그를 추적합니다. 세션은 `sessions`에 토큰의 SHA-256 해시만 보관합니다. DB 파일은 외부에 공개하지 않습니다.

## 코드 수정 위치

| 변경할 내용 | 파일 |
| --- | --- |
| 화면 경로·로그인 보호 | `frontend/src/App.tsx`, `frontend/src/components/RequireAuth.tsx` |
| API URL·HTTP 오류·응답 타입 | `frontend/src/api/` |
| 로그인·가입 화면 | `frontend/src/pages/AuthPage.tsx` |
| 채팅 화면 조립 | `frontend/src/pages/ChatPage.tsx` |
| 질문 전송·조회·재시도·polling | `frontend/src/chat/useChat.ts` |
| 대화 상태·응답 병합·오래된 응답 무시 | `frontend/src/chat/state.ts` |
| 사이드바·메시지·입력창 | `frontend/src/chat/Sidebar.tsx`, `TurnList.tsx`, `Composer.tsx` |
| 화면 스타일 | `frontend/src/styles/` |
| API 등록·HTTP 요청 및 응답 | `app/routers/` |
| 대화 생성·소유권·페이지 조회 | `app/services/conversations.py` |
| AI 호출·저장·중복 요청 처리 | `app/services/chat.py` |

React Router가 화면 이동을 관리하고 React가 상태에 따라 DOM을 렌더링합니다. FastAPI의 `pages.py`는 직접 접속할 때 React 진입 HTML을 제공하며 `/chat`의 세션도 검사합니다. `/api` 접두사와 서버 라우터 등록은 `app/routers/__init__.py`에서 관리합니다. API 자체의 인증·소유권 검사는 화면 보호와 별개로 항상 적용됩니다.

## 검증

```bash
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend check
pnpm --dir frontend test
pnpm --dir frontend build
uv sync --frozen --extra dev
uv run --frozen ruff check app tests migrations scripts
uv run --frozen ruff format --check app tests migrations scripts
uv run --frozen pytest -q
```

자동 테스트는 독립된 임시 SQLite에 실제 Alembic 마이그레이션을 적용합니다. 인증·만료·소유권, 문맥·페이지 이동, 중복·동시 질문, 타임아웃·중단·DB 실패, 재시작 복구, SDK 요청 직렬화 및 오류 처리를 검증합니다. 프런트는 Vitest로 응답 경합·페이지 병합·불명확한 요청 복구·통신 오류를 검증합니다. AI는 테스트 대역과 HTTP MockTransport를 사용하며 실제 OpenAI 비용은 발생하지 않습니다. CI도 같은 방식입니다.

브라우저 검증은 별도 테스트 서버와 Chromium으로 회원가입·로그인·질문·후속 질문·새로고침·모바일 화면을 확인합니다.

```bash
uv sync --frozen --extra dev --extra browser
uv run --frozen playwright install chromium
uv run --frozen python -m tests.browser_smoke
```

실제 OpenAI 호출·외부 HTTPS·인스턴스 재시작 검증과 팀별 PR·커밋 기록은 별도로 수행해야 합니다.
