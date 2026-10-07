# AI 답변 품질 점검

시스템 프롬프트(`app/services/prompts.py`)나 문맥 설정(`app/services/chat.py`)을 바꿀 때마다 아래 질문 세트로 같은 방식으로 점검하고 결과를 기록한다. 대상 사용자는 개발 초보자다.

## 1. 정성 평가: 고정 질문 세트

평가 회차마다 새 테스트 계정을 만들고 대화 기록이 없는 화면에서 시작한다. 로그아웃·재로그인해도 기존 대화는 남는다. 변경 전후에는 같은 `AI_MODEL`과 질문 순서를 사용한다.

운영 서버의 같은 터미널에서 아래 변수를 준비한다. 출력된 이름으로 웹에서 회원가입한 뒤, 그 계정은 이번 평가에만 사용한다.

```bash
REVIEW_USER="quality-$(date -u +%Y%m%dT%H%M%SZ)"
REVIEW_START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
REVIEW_LOG="${REVIEW_USER}.log"
printf '평가 계정: %s\n' "$REVIEW_USER"
```

웹 화면에서 아래 질문을 순서대로 보내고, 각 응답이나 오류 안내가 나온 뒤 다음 질문으로 진행한다. 같은 회차에서 실패한 질문을 추가로 재시도하지 않는다. 2번과 4번은 바로 앞 질문에 이어서 보낸다(문맥 유지 확인).

| # | 질문 | 확인할 점 |
| --- | --- | --- |
| 1 | 변수와 함수의 차이가 뭐야? | 핵심 답을 먼저 말하는가 |
| 2 | 간단한 예시도 보여줘 | 1번 내용을 이어받아 짧은 코드 예시를 주는가 |
| 3 | API가 뭔지 쉽게 설명해줘 | 일상 비유를 쓰는가, 용어를 풀어 주는가 |
| 4 | 그럼 REST API는? | 3번 문맥을 이어받는가 |
| 5 | Git과 GitHub는 뭐가 달라? | 둘을 헷갈리지 않게 비교하는가 |
| 6 | async/await가 뭐야? | 초보자 수준으로 설명하는가 |
| 7 | What is a database? | 영어로 답하는가 |
| 8 | 파이썬 `list.magic_sort()` 사용법 알려줘 | 없는 함수를 지어내지 않고 없다고 말하는가 |
| 9 | 그거 | 모호한 질문에 되묻거나 모른다고 말하는가 |
| 10 | 공백만 입력 | 화면에서 전송이 막히는가 (서버는 422) |

## 2. 채점 기준

1~9번 답변마다 아래 4개 항목을 1~5점으로 매긴다. 10번은 통과/실패만 기록한다.

| 항목 | 5점 | 1점 |
| --- | --- | --- |
| 정확성 | 틀린 내용이 없다 | 핵심 내용이 틀렸다 |
| 이해하기 쉬움 | 용어를 풀어 쓰고 단계적으로 설명한다 | 전문 용어를 설명 없이 나열한다 |
| 예시 | 짧고 실행 가능한 예시나 적절한 비유가 있다 | 필요한데 예시가 없거나 너무 길다 |
| 문맥·정직성 | 앞 대화를 이어받고, 모르면 모른다고 한다 | 앞 대화를 무시하거나 내용을 지어낸다 |

## 3. 정량 지표: 서버 로그

모든 질문의 응답이나 오류 안내를 확인한 뒤, 앞서 변수를 준비한 터미널에서 로그를 저장한다. 시작 시각 이후의 로그 중 평가 계정의 `ai_call_start`에 연결된 요청 ID만 선택한다. `user_id`가 없는 `ai_provider_error`도 같은 요청 ID로 함께 보관한다.

```bash
docker compose logs --no-color --no-log-prefix --since "$REVIEW_START" app > "${REVIEW_USER}-all.log"
docker compose exec -T app python -c '
import json
import sqlite3
import sys

with sqlite3.connect("file:/data/app.db?mode=ro", uri=True) as db:
    user = db.execute("SELECT id FROM users WHERE username = ?", (sys.argv[1],)).fetchone()
if user is None:
    raise SystemExit("평가 계정을 찾을 수 없습니다.")

events = []
for line in sys.stdin:
    try:
        events.append(json.loads(line))
    except json.JSONDecodeError:
        continue
request_ids = {
    event["request_id"] for event in events
    if event.get("event") == "ai_call_start" and event.get("user_id") == user[0]
}
for event in events:
    if event.get("request_id") in request_ids:
        print(json.dumps(event, ensure_ascii=False))
' "$REVIEW_USER" < "${REVIEW_USER}-all.log" > "$REVIEW_LOG"
```

이후 지표는 필터링된 `REVIEW_LOG` 파일에서만 집계한다. 다른 계정이나 이전 평가의 로그가 포함된 `-all.log` 파일은 집계에 사용하지 않는다.

| 지표 | 확인 방법 |
| --- | --- |
| AI 호출 수 | `grep -c '"event": "ai_call_start"' "$REVIEW_LOG"` |
| AI 실패 수 | `grep -c '"event": "ai_call_failed"' "$REVIEW_LOG"` |
| 실패 원인 | `grep '"event": "ai_provider_error"' "$REVIEW_LOG"` 의 `category` |
| AI 호출 성공 시 소요 시간 | `grep '"event": "ai_call_success"' "$REVIEW_LOG"` 의 `latency_ms` |
| 문맥으로 보낸 대화 수 | `grep '"event": "ai_call_start"' "$REVIEW_LOG"` 의 `context_turns` |

실패율 = AI 실패 수 ÷ AI 호출 수. 호출 수가 0이면 실패율을 계산하지 않고 미측정으로 기록한다. 1~9번을 모두 보낸 회차의 호출 수가 9가 아니면 인증·입력 검증·질문 횟수 제한 또는 로그 수집 범위를 먼저 확인한다.

## 4. 결과 기록

메모에 평가 계정, 사용한 `AI_MODEL`, 해당 회차의 로그 파일명을 함께 남긴다.

| 날짜 | 바꾼 내용 | 1~9번 평균 점수 | 10번 | 실패율 | 메모 |
| --- | --- | --- | --- | --- | --- |
| | | | | | |
