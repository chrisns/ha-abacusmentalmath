"""Thin async client for the (unofficial, reverse-engineered) Abacus Mental Math parent API."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import API_BASE_URL

_LOGGER = logging.getLogger(__name__)

_TIMEOUT = ClientTimeout(total=30)


class AbacusMentalMathError(Exception):
    """Base error talking to the Abacus Mental Math API."""


class AbacusMentalMathAuthError(AbacusMentalMathError):
    """Raised when the parent email/password is rejected."""


@dataclass
class Student:
    """A child listed under the parent account."""

    id: int
    first_name: str
    last_name: str


@dataclass
class StudentStats:
    """Everything the integration tracks for one child."""

    student: Student
    username: str | None = None
    coin_amount: int = 0
    diamond_amount: int = 0
    last_active_at: datetime | None = None
    mode_type: str | None = None
    wins_daily: int = 0
    wins_weekly: int = 0
    wins_monthly: int = 0
    units_today: int = 0
    units_yesterday: int = 0
    units_this_week: int = 0
    units_this_month: int = 0
    week_series: list[dict[str, Any]] = field(default_factory=list)
    month_series: list[dict[str, Any]] = field(default_factory=list)


def _sum_amount(payload: dict[str, Any]) -> int:
    return sum(row.get("amount", 0) for row in payload.get("data", []))


def _parse_timestamp(value: str | None) -> datetime | None:
    """Parse the API's ISO-ish timestamp string into an aware datetime, or None."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _LOGGER.debug("Could not parse timestamp %r", value)
        return None


class AbacusMentalMathClient:
    """Logs in as a parent and reads child progress data.

    This talks to a private, undocumented API the official mobile app uses
    (there is no public developer program). Endpoints may change without
    notice — see the README for what's been reverse-engineered so far.
    """

    def __init__(self, session: ClientSession, email: str, password: str) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._token: str | None = None
        self._login_lock = asyncio.Lock()

    async def async_login(self) -> None:
        """Authenticate and cache a bearer token.

        Safe to call from multiple coroutines at once: only the first caller
        actually hits the network, the rest just pick up the token it set.
        """
        async with self._login_lock:
            if self._token is None:
                await self._async_do_login()

    async def _relogin_after_401(self, stale_token: str | None) -> None:
        """Re-login, unless another concurrent caller already refreshed the token."""
        async with self._login_lock:
            if self._token == stale_token:
                self._token = None
                await self._async_do_login()

    async def _async_do_login(self) -> None:
        try:
            resp = await self._session.post(
                f"{API_BASE_URL}/parent/login",
                json={
                    "email": self._email,
                    "password": self._password,
                    "language_key": "en",
                },
                timeout=_TIMEOUT,
            )
        except ClientError as err:
            raise AbacusMentalMathError(f"Login request failed: {err}") from err

        if resp.status in (401, 403, 422):
            raise AbacusMentalMathAuthError("Email or password rejected")
        if resp.status != 200:
            raise AbacusMentalMathError(f"Login returned HTTP {resp.status}")

        body = await resp.json()
        token = body.get("access_token")
        if not token:
            raise AbacusMentalMathAuthError("Login succeeded but no access_token was returned")
        self._token = token

    async def _get(self, path: str, *, retry: bool = True) -> dict[str, Any]:
        if self._token is None:
            await self.async_login()

        token_used = self._token
        try:
            resp = await self._session.get(
                f"{API_BASE_URL}{path}",
                headers={"authorization": f"Bearer {token_used}"},
                timeout=_TIMEOUT,
            )
        except ClientError as err:
            raise AbacusMentalMathError(f"Request to {path} failed: {err}") from err

        if resp.status in (401, 403):
            if not retry:
                raise AbacusMentalMathAuthError(f"Rejected by {path} after re-login")
            await self._relogin_after_401(token_used)
            return await self._get(path, retry=False)
        if resp.status != 200:
            raise AbacusMentalMathError(f"{path} returned HTTP {resp.status}")

        return await resp.json()

    async def async_list_students(self) -> list[Student]:
        """Return every child listed under this parent account."""
        body = await self._get("/parent/students")
        return [
            Student(id=row["id"], first_name=row["first_name"], last_name=row["last_name"])
            for row in body.get("data", [])
        ]

    async def async_get_student_stats(self, student: Student) -> StudentStats:
        """Fetch profile + today/yesterday/week/month unit totals for one child."""
        profile = (await self._get(f"/parent/{student.id}/profile")).get("data", {})
        day = await self._get(f"/parent/{student.id}/profile/units-finished/day/0")
        yesterday = await self._get(f"/parent/{student.id}/profile/units-finished/day/1")
        week = await self._get(f"/parent/{student.id}/profile/units-finished/week/0")
        month = await self._get(f"/parent/{student.id}/profile/units-finished/month/0")

        return StudentStats(
            student=student,
            username=profile.get("username"),
            coin_amount=profile.get("coin_amount", 0),
            diamond_amount=profile.get("diamond_amount", 0),
            last_active_at=_parse_timestamp(profile.get("last_active_at")),
            mode_type=profile.get("mode_type"),
            wins_daily=profile.get("wins_daily", 0),
            wins_weekly=profile.get("wins_weekly", 0),
            wins_monthly=profile.get("wins_monthly", 0),
            units_today=_sum_amount(day),
            units_yesterday=_sum_amount(yesterday),
            units_this_week=_sum_amount(week),
            units_this_month=_sum_amount(month),
            week_series=week.get("data", []),
            month_series=month.get("data", []),
        )
