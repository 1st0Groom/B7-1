# B7-1 AI 챗봇

로그인한 사용자가 웹 페이지에서 질문하면 FastAPI 서버가 OpenAI API를 호출해 답변을 보여 주고, 질문과 답변을 SQLite에 저장하는 서비스입니다. 화면은 React로 만들고 같은 FastAPI 서버가 제공합니다.

- 대상: 개념 설명과 질의응답이 필요한 학습자
- 핵심 흐름: 회원가입 → 로그인 → 질문 → 답변 → 후속 질문(최근 대화 문맥 유지) → 재로그인 후 기록 조회
- 설계·ERD·API 예시: [설계 문서](docs/design.md)
- 과제 기준: [B7-1](docs/B7-1.md)
- 팀 역할·기여 기록: [팀 문서](docs/team.md)
- **외부 서비스 URL: 배포 후 기록 필요**
- **제출용 GitHub URL: 저장소 공개 범위 확인 후 기록 필요**

## 로컬 실행

Python 3.12, [uv](https://docs.astral.sh/uv/), Node.js 24, pnpm 12.3.4를 사용합니다.

```bash
npm install --global pnpm@12.3.4
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
uv sync --frozen --extra dev
cp .env.example .env   # OPENAI_API_KEY와 AI_MODEL을 설정합니다.
mkdir -p data
uv run --frozen uvicorn app.main:create_app --factory --reload
```

`http://localhost:8000`에서 가입하고 로그인합니다. DB 테이블은 서버 시작 시 자동으로 생성됩니다. 이전 버전에서 만든 `data/app.db`가 있다면 스키마가 다르므로 삭제한 뒤 실행하세요. 프런트를 수정했다면 `pnpm --dir frontend build`를 다시 실행합니다. 자동 반영 개발 서버는 위 서버를 띄운 상태에서 `pnpm --dir frontend dev`로 실행하고 `http://localhost:5173`에 접속합니다. Vite가 `/api`를 8000으로 프록시합니다.

## 환경 변수

| 이름 | 기본값 / 용도 |
| --- | --- |
| `OPENAI_API_KEY` | 필수. 서버에서만 사용하는 OpenAI API 키 |
| `AI_MODEL` | 필수. 계정에서 사용 가능한 OpenAI 모델 ID |
| `AI_TIMEOUT_SECONDS` | `30`; OpenAI 호출 시간 제한(초), 자동 재시도 없음 |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/app.db`; Compose는 `/data/app.db` |

## 민감정보 관리

- API 키는 `.env`에만 두고 코드·문서·이미지에 넣지 않습니다. `.env.example`에는 변수 이름과 비밀이 아닌 기본값만 있습니다.
- `.gitignore`와 `.dockerignore`가 `.env`, DB 파일, 로그를 제외합니다.
- OpenAI 호출은 서버에서만 하며 브라우저에는 답변만 전달합니다.
- 로그에는 질문·답변·비밀번호를 남기지 않습니다.
- **비밀번호는 DB에 평문으로 저장되고 HTTP로 전송됩니다. 실제로 쓰는 비밀번호를 사용하지 마세요.**

## EC2 배포

`infra/ec2.yaml`은 기본 VPC에 EC2 1대와 보안 그룹을 만드는 CloudFormation 템플릿입니다. 서울 리전(`ap-northeast-2`)에서 사용합니다. 기본값은 이미지 빌드 여유를 위한 `t3.small`이며, AWS 사용량은 계정 크레딧을 차감하거나 요금이 발생할 수 있으니 생성 전에 확인하고 평가가 끝나면 스택을 삭제합니다.

### 스택 생성

먼저 서울 리전에 EC2 키 페어가 있는지 확인합니다. 없다면 EC2 콘솔의 **키 페어**에서 새 키 페어를 만들고 내려받은 `.pem` 파일을 저장소 밖의 안전한 곳에 보관합니다. 개인 키는 다시 내려받을 수 없으므로 저장소나 채팅에 올리지 않습니다. 현재 공인 IPv4 주소도 확인합니다.

AWS 콘솔에서 **CloudFormation → 스택 생성 → 새 리소스 사용(표준)**을 선택하고 `infra/ec2.yaml`을 업로드합니다. 다음 값을 설정합니다.

| 파라미터 | 값 |
| --- | --- |
| `KeyName` | 앞에서 확인한 EC2 키 페어 |
| `SshCidr` | 현재 공인 IPv4 주소에 `/32`를 붙인 값, 예: `203.0.113.10/32` |
| `InstanceType` | 기본 `t3.small` 권장 |
| `AmazonLinux2023Ami` | 기본값 유지 |

스택을 생성한 뒤 **Outputs**의 `PublicIp`와 `ServiceUrl`을 확인합니다. HTTP 80 포트는 외부 공개이고 SSH 22 포트는 지정한 주소에서만 접속됩니다. 템플릿은 기본 VPC를 사용하므로 서울 리전에 기본 VPC가 있어야 합니다.

### 앱 실행

내 컴퓨터 터미널에서 개인 키 권한을 제한하고 인스턴스에 접속합니다.

```bash
chmod 400 /path/to/key.pem
PUBLIC_IP="REPLACE_WITH_PUBLIC_IP"  # CloudFormation Outputs의 PublicIp 값으로 교체
ssh -i /path/to/key.pem "ec2-user@$PUBLIC_IP"
```

인스턴스 터미널에서 Docker를 설치하고 시작합니다.

```bash
sudo dnf install -y docker git nano
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user
exit
```

SSH로 다시 접속한 뒤 Docker Compose 플러그인을 설치합니다. 플러그인은 Docker CLI에 사용자별로 설치됩니다.

```bash
mkdir -p ~/.docker/cli-plugins
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
  -o ~/.docker/cli-plugins/docker-compose
chmod +x ~/.docker/cli-plugins/docker-compose
docker compose version
```

PR이 공개 저장소의 기본 브랜치에 머지된 뒤 저장소를 내려받고 서비스를 시작합니다.

```bash
git clone https://github.com/codyssey-kr/B7-1.git
cd B7-1
cp .env.example .env
nano .env   # OPENAI_API_KEY와 AI_MODEL을 설정합니다.
docker compose up --build -d
docker compose ps
docker compose logs --tail=100 app
```

서비스 주소는 `http://<PublicIp>`입니다. 배포 후 README 첫 부분의 외부 서비스 URL을 실제 주소로 바꾸고, 외부 네트워크에서 가입·로그인·AI 질문·재시작 후 대화 기록 조회를 확인합니다. 코드를 업데이트할 때는 저장소에서 `git pull`한 뒤 `docker compose up --build -d`를 실행합니다.

### DB 백업과 정리

대화 DB는 EC2 내부의 Docker 볼륨 `app_data`에 있습니다. 스택 삭제 전에 필요하면 인스턴스에서 백업합니다.

```bash
docker compose cp app:/data/app.db ./app.db
```

작업을 마치면 CloudFormation에서 해당 스택을 삭제합니다. EC2와 루트 디스크도 삭제되므로 백업하지 않은 DB는 복구할 수 없습니다. `docker compose down -v`도 DB 볼륨을 삭제하므로 평소 업데이트에는 사용하지 않습니다. 마이그레이션 도구가 없으므로 DB 스키마(`app/models.py`)를 바꾸면 저장된 계정·대화가 초기화됩니다.

## API

전체 스키마는 서버의 `/docs`, 요청·응답 예시는 [설계의 API 명세](docs/design.md#6-api-명세)를 참고하세요. 로그인하지 않은 채팅 요청은 `401`을 반환합니다.

| 메서드 | 경로 | 동작 |
| --- | --- | --- |
| POST | `/api/auth/signup` | `{username, password}`로 가입 |
| POST | `/api/auth/login` | 로그인, `session` 쿠키 발급 |
| POST | `/api/auth/logout` | 세션 폐기 |
| POST | `/api/chat` | `{question}`으로 질문, 저장된 문답 반환 |
| GET | `/api/me/chats` | 내 대화 로그 조회 |

```bash
curl -sS http://localhost:8000/api/auth/signup -H 'Content-Type: application/json' \
  -d '{"username":"reviewer","password":"local-review-only"}'
curl -sS -c cookies.txt http://localhost:8000/api/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"reviewer","password":"local-review-only"}'
curl -sS -b cookies.txt http://localhost:8000/api/chat -H 'Content-Type: application/json' \
  -d '{"question":"FastAPI에서 라우터가 뭐야?"}'
curl -sS -b cookies.txt http://localhost:8000/api/me/chats
```

## DB 확인

`chats` 테이블에 사용자 ID, 생성 시각, 질문, 답변이 저장됩니다. `scripts/check_logs.sql`은 특정 사용자의 최근 대화 20건을 조회합니다.

```bash
sqlite3 data/app.db '.parameter init' '.parameter set :user_id 1' '.read scripts/check_logs.sql'
# 운영 서버: docker compose cp app:/data/app.db ./app.db 후 같은 명령을 app.db에 실행
```

## 검증

```bash
pnpm --dir frontend check
pnpm --dir frontend build
uv run --frozen ruff check app
```

자동 테스트는 두지 않습니다. B7-1 요구사항별 확인 절차는 [점검 시나리오](docs/check-scenario.md)에 있으며, AI 에이전트나 사람이 그대로 따라 실행할 수 있습니다.
