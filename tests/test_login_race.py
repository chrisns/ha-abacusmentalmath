"""Mock-based check that concurrent 401s coalesce into a single re-login.

Uses unittest.mock to fake the aiohttp session entirely — no network, no
real server. Runnable standalone: `python tests/test_login_race.py`.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from _pkg import load_api

api = load_api()


def _mock_response(status: int, body: dict) -> MagicMock:
    resp = MagicMock()
    resp.status = status
    resp.json = AsyncMock(return_value=body)
    return resp


async def main() -> None:
    login_calls = 0
    valid_token = "tok-fresh"

    async def fake_post(url, json=None, timeout=None):
        nonlocal login_calls
        login_calls += 1
        # Simulate real network latency so concurrent callers actually overlap.
        await asyncio.sleep(0.01)
        return _mock_response(200, {"access_token": valid_token})

    async def fake_get(url, headers=None, timeout=None):
        token_used = headers["authorization"].removeprefix("Bearer ")
        if token_used != valid_token:
            return _mock_response(401, {})
        return _mock_response(200, {"data": [{"amount": 1}]})

    session = MagicMock()
    session.post = fake_post
    session.get = fake_get

    client = api.AbacusMentalMathClient(session, "a@b.com", "correct-horse")
    client._token = "stale-token"  # noqa: SLF001 — force everyone to hit the 401 path at once

    # Ten concurrent requests all holding the same stale token.
    results = await asyncio.gather(*(client._get("/parent/1/profile") for _ in range(10)))  # noqa: SLF001

    assert all(r == {"data": [{"amount": 1}]} for r in results)
    assert login_calls == 1, f"expected exactly one re-login, got {login_calls}"
    print("OK")


if __name__ == "__main__":
    asyncio.run(main())
