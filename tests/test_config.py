import pytest

from src.core.config import Settings


def test_config_fails_without_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test that the application aggressively crashes if no LLM keys are found.
    We patch the class attributes directly because they are evaluated at import time.
    """
    # 1. Arrange: Force the class attributes to None
    monkeypatch.setattr(Settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(Settings, "GEMINI_API_KEY", None)
    monkeypatch.setattr(Settings, "AZURE_OPENAI_API_KEY", None)

    # 2. Act & Assert: Verify that calling validation raises a ValueError
    with pytest.raises(ValueError) as exc_info:
        Settings.validate_core_settings()

    # 3. Assert: Check that the error message is exactly what we expect
    assert "[FATAL]" in str(exc_info.value)
    assert "You must provide credentials" in str(exc_info.value)


def test_config_detects_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the active provider toggles correctly."""
    # 1. Arrange: Simulate only having a Gemini key
    monkeypatch.setattr(Settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(Settings, "AZURE_OPENAI_API_KEY", None)
    monkeypatch.setattr(Settings, "GEMINI_API_KEY", "fake-test-key")

    # 2. Act
    Settings.validate_core_settings()

    # 3. Assert
    assert Settings.ACTIVE_LLM_PROVIDER == "gemini"
