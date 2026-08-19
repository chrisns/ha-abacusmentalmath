"""Shared pytest fixtures — pulls in Home Assistant's own test harness."""
import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let hass load custom_components/abacusmentalmath during tests."""
    yield
