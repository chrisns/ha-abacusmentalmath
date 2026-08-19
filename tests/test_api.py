"""Self-check for the API client against a real local aiohttp server.

No Home Assistant install needed — only aiohttp, which the integration
already depends on. Run directly:

    python tests/test_api.py

Loads const.py/api.py by file path (bypassing the package's __init__.py,
which pulls in homeassistant) so this stays a lightweight, dependency-free check.
"""
from __future__ import annotations

import asyncio

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from _pkg import load_api

api = load_api()


def _build_app(login_calls: list[int]) -> web.Application:
    """A fake Abacus Mental Math backend: one valid token at a time, one child."""
    state = {"token": None}

    async def login(request: web.Request) -> web.Response:
        body = await request.json()
        login_calls.append(1)
        if body.get("password") != "correct-horse":
            return web.json_response({"message": "invalid"}, status=401)
        state["token"] = f"tok{len(login_calls)}"
        return web.json_response({"access_token": state["token"], "token_type": "Bearer"})

    def _authed(request: web.Request) -> bool:
        return request.headers.get("authorization") == f"Bearer {state['token']}"

    async def students(request: web.Request) -> web.Response:
        if not _authed(request):
            return web.json_response({"message": "unauthorized"}, status=401)
        return web.json_response({"data": [{"id": 1, "first_name": "Test", "last_name": "Kid"}]})

    async def profile(request: web.Request) -> web.Response:
        if not _authed(request):
            return web.json_response({"message": "unauthorized"}, status=401)
        return web.json_response(
            {
                "data": {
                    "id": 1,
                    "username": "TestKid",
                    "coin_amount": 10,
                    "diamond_amount": 2,
                    "last_active_at": "2026-08-19T12:00:00Z",
                    "mode_type": "sprint",
                    "wins_daily": 1,
                    "wins_weekly": 2,
                    "wins_monthly": 3,
                }
            }
        )

    async def units(request: web.Request) -> web.Response:
        if not _authed(request):
            return web.json_response({"message": "unauthorized"}, status=401)
        period = request.match_info["period"]
        amounts = {"day": [{"amount": 3}, {"amount": 2}], "week": [{"amount": 20}], "month": [{"amount": 80}]}
        return web.json_response({"data": amounts[period]})

    app = web.Application()
    app.router.add_post("/parent/login", login)
    app.router.add_get("/parent/students", students)
    app.router.add_get("/parent/{id}/profile", profile)
    app.router.add_get("/parent/{id}/profile/units-finished/{period}/{offset}", units)
    return app


async def main() -> None:
    login_calls: list[int] = []
    server = TestServer(_build_app(login_calls))
    async with TestClient(server) as client:
        api.API_BASE_URL = str(client.make_url(""))

        # Wrong password -> AbacusMentalMathAuthError, not a generic error.
        bad = api.AbacusMentalMathClient(client.session, "a@b.com", "wrong")
        try:
            await bad.async_login()
        except api.AbacusMentalMathAuthError:
            pass
        else:
            raise AssertionError("expected AbacusMentalMathAuthError for a bad password")

        good = api.AbacusMentalMathClient(client.session, "a@b.com", "correct-horse")
        students = await good.async_list_students()
        assert students == [api.Student(id=1, first_name="Test", last_name="Kid")], students

        stats = await good.async_get_student_stats(students[0])
        assert stats.coin_amount == 10
        assert stats.diamond_amount == 2
        assert stats.units_today == 5, stats.units_today  # 3 + 2
        assert stats.units_this_week == 20
        assert stats.units_this_month == 80
        assert stats.wins_daily == 1 and stats.wins_weekly == 2 and stats.wins_monthly == 3

        # Force the cached token to go stale server-side, then confirm the
        # client transparently re-logs-in and the call still succeeds.
        calls_before = len(login_calls)
        good._token = "stale-token"  # noqa: SLF001 — poking internal state is the point of this check
        students_again = await good.async_list_students()
        assert students_again == students
        assert len(login_calls) == calls_before + 1, "expected exactly one re-login on 401"

    print("OK")


if __name__ == "__main__":
    asyncio.run(main())
