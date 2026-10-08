# 배포 및 운영

아래 명령은 **저장소 루트**에서 실행합니다. 환경 변수는 [루트 README](../README.md#환경-변수), 공통 컨테이너 실행 명령은 [도커 실행](../README.md#도커-실행)을 참고합니다.

## 서버 준비

Linux 인스턴스 1대와 Docker Engine + Compose가 필요합니다. 외부에서 80 포트로 접속할 수 있게 엽니다.

Amazon Linux 2023 x86_64에서 `docker compose up --build`가 Buildx 0.17 이상을 요구하면 다음 플러그인을 설치합니다.

```bash
mkdir -p ~/.docker/cli-plugins
curl -fSL https://github.com/docker/buildx/releases/download/v0.37.2/buildx-v0.37.2.linux-amd64 \
  -o ~/.docker/cli-plugins/docker-buildx
chmod +x ~/.docker/cli-plugins/docker-buildx
docker buildx version
```

## 업데이트와 DB 초기화

업데이트할 때도 `docker compose up --build -d`를 다시 실행합니다. `docker compose down -v`는 DB 볼륨까지 삭제하므로 평소에는 사용하지 않습니다. 마이그레이션 도구가 없으므로 DB 스키마(`app/models.py`)를 바꾸면 DB를 초기화해야 하며 저장된 계정·대화가 모두 삭제됩니다. 로컬은 `data/app.db`를 지우고, 서버는 `docker compose down -v && docker compose up --build -d`를 실행합니다.

## 운영 DB 조회

운영 서버에서는 저장소 루트에서 아래 명령을 실행합니다. 컨테이너의 Python으로 DB를 읽기 전용으로 열어 조회하므로 실행 중인 DB 파일을 복사하거나 서버에 `sqlite3` CLI를 추가 설치할 필요가 없습니다. 끝의 `1`은 조회할 계정의 `user_id`로 바꾸며, 첫 출력의 `users` 목록에서 ID를 확인할 수 있습니다.

```bash
docker compose exec -T app python -c '
import sqlite3
import sys

with sqlite3.connect("file:/data/app.db?mode=ro", uri=True) as db:
    print("users:", db.execute("SELECT id, username FROM users").fetchall())
    rows = db.execute(sys.stdin.read(), {"user_id": int(sys.argv[1])})
    print(*(column[0] for column in rows.description), sep="\t")
    for row in rows:
        print(*row, sep="\t")
' 1 < scripts/check_logs.sql
```

조회 결과에는 사용자와 대화 내용이 포함되므로 외부에 공유하지 않습니다.

## 배포 확인

배포 후 외부 네트워크에서 가입·로그인·실제 AI 질문·재시작 후 기록 조회를 확인합니다.

서비스 주소는 [루트 README](../README.md)에 기록합니다.

## 배포 기록

- **배포 검증(2026-10-08, @1st0Groom 기록):** 외부 접속, 로그인 후 네이토 AI 응답, 앱 재시작 후 대화 기록 유지 확인
