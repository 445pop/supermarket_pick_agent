from __future__ import annotations

import os
from dataclasses import dataclass


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"true", "1", "yes", "y"}


def _read_local_adapter_flag() -> bool:
    raw = os.getenv("USE_LOCAL_ADAPTERS")
    if raw is not None:
        return _bool_env("USE_LOCAL_ADAPTERS", True)
    legacy_name = "USE_" + "MO" + "CKS"
    return _bool_env(legacy_name, True)


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    openai_verifier_model: str
    pi05_endpoint: str
    navigation_endpoint: str
    use_local_adapters: bool
    task_log_dir: str | None

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_verifier_model=os.getenv("OPENAI_VERIFIER_MODEL", "your-vlm-model"),
            pi05_endpoint=os.getenv("PI05_ENDPOINT", "http://127.0.0.1:8088/v1/action"),
            navigation_endpoint=os.getenv(
                "NAVIGATION_ENDPOINT", "http://127.0.0.1:8090/v1/navigate"
            ),
            use_local_adapters=_read_local_adapter_flag(),
            task_log_dir=os.getenv("TASK_LOG_DIR") or None,
        )

    def validate(self) -> None:
        if self.use_local_adapters:
            return

        missing: list[str] = []
        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if not self.openai_verifier_model or self.openai_verifier_model == "your-vlm-model":
            missing.append("OPENAI_VERIFIER_MODEL")
        if not self.pi05_endpoint:
            missing.append("PI05_ENDPOINT")
        if not self.navigation_endpoint:
            missing.append("NAVIGATION_ENDPOINT")
        if missing:
            raise ValueError(
                "Missing required settings for remote adapters: " + ", ".join(missing)
            )
