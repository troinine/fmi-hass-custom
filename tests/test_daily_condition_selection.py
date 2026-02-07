"""Test daily weather condition selection logic."""
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest

# Mock all Home Assistant and external dependencies before importing custom_components
sys.modules["homeassistant"] = MagicMock()
sys.modules["homeassistant.const"] = MagicMock()
sys.modules["homeassistant.const"].SUN_EVENT_SUNSET = "sunset"
sys.modules["homeassistant.const"].SUN_EVENT_SUNRISE = "sunrise"
sys.modules["homeassistant.core"] = MagicMock()
sys.modules["homeassistant.helpers"] = MagicMock()
sys.modules["homeassistant.helpers.sun"] = MagicMock()
sys.modules["homeassistant.helpers.typing"] = MagicMock()
sys.modules["homeassistant.exceptions"] = MagicMock()
sys.modules["homeassistant.helpers.aiohttp_client"] = MagicMock()
sys.modules["homeassistant.helpers.update_coordinator"] = MagicMock()
sys.modules["fmi_weather_client"] = MagicMock()
sys.modules["fmi_weather_client.models"] = MagicMock()
sys.modules["fmi_weather_client.errors"] = MagicMock()
sys.modules["async_timeout"] = MagicMock()
sys.modules["geopy"] = MagicMock()
sys.modules["geopy.distance"] = MagicMock()
sys.modules["geopy.geocoders"] = MagicMock()
sys.modules["geopy.exc"] = MagicMock()

from custom_components.fmi import utils


def test_safety_override_lightning():
    """Test that 1 hour of lightning overrides all other conditions."""
    conditions = [
        (datetime(2024, 1, 15, 8, 0, tzinfo=timezone.utc), 'cloudy'),
        (datetime(2024, 1, 15, 9, 0, tzinfo=timezone.utc), 'cloudy'),
        (datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc), 'lightning'),
        (datetime(2024, 1, 15, 11, 0, tzinfo=timezone.utc), 'cloudy'),
        (datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc), 'cloudy'),
        (datetime(2024, 1, 15, 13, 0, tzinfo=timezone.utc), 'cloudy'),
    ]
    
    result = utils.select_daily_condition(conditions)
    assert result == 'lightning'


def test_precipitation_threshold():
    """Test that 3 hours of rain meets precipitation threshold."""
    conditions = [
        (datetime(2024, 1, 15, 8, 0, tzinfo=timezone.utc), 'cloudy'),
        (datetime(2024, 1, 15, 9, 0, tzinfo=timezone.utc), 'rainy'),
        (datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc), 'rainy'),
        (datetime(2024, 1, 15, 11, 0, tzinfo=timezone.utc), 'rainy'),
        (datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc), 'cloudy'),
        (datetime(2024, 1, 15, 13, 0, tzinfo=timezone.utc), 'cloudy'),
    ]
    
    result = utils.select_daily_condition(conditions)
    assert result == 'rainy'


def test_below_threshold_fallback():
    """Test that 2 hours of rain (below threshold) falls back to most common."""
    conditions = [
        (datetime(2024, 1, 15, 8, 0, tzinfo=timezone.utc), 'cloudy'),
        (datetime(2024, 1, 15, 9, 0, tzinfo=timezone.utc), 'cloudy'),
        (datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc), 'rainy'),
        (datetime(2024, 1, 15, 11, 0, tzinfo=timezone.utc), 'rainy'),
        (datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc), 'cloudy'),
        (datetime(2024, 1, 15, 13, 0, tzinfo=timezone.utc), 'cloudy'),
    ]
    
    result = utils.select_daily_condition(conditions)
    # Should be 'cloudy' (most common during daytime hours)
    assert result == 'cloudy'


def test_sunny_preference():
    """Test that clear-night is converted to sunny for daily forecasts."""
    conditions = [
        (datetime(2024, 1, 15, 8, 0, tzinfo=timezone.utc), 'clear-night'),
        (datetime(2024, 1, 15, 9, 0, tzinfo=timezone.utc), 'clear-night'),
        (datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc), 'clear-night'),
        (datetime(2024, 1, 15, 11, 0, tzinfo=timezone.utc), 'clear-night'),
        (datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc), 'clear-night'),
    ]
    
    result = utils.select_daily_condition(conditions)
    # clear-night should be normalized to sunny
    assert result == 'sunny'


def test_severity_priority():
    """Test that lightning beats pouring rain in safety override."""
    conditions = [
        (datetime(2024, 1, 15, 8, 0, tzinfo=timezone.utc), 'pouring'),
        (datetime(2024, 1, 15, 9, 0, tzinfo=timezone.utc), 'pouring'),
        (datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc), 'pouring'),
        (datetime(2024, 1, 15, 11, 0, tzinfo=timezone.utc), 'lightning'),
        (datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc), 'pouring'),
        (datetime(2024, 1, 15, 13, 0, tzinfo=timezone.utc), 'pouring'),
    ]
    
    result = utils.select_daily_condition(conditions)
    # Lightning (severity 1) should override pouring (severity 2)
    assert result == 'lightning'
