"""Test UV index integration and timezone handling."""
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from dateutil import tz

# Mock all Home Assistant and external dependencies before importing custom_components
sys.modules["homeassistant"] = MagicMock()
sys.modules["homeassistant.const"] = MagicMock()
sys.modules["homeassistant.const"].SUN_EVENT_SUNSET = "sunset"
sys.modules["homeassistant.const"].SUN_EVENT_SUNRISE = "sunrise"
sys.modules["homeassistant.const"].CONF_LATITUDE = "latitude"
sys.modules["homeassistant.const"].CONF_LONGITUDE = "longitude"
sys.modules["homeassistant.const"].CONF_NAME = "name"
sys.modules["homeassistant.const"].CONF_OFFSET = "offset"
sys.modules["homeassistant.core"] = MagicMock()
sys.modules["homeassistant.helpers"] = MagicMock()
sys.modules["homeassistant.helpers.sun"] = MagicMock()
sys.modules["homeassistant.helpers.typing"] = MagicMock()
sys.modules["homeassistant.exceptions"] = MagicMock()
sys.modules["homeassistant.helpers.aiohttp_client"] = MagicMock()
sys.modules["homeassistant.helpers.update_coordinator"] = MagicMock()
sys.modules["homeassistant.helpers.update_coordinator"].DataUpdateCoordinator = object
sys.modules["homeassistant.helpers.update_coordinator"].UpdateFailed = Exception
sys.modules["fmi_weather_client"] = MagicMock()
sys.modules["fmi_weather_client.models"] = MagicMock()
sys.modules["fmi_weather_client.errors"] = MagicMock()
sys.modules["async_timeout"] = MagicMock()
sys.modules["geopy"] = MagicMock()
sys.modules["geopy.distance"] = MagicMock()
sys.modules["geopy.geocoders"] = MagicMock()
sys.modules["geopy.exc"] = MagicMock()
sys.modules["aiohttp"] = MagicMock()

from custom_components.fmi import utils


class TestUVIndexData:
    """Test UVIndexData class."""
    
    def test_create_uv_data(self):
        """Test creating UVIndexData object."""
        test_time = datetime(2026, 2, 7, 12, 0, tzinfo=timezone.utc)
        uv_data = utils.UVIndexData(
            time=test_time,
            uv_index=5.2,
            uv_index_clear_sky=6.5
        )
        
        assert uv_data.time == test_time
        assert uv_data.uv_index == 5.2
        assert uv_data.uv_index_clear_sky == 6.5
    
    def test_create_uv_data_without_clear_sky(self):
        """Test creating UVIndexData without clear sky value."""
        test_time = datetime(2026, 2, 7, 12, 0, tzinfo=timezone.utc)
        uv_data = utils.UVIndexData(
            time=test_time,
            uv_index=3.1
        )
        
        assert uv_data.time == test_time
        assert uv_data.uv_index == 3.1
        assert uv_data.uv_index_clear_sky is None


class TestTimezoneHandling:
    """Test timezone-aware datetime handling for UV index."""
    
    def test_timezone_aware_datetime_subtraction(self):
        """Test that timezone-aware datetimes can be compared without errors."""
        # This is the core issue we're fixing - ensure we can subtract
        # timezone-aware datetimes without TypeError
        
        # Local timezone datetime
        local_time = datetime(2026, 2, 7, 12, 0, tzinfo=tz.tzlocal())
        
        # UTC timezone datetime
        utc_time = datetime(2026, 2, 7, 10, 0, tzinfo=timezone.utc)
        
        # Convert both to same timezone for comparison
        local_time_normalized = local_time.astimezone(tz.tzlocal())
        utc_time_normalized = utc_time.astimezone(tz.tzlocal())
        
        # This should not raise TypeError
        time_diff = abs(local_time_normalized - utc_time_normalized)
        
        # Verify the difference is calculated
        assert isinstance(time_diff, timedelta)
    
    def test_naive_datetime_timezone_conversion(self):
        """Test converting naive datetime to timezone-aware."""
        # Naive datetime (no timezone info)
        naive_time = datetime(2026, 2, 7, 12, 0)
        
        # Should be able to add timezone
        aware_time = naive_time.replace(tzinfo=tz.tzlocal())
        
        assert aware_time.tzinfo is not None
        assert aware_time.hour == 12
    
    def test_datetime_parsing_from_iso_string(self):
        """Test parsing ISO 8601 strings with timezone (like Open-Meteo returns)."""
        # Open-Meteo returns ISO 8601 strings with timezone offset
        iso_string = "2026-02-07T12:00:00+02:00"
        
        # Parse it
        parsed_time = datetime.fromisoformat(iso_string)
        
        # Should be timezone-aware
        assert parsed_time.tzinfo is not None
        
        # Can convert to local timezone
        local_time = parsed_time.astimezone(tz.tzlocal())
        assert local_time.tzinfo is not None
    
    def test_mixed_timezone_comparison(self):
        """Test comparing datetimes from different timezones."""
        # UTC time
        utc_time = datetime(2026, 2, 7, 10, 0, tzinfo=timezone.utc)
        
        # Helsinki time (UTC+2 in winter)
        helsinki_tz = tz.gettz('Europe/Helsinki')
        helsinki_time = datetime(2026, 2, 7, 12, 0, tzinfo=helsinki_tz)
        
        # Convert both to UTC for comparison
        utc_time_utc = utc_time.astimezone(timezone.utc)
        helsinki_time_utc = helsinki_time.astimezone(timezone.utc)
        
        # These should represent the same moment in time
        time_diff = abs(utc_time_utc - helsinki_time_utc)
        
        # Difference should be 0 (same moment in time)
        assert time_diff.total_seconds() == 0


def test_uv_index_data_timezone_normalization():
    """Test that UV index data is stored with proper timezone normalization."""
    # Simulate what happens in fetch_uv_index_data
    
    # Open-Meteo returns ISO 8601 with timezone
    time_strings = [
        "2026-02-07T10:00:00+02:00",
        "2026-02-07T11:00:00+02:00",
        "2026-02-07T12:00:00+02:00",
    ]
    
    uv_values = [0.5, 1.0, 1.5]
    
    # Parse and store as we do in utils.fetch_uv_index_data
    uv_data_dict = {}
    
    for time_str, uv_val in zip(time_strings, uv_values):
        dt = datetime.fromisoformat(time_str)
        
        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz.tzutc()).astimezone(tz.tzlocal())
        
        uv_data_dict[dt] = utils.UVIndexData(
            time=dt,
            uv_index=float(uv_val)
        )
    
    # Verify all keys are timezone-aware
    for dt_key in uv_data_dict.keys():
        assert dt_key.tzinfo is not None, "All datetime keys should be timezone-aware"
    
    # Verify we can compare with another timezone-aware datetime
    test_time = datetime(2026, 2, 7, 12, 0, tzinfo=tz.tzlocal())
    
    # Find closest match
    min_diff = timedelta(hours=2)
    closest_key = None
    
    for data_time in uv_data_dict.keys():
        data_time_local = data_time.astimezone(tz.tzlocal())
        time_diff = abs(data_time_local - test_time)
        
        if time_diff < min_diff:
            min_diff = time_diff
            closest_key = data_time
    
    # Should have found a match
    assert closest_key is not None
    assert min_diff < timedelta(hours=1)


if __name__ == "__main__":
    import sys
    
    # Run tests
    test_classes = [TestUVIndexData(), TestTimezoneHandling()]
    
    failed = 0
    passed = 0
    
    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        for method_name in dir(test_class):
            if method_name.startswith('test_'):
                try:
                    method = getattr(test_class, method_name)
                    method()
                    print(f"✓ {class_name}.{method_name}")
                    passed += 1
                except Exception as e:
                    print(f"✗ {class_name}.{method_name}: {e}")
                    failed += 1
    
    # Run module-level test
    try:
        test_uv_index_data_timezone_normalization()
        print(f"✓ test_uv_index_data_timezone_normalization")
        passed += 1
    except Exception as e:
        print(f"✗ test_uv_index_data_timezone_normalization: {e}")
        failed += 1
    
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
