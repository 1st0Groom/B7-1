# 팀 역할 및 기여 기록

확인된 팀원과 실제 작업 이력만 기록한다. `미정`·`미작성` 행은 작성 양식이며 완료 실적이 아니다.

| 팀원 | 담당 기능 | 개인 작업 요약 | 대표 커밋 | PR / 검토 링크 |
| --- | --- | --- | --- | --- |
| 미정 | 인증·세션·접근 제어 | 미작성 | 미작성 | 미작성 |
| 미정 | 대화 API·DB·OpenAI | 미작성 | 미작성 | 미작성 |
| solbao-dev | 프론트엔드 화면·UX 개선, 팀 Git/PR 협업 규칙 문서화 | 초보자용 화면·예시 질문, 인증·질문 입력·응답 대기·학습 기록 UX 개선; Git/PR 협업 규칙 작성 | `877e65f`, `5569ef3`, `4463cae`, `906a99e`, `dfc87ae` 등 아래 9개 | [#4](https://github.com/codyssey-kr/B7-1/pull/4)·[#5](https://github.com/codyssey-kr/B7-1/pull/5) 병합, [#13](https://github.com/codyssey-kr/B7-1/pull/13) Open·리뷰 대기 |
| 미정 | 배포·로그·통합 검증 | 미작성 | 미작성 | 미작성 |

팀 인원에 맞게 역할을 조정하고 각 기능 담당자가 테스트와 문서를 함께 작성한다. 기능 브랜치 → PR → 다른 팀원 검토 → merge commit 순서로 통합한다. 팀원별 유의미한 커밋 10회 이상과 PR 기반 머지 기록은 실제 Git 이력으로 증빙한다. 자동 생성된 초기 구현이나 이 문서의 역할 예시만으로 개인 기여 요건이 충족되지는 않는다.

## solbao-dev 개인 기여 상세

아래는 이 문서 변경 전에 작성한 기존 기여 커밋 9개다.

- 이전 프론트엔드 작업([PR #4](https://github.com/codyssey-kr/B7-1/pull/4), 병합):
  - `877e65f` `feat: add beginner-friendly service identity` — 인증·채팅 화면에 개발 초보자를 위한 서비스 이름과 안내 문구를 적용했다.
  - `f18dc06` `feat: style beginner-friendly learning chat UI` — 인증·채팅 화면의 카드, 입력·버튼, 간격, 색상과 좁은 화면 스타일을 개선했다.
  - `5569ef3` `feat: add example questions for beginner users` — 예시 질문 3개를 추가하고, 버튼을 누르면 해당 질문이 textarea에 들어가도록 했다.
- 팀 협업 문서([PR #5](https://github.com/codyssey-kr/B7-1/pull/5), 병합):
  - `4463cae` `docs: add team Git and PR collaboration guidelines` — 작업 브랜치, 의미 있는 커밋, 다른 팀원 검토와 PR 병합 흐름을 이 문서에 기록했다.
- 프론트엔드 UX 작업([PR #13](https://github.com/codyssey-kr/B7-1/pull/13), Open·리뷰 대기):
  - `a817ab8` `feat: add auth submission feedback` — 로그인·회원가입 제출 중 버튼 문구를 바꾸고 제출·화면 전환 버튼을 잠가 중복 제출을 막았다.
  - `fcb9a3e` `feat: show chat question character count` — 질문 글자 수를 표시하고 입력창에 `aria-describedby`로 연결했다.
  - `f8765bc` `feat: add auth flow loading feedback` — 가입·로그인 상황별 로딩 화면과 최소 표시 시간을 추가하고, 최초 세션 확인에는 인위적 지연을 두지 않았다.
  - `906a99e` `feat: show pending chat response` — 전송 직후 질문·AI 답변 대기 상태를 표시하고, 응답 대기 중 입력을 잠갔다. 성공 응답에는 최소 3초 표시와 조건부 자동 스크롤을 적용했으며, 실패 시 오류 안내와 입력 질문을 유지했다.
  - `dfc87ae` `feat: add learning history section` — 기존 예시 질문을 기록이 없는 처음 사용자에게만 보이도록 조건을 개선했다. 저장된 질문·AI 답변·시간을 읽기 전용 “나의 학습 기록”으로 표시하고 pending 질문을 저장 기록 목록과 분리했다.

PR #13의 프론트엔드 검사(TypeScript·Prettier), 프로덕션 Vite 빌드, `git diff --check`가 통과했다. AI 미연결 상태의 오류 안내, 실패 후 질문 유지, 처음 사용자 예시 질문 화면을 확인했다. 실제 AI 성공 답변 표시, pending에서 실제 문답으로 전환·중복 여부·최소 표시 시간·자동 스크롤, DB 저장 및 학습 기록 표시, 새로고침·재로그인 후 사용자별 복원과 사용자 간 기록 분리는 **통합 테스트 예정**이다.

## Git / PR 협업 규칙

아래는 위 통합 흐름을 일관되게 따르기 위한 팀 협업 규칙이며, 과제의 공식 필수 규칙을 새로 정하는 내용은 아니다.

### 브랜치

- `main`에서 직접 작업하지 않고, 작업 목적별로 별도 브랜치를 만든다.
- 하나의 브랜치는 하나의 명확한 작업 목적만 다룬다. 예: `feat/learning-chat-ui`, `docs/team-pr-guidelines`.

### 커밋

- 기능이나 작업 목적에 따라 의미 있는 단위로 커밋한다. 커밋 수를 늘리기 위한 불필요한 분할은 하지 않는다.
- 커밋 메시지만 보고도 변경 목적을 알 수 있게 작성한다.

### PR (Pull Request)

- 작업 브랜치는 PR을 통해 `main`에 병합하고, 병합 전 다른 팀원의 검토를 받는다.
- PR에는 가능하면 작업 목적, 주요 변경 사항, 작업 커밋, 테스트 및 확인 결과, 변경하지 않은 범위 또는 영향 범위를 기록한다.
- 관련 없는 작업을 하나의 PR에 섞지 않는다. PR 생성 전 변경 파일과 커밋을 확인한다.

### 기본 작업 흐름

`main` 최신화 → 작업 브랜치 생성 → 구현 및 확인 → 의미 있는 단위로 커밋 → fork의 작업 브랜치에 push → PR 생성 → 다른 팀원 검토 → `main` 병합
