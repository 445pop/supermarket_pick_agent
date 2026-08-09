import pytest

from supermarket_pick_agent.config import Settings


def test_settings_prefers_local_adapter_flag(monkeypatch):
    monkeypatch.setenv("USE_LOCAL_ADAPTERS", "false")
    monkeypatch.setenv("USE_MOCKS", "true")

    settings = Settings.from_env()

    assert settings.use_local_adapters is False


def test_settings_keeps_legacy_flag_compatible(monkeypatch):
    monkeypatch.delenv("USE_LOCAL_ADAPTERS", raising=False)
    monkeypatch.setenv("USE_MOCKS", "false")

    settings = Settings.from_env()

    assert settings.use_local_adapters is False


def test_remote_settings_require_service_values():
    settings = Settings(
        openai_api_key=None,
        openai_verifier_model="your-vlm-model",
        pi05_endpoint="",
        navigation_endpoint="",
        use_local_adapters=False,
        task_log_dir=None,
    )

    with pytest.raises(ValueError) as exc_info:
        settings.validate()

    message = str(exc_info.value)
    assert "OPENAI_API_KEY" in message
    assert "OPENAI_VERIFIER_MODEL" in message
    assert "PI05_ENDPOINT" in message
    assert "NAVIGATION_ENDPOINT" in message
