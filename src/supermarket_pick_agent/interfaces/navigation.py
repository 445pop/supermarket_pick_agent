from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from ..models import Observation


@dataclass(frozen=True)
class NavigationTarget:
    point: str


class NavigationClient(Protocol):
    def navigate_to(self, target: NavigationTarget) -> Observation:
        """Move robot base/platform to a named point and return navigation observation."""


class MockNavigationClient:
    def navigate_to(self, target: NavigationTarget) -> Observation:
        return Observation(
            source="navigation",
            success=True,
            reason="arrived",
            data={"point": target.point, "mode": "mock"},
        )


class HttpNavigationClient:
    def __init__(self, endpoint: str, timeout_s: float = 20.0) -> None:
        self.endpoint = endpoint
        self.timeout_s = timeout_s

    def navigate_to(self, target: NavigationTarget) -> Observation:
        payload = json.dumps({"point": target.point}).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                body = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            return Observation(
                source="navigation",
                success=False,
                reason="navigation_request_failed",
                data={"error": str(exc), "point": target.point},
            )

        return Observation(
            source="navigation",
            success=bool(body.get("success")),
            reason=str(body.get("reason", "unknown")),
            data=body,
        )

