from __future__ import annotations

import os
from dataclasses import dataclass


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"true", "1", "yes", "y"}


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    openai_verifier_model: str
    pi05_endpoint: str
    navigation_endpoint: str
    use_mocks: bool

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_verifier_model=os.getenv("OPENAI_VERIFIER_MODEL", "gpt-5.5"),
            pi05_endpoint=os.getenv("PI05_ENDPOINT", "http://127.0.0.1:8088/v1/action"),
            navigation_endpoint=os.getenv(
                "NAVIGATION_ENDPOINT", "http://127.0.0.1:8090/v1/navigate"
            ),
            use_mocks=_bool_env("USE_MOCKS", True),
        )

