import pytest

from agent.config import (
    AgentConfigurationError,
    get_gemini_api_key,
    get_model_name,
)


def test_model_name_has_default(
    monkeypatch,
):
    monkeypatch.delenv(
        "GEMINI_MODEL",
        raising=False,
    )

    assert (
        get_model_name()
        == "gemini-3.5-flash-lite"
    )


def test_model_name_can_be_configured(
    monkeypatch,
):
    monkeypatch.setenv(
        "GEMINI_MODEL",
        "custom-model",
    )

    assert (
        get_model_name()
        == "custom-model"
    )


def test_missing_api_key_raises_configuration_error(
    monkeypatch,
):
    monkeypatch.delenv(
        "GEMINI_API_KEY",
        raising=False,
    )

    with pytest.raises(
        AgentConfigurationError
    ):
        get_gemini_api_key()


def test_api_key_is_read_from_environment(
    monkeypatch,
):
    monkeypatch.setenv(
        "GEMINI_API_KEY",
        "test-key",
    )

    assert (
        get_gemini_api_key()
        == "test-key"
    )