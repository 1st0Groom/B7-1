"""Run a real browser against an isolated app with a fake AI; no API key or cost."""

import json
import multiprocessing
import socket
import tempfile
import time
import urllib.request

import uvicorn
from playwright.sync_api import expect, sync_playwright

from app.config import Settings
from app.errors import AppError
from app.main import create_app
from tests.conftest import FakeAI, migrate


class BrowserAI(FakeAI):
    async def generate(self, history, question):
        if question == "실패 후 재시도" and not any(q == question for _, q in self.calls):
            self.calls.append((history, question))
            raise AppError("AI_TIMEOUT")
        return await super().generate(history, question)


def serve(port, database_url):
    settings = Settings(
        _env_file=None,
        openai_api_key="browser-fake-only",
        ai_model="gpt-4o-mini",
        app_origin=f"http://127.0.0.1:{port}",
        database_url=database_url,
        log_level="WARNING",
    )
    app = create_app(settings, BrowserAI())
    uvicorn.run(app, host="127.0.0.1", port=port, access_log=False, log_level="warning")


def main():
    with tempfile.TemporaryDirectory(prefix="b7-browser-") as temporary:
        database_url = f"sqlite+aiosqlite:///{temporary}/browser.db"
        migrate(database_url)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        process = multiprocessing.Process(target=serve, args=(port, database_url))
        process.start()
        origin = f"http://127.0.0.1:{port}"
        try:
            for _ in range(100):
                try:
                    urllib.request.urlopen(f"{origin}/health/ready", timeout=1).close()
                    break
                except OSError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Browser test server did not start")
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"{origin}/chat")
                page.wait_for_url("**/login")
                page.get_by_role("link", name="회원가입", exact=True).click()
                page.wait_for_url("**/signup")
                page.go_back()
                page.wait_for_url("**/login")
                page.go_forward()
                page.wait_for_url("**/signup")
                page.get_by_label("아이디", exact=True).fill("browser_user")
                page.get_by_label("비밀번호", exact=True).fill("browser-test-password")
                page.get_by_role("button", name="회원가입").click()
                page.wait_for_url("**/login?registered=1")
                page.get_by_label("아이디", exact=True).fill("browser_user")
                page.get_by_label("비밀번호", exact=True).fill("browser-test-password")
                page.get_by_role("button", name="로그인").click()
                page.wait_for_url("**/chat")
                page.screenshot(path="/tmp/b7-chat-desktop.png", full_page=True)
                page.get_by_label("AI에게 질문하기").fill("FastAPI 라우터가 뭐야?")
                page.get_by_role("button", name="질문 보내기").click()
                expect(page.locator(".message.answer")).to_have_text("답변: FastAPI 라우터가 뭐야?")
                page.get_by_label("AI에게 질문하기").fill("<img src=x onerror=alert(1)>")
                expect(page.get_by_role("button", name="질문 보내기")).to_be_enabled()
                page.get_by_role("button", name="질문 보내기").click()
                expect(page.locator(".message.answer")).to_have_count(2)
                assert page.locator("#turns img").count() == 0
                page.reload()
                page.locator(".conversation").first.click()
                expect(page.locator(".message.answer")).to_have_count(2)
                page.screenshot(path="/tmp/b7-chat-conversation.png", full_page=True)

                # A response lost after commit must be recovered by reading stored history.
                def lose_response(route):
                    route.fetch()
                    route.abort("connectionreset")

                page.route("**/messages", lose_response, times=1)
                page.get_by_label("AI에게 질문하기").fill("연결이 끊겨도 기록 확인")
                page.get_by_role("button", name="질문 보내기").click()
                expect(page.locator(".message.answer")).to_have_count(3)
                expect(page.locator("#refresh-chat")).to_be_hidden()
                stored = page.request.get(f"{origin}/api/me/chats").json()["items"]
                assert len(stored) == 3
                expect(page.get_by_label("AI에게 질문하기")).to_have_value("")

                # A request lost before reaching the server uses the same UUID on recovery.
                lost = []

                def lose_request(route):
                    lost.append(route.request.post_data_json)
                    route.abort("connectionreset")

                page.route("**/messages", lose_request, times=1)
                page.get_by_label("AI에게 질문하기").fill("전송 전 연결 끊김")
                page.get_by_role("button", name="질문 보내기").click()
                expect(page.locator("#refresh-chat")).to_be_visible()
                expect(page.locator("#refresh-chat")).to_be_enabled()
                expect(page.get_by_role("button", name="질문 보내기")).to_be_disabled()
                with page.expect_request("**/messages") as retried:
                    page.locator("#refresh-chat").click()
                assert retried.value.post_data_json == lost[0]
                expect(page.locator(".message.answer")).to_have_count(4)
                expect(page.locator("#refresh-chat")).to_be_hidden()

                # A known failure is retried explicitly with a fresh UUID.
                page.get_by_label("AI에게 질문하기").fill("실패 후 재시도")
                page.get_by_role("button", name="질문 보내기").click()
                expect(page.locator(".failure")).to_contain_text("응답 시간이 초과")
                expect(page.get_by_role("button", name="다시 시도", exact=True)).to_be_enabled()
                page.get_by_role("button", name="다시 시도", exact=True).click()
                page.get_by_role("button", name="질문 보내기").click()
                expect(page.locator(".message.answer")).to_have_count(5)
                stored = page.request.get(f"{origin}/api/me/chats").json()["items"]
                attempts = [item for item in stored if item["question"] == "실패 후 재시도"]
                assert {item["status"] for item in attempts} == {"failed", "succeeded"}
                assert len({item["client_request_id"] for item in attempts}) == 2

                # Simulate a GET snapshot taken while the last answer was pending.
                def pending_snapshot(route):
                    response = route.fetch()
                    data = response.json()
                    data["items"][-1].update(status="pending", answer=None)
                    route.fulfill(response=response, body=json.dumps(data))

                page.route("**/turns?limit=50", pending_snapshot, times=1)
                page.locator(".conversation").first.click()
                expect(page.locator(".pending")).to_be_visible()
                expect(page.get_by_role("button", name="질문 보내기")).to_be_disabled()
                expect(page.locator(".pending")).to_have_count(0, timeout=7000)
                expect(page.locator(".message.answer")).to_have_count(5)
                page.set_viewport_size({"width": 390, "height": 844})
                expect(page.get_by_role("button", name="☰ 대화")).to_be_visible()
                page.screenshot(path="/tmp/b7-chat-mobile.png", full_page=True)
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                page.get_by_role("button", name="☰ 대화").click()
                page.get_by_role("button", name="로그아웃").click()
                page.wait_for_url("**/login")
                assert not errors, errors
                browser.close()
            print(
                "Browser smoke passed: signup/login/chat/follow-up/history/"
                "lost-response/stable-request-ID/retry/polling/router/XSS/mobile/logout"
            )
            print("Screenshots: /tmp/b7-chat-{desktop,conversation,mobile}.png")
        finally:
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join()


if __name__ == "__main__":
    main()
