from __future__ import annotations

import json
from json import JSONDecodeError
from urllib.error import URLError
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


class LocalNavigationClient:
    def navigate_to(self, target: NavigationTarget) -> Observation:
        return Observation(
            source="navigation",
            success=True,
            reason="arrived",
            data={"point": target.point, "mode": "local_adapter"},
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
        except JSONDecodeError as exc:
            return Observation(
                source="navigation",
                success=False,
                reason="navigation_response_invalid_json",
                data={"error": str(exc), "point": target.point},
            )
        except (TimeoutError, URLError, OSError) as exc:
            return Observation(
                source="navigation",
                success=False,
                reason="navigation_request_failed",
                data={"error": type(exc).__name__, "detail": str(exc), "point": target.point},
            )

        if not isinstance(body, dict):
            return Observation(
                source="navigation",
                success=False,
                reason="navigation_response_invalid_schema",
                data={"point": target.point, "response_type": type(body).__name__},
            )
        if "success" not in body:
            return Observation(
                source="navigation",
                success=False,
                reason="navigation_response_missing_success",
                data={"point": target.point, "response": body},
            )

        return Observation(
            source="navigation",
            success=bool(body.get("success")),
            reason=str(body.get("reason", "unknown")),
            data=body,
        )
