"""Tests for the FMI weather forecast functionality."""

import sys
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
import pytest
import math

# Create proper mock base classes to avoid metaclass conflicts
class MockCoordinatorEntityBase:
    """Mock base class for CoordinatorEntity."""
    def __init__(self, coordinator):
        self.coordinator = coordinator


class MockWeatherEntityBase:
    """Mock base class for WeatherEntity."""
    pass


class MockDeviceEntryType:
    """Mock DeviceEntryType enum."""
    SERVICE = "service"


# Mock sun helper functions
def mock_get_astral_event_date(hass, event_type, date_val):
    """Mock function for astral event date."""
    from datetime import time
    from dateutil import tz
    # Return a mock sunset/sunrise time
    if event_type == "sunset":
        return datetime.combine(date_val, time(hour=18, minute=0)).replace(tzinfo=tz.tzlocal())
    else:  # sunrise
        return datetime.combine(date_val, time(hour=6, minute=0)).replace(tzinfo=tz.tzlocal())


# Mock Home Assistant modules before importing custom_components
sys.modules["homeassistant"] = MagicMock()
sys.modules["homeassistant.const"] = MagicMock()
sys.modules["homeassistant.const"].SUN_EVENT_SUNSET = "sunset"
sys.modules["homeassistant.const"].SUN_EVENT_SUNRISE = "sunrise"
sys.modules["homeassistant.core"] = MagicMock()
sys.modules["homeassistant.core"].callback = lambda func: func
sys.modules["homeassistant.helpers"] = MagicMock()
sys.modules["homeassistant.helpers.typing"] = MagicMock()
sys.modules["homeassistant.helpers.sun"] = MagicMock()
sys.modules["homeassistant.helpers.sun"].get_astral_event_date = mock_get_astral_event_date
sys.modules["homeassistant.exceptions"] = MagicMock()
sys.modules["homeassistant.helpers.aiohttp_client"] = MagicMock()
sys.modules["homeassistant.helpers.update_coordinator"] = MagicMock()
sys.modules["homeassistant.helpers.update_coordinator"].CoordinatorEntity = MockCoordinatorEntityBase
sys.modules["homeassistant.helpers.device_registry"] = MagicMock()
sys.modules["homeassistant.helpers.device_registry"].DeviceEntryType = MockDeviceEntryType
sys.modules["homeassistant.components"] = MagicMock()
sys.modules["homeassistant.components.weather"] = MagicMock()
sys.modules["homeassistant.components.weather"].WeatherEntity = MockWeatherEntityBase
sys.modules["homeassistant.components.weather"].Forecast = dict
sys.modules["homeassistant.components.weather.const"] = MagicMock()

# Set up weather entity feature mock
class MockWeatherEntityFeature:
    FORECAST_HOURLY = 1
    FORECAST_DAILY = 2


sys.modules["homeassistant.components.weather.const"].WeatherEntityFeature = MockWeatherEntityFeature

# Set up mock attributes
ATTR_FORECAST_CONDITION = "condition"
ATTR_FORECAST_NATIVE_PRECIPITATION = "precipitation"
ATTR_FORECAST_NATIVE_TEMP = "temperature"
ATTR_FORECAST_TIME = "datetime"
ATTR_FORECAST_WIND_BEARING = "wind_bearing"
ATTR_FORECAST_NATIVE_WIND_SPEED = "wind_speed"
ATTR_FORECAST_NATIVE_TEMP_LOW = "templow"
ATTR_FORECAST_CLOUD_COVERAGE = "cloud_coverage"
ATTR_WEATHER_HUMIDITY = "humidity"
ATTR_WEATHER_PRESSURE = "pressure"

sys.modules["homeassistant.components.weather"].ATTR_FORECAST_CONDITION = ATTR_FORECAST_CONDITION
sys.modules["homeassistant.components.weather"].ATTR_FORECAST_NATIVE_PRECIPITATION = ATTR_FORECAST_NATIVE_PRECIPITATION
sys.modules["homeassistant.components.weather"].ATTR_FORECAST_NATIVE_TEMP = ATTR_FORECAST_NATIVE_TEMP
sys.modules["homeassistant.components.weather"].ATTR_FORECAST_TIME = ATTR_FORECAST_TIME
sys.modules["homeassistant.components.weather"].ATTR_FORECAST_WIND_BEARING = ATTR_FORECAST_WIND_BEARING
sys.modules["homeassistant.components.weather"].ATTR_FORECAST_NATIVE_WIND_SPEED = ATTR_FORECAST_NATIVE_WIND_SPEED
sys.modules["homeassistant.components.weather"].ATTR_FORECAST_NATIVE_TEMP_LOW = ATTR_FORECAST_NATIVE_TEMP_LOW
sys.modules["homeassistant.components.weather"].ATTR_FORECAST_CLOUD_COVERAGE = ATTR_FORECAST_CLOUD_COVERAGE
sys.modules["homeassistant.components.weather.const"].ATTR_WEATHER_HUMIDITY = ATTR_WEATHER_HUMIDITY
sys.modules["homeassistant.components.weather.const"].ATTR_WEATHER_PRESSURE = ATTR_WEATHER_PRESSURE

from custom_components.fmi import const
from custom_components.fmi.weather import FMIWeatherEntity


class MockValue:
    """Mock class for FMI value objects."""
    def __init__(self, value, unit=None):
        self.value = value
        self.unit = unit


class MockWeatherData:
    """Mock class for FMI weather data."""
    def __init__(self, time, symbol=1, temperature=15.0, humidity=70.0, 
                 precipitation_amount=0.0, wind_speed=5.0, wind_direction=180.0,
                 cloud_cover=50.0, pressure=1013.0, dew_point=10.0,
                 wind_gust=None, wind_max=None):
        self.time = time
        self.symbol = MockValue(symbol)
        self.temperature = MockValue(temperature, "°C")
        self.humidity = MockValue(humidity, "%")
        self.precipitation_amount = MockValue(precipitation_amount, "mm")
        self.wind_speed = MockValue(wind_speed, "m/s")
        self.wind_direction = MockValue(wind_direction, "°")
        self.cloud_cover = MockValue(cloud_cover, "%")
        self.pressure = MockValue(pressure, "hPa")
        self.dew_point = MockValue(dew_point, "°C")
        self.wind_gust = MockValue(wind_gust, "m/s") if wind_gust is not None else None
        self.wind_max = MockValue(wind_max, "m/s") if wind_max is not None else None


class MockWeather:
    """Mock class for FMI weather object."""
    def __init__(self, data, place="Helsinki"):
        self.data = data
        self.place = place


class MockForecast:
    """Mock class for FMI forecast object."""
    def __init__(self, forecasts):
        self.forecasts = forecasts


class MockCoordinator:
    """Mock coordinator for testing."""
    def __init__(self, weather_data, forecast_data):
        self.unique_id = "60.0_25.0"
        self.last_update_success = True
        self._weather = weather_data
        self._forecast = forecast_data
        self._listeners = []
        self.hass = MagicMock()  # Add hass attribute
        
    def get_observation(self):
        return None
        
    def get_weather(self):
        return self._weather
        
    def get_forecasts(self):
        if self._forecast is None:
            return []
        return self._forecast.forecasts
    
    def async_add_listener(self, callback):
        self._listeners.append(callback)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    return hass


@pytest.fixture
def mock_weather_data():
    """Create mock current weather data."""
    current_time = datetime.now(timezone.utc)
    return MockWeather(
        MockWeatherData(
            time=current_time,
            symbol=2,
            temperature=18.5,
            humidity=65.0,
            precipitation_amount=0.1,
            wind_speed=7.2,
            wind_direction=225.0,
            cloud_cover=40.0,
            pressure=1015.0,
            dew_point=12.0,
            wind_gust=10.5
        )
    )


@pytest.fixture
def mock_forecast_data():
    """Create mock forecast data for multiple hours."""
    from datetime import timedelta
    base_time = datetime.now(timezone.utc)
    forecasts = []
    
    # Create 24 hours of forecast data
    for hour in range(24):
        # Use timedelta to properly increment time
        time_offset = base_time + timedelta(hours=hour)
        
        # Simulate temperature variation throughout the day
        temp = 15.0 + 10 * math.sin(hour * math.pi / 12)
        
        forecasts.append(
            MockWeatherData(
                time=time_offset,
                symbol=1 if hour % 3 == 0 else 2,
                temperature=temp,
                humidity=60.0 + hour,
                precipitation_amount=0.0 if hour % 4 else 0.5,
                wind_speed=5.0 + hour * 0.5,
                wind_direction=(180.0 + hour * 10) % 360,  # Keep within 0-360 range
                cloud_cover=30.0 + hour * 2,
                pressure=1013.0 - hour * 0.5
            )
        )
    
    return MockForecast(forecasts)


@pytest.fixture
def mock_coordinator(mock_weather_data, mock_forecast_data):
    """Create a mock coordinator."""
    return MockCoordinator(mock_weather_data, mock_forecast_data)


class TestWeatherForecastData:
    """Test class for weather forecast data."""
    
    def test_forecast_hourly_returns_data(self, mock_coordinator):
        """Test that hourly forecast returns data."""
        entity = FMIWeatherEntity("Test", mock_coordinator)
        
        # Get hourly forecast
        # Note: This is a sync test, so we'll call the internal _forecast method
        forecast = entity._forecast(daily_mode=False)
        
        assert forecast is not None
        assert len(forecast) > 0
        assert isinstance(forecast, list)
    
    def test_forecast_daily_returns_data(self, mock_coordinator):
        """Test that daily forecast returns data."""
        entity = FMIWeatherEntity("Test", mock_coordinator)
        
        # Get daily forecast
        forecast = entity._forecast(daily_mode=True)
        
        assert forecast is not None
        assert len(forecast) > 0
        assert isinstance(forecast, list)
    
    def test_forecast_has_required_fields(self, mock_coordinator):
        """Test that forecast items have all required fields."""
        entity = FMIWeatherEntity("Test", mock_coordinator)
        forecast = entity._forecast(daily_mode=False)
        
        required_fields = [
            ATTR_FORECAST_TIME,
            ATTR_FORECAST_CONDITION,
            ATTR_FORECAST_NATIVE_TEMP,
            ATTR_FORECAST_NATIVE_PRECIPITATION,
            ATTR_FORECAST_NATIVE_WIND_SPEED,
            ATTR_FORECAST_WIND_BEARING,
            ATTR_WEATHER_PRESSURE,
            ATTR_WEATHER_HUMIDITY,
            ATTR_FORECAST_CLOUD_COVERAGE
        ]
        
        for item in forecast:
            for field in required_fields:
                assert field in item, f"Field {field} missing from forecast item"
    
    def test_forecast_temperature_values(self, mock_coordinator):
        """Test that temperature values are correctly extracted."""
        entity = FMIWeatherEntity("Test", mock_coordinator)
        forecast = entity._forecast(daily_mode=False)
        
        for item in forecast:
            temp = item[ATTR_FORECAST_NATIVE_TEMP]
            assert temp is not None
            assert isinstance(temp, (int, float))
            assert -50 <= temp <= 50, "Temperature out of reasonable range"
    
    def test_forecast_precipitation_values(self, mock_coordinator):
        """Test that precipitation values are valid."""
        entity = FMIWeatherEntity("Test", mock_coordinator)
        forecast = entity._forecast(daily_mode=False)
        
        for item in forecast:
            precip = item[ATTR_FORECAST_NATIVE_PRECIPITATION]
            if precip is not None:
                assert isinstance(precip, (int, float))
                assert precip >= 0, "Precipitation cannot be negative"
    
    def test_forecast_wind_speed_values(self, mock_coordinator):
        """Test that wind speed values are valid."""
        entity = FMIWeatherEntity("Test", mock_coordinator)
        forecast = entity._forecast(daily_mode=False)
        
        for item in forecast:
            wind_speed = item[ATTR_FORECAST_NATIVE_WIND_SPEED]
            if wind_speed is not None:
                assert isinstance(wind_speed, (int, float))
                assert wind_speed >= 0, "Wind speed cannot be negative"
    
    def test_forecast_wind_bearing_values(self, mock_coordinator):
        """Test that wind bearing values are valid."""
        entity = FMIWeatherEntity("Test", mock_coordinator)
        forecast = entity._forecast(daily_mode=False)
        
        for item in forecast:
            bearing = item[ATTR_FORECAST_WIND_BEARING]
            if bearing is not None:
                assert isinstance(bearing, (int, float))
                assert 0 <= bearing <= 360, "Wind bearing out of valid range"
    
    def test_forecast_humidity_values(self, mock_coordinator):
        """Test that humidity values are valid."""
        entity = FMIWeatherEntity("Test", mock_coordinator)
        forecast = entity._forecast(daily_mode=False)
        
        for item in forecast:
            humidity = item[ATTR_WEATHER_HUMIDITY]
            if humidity is not None:
                assert isinstance(humidity, (int, float))
                assert 0 <= humidity <= 100, "Humidity out of valid range"
    
    def test_forecast_pressure_values(self, mock_coordinator):
        """Test that pressure values are valid."""
        entity = FMIWeatherEntity("Test", mock_coordinator)
        forecast = entity._forecast(daily_mode=False)
        
        for item in forecast:
            pressure = item[ATTR_WEATHER_PRESSURE]
            if pressure is not None:
                assert isinstance(pressure, (int, float))
                assert 900 <= pressure <= 1100, "Pressure out of reasonable range"
    
    def test_forecast_cloud_coverage_values(self, mock_coordinator):
        """Test that cloud coverage values are valid."""
        entity = FMIWeatherEntity("Test", mock_coordinator)
        forecast = entity._forecast(daily_mode=False)
        
        for item in forecast:
            clouds = item[ATTR_FORECAST_CLOUD_COVERAGE]
            if clouds is not None:
                assert isinstance(clouds, (int, float))
                assert 0 <= clouds <= 100, "Cloud coverage out of valid range"
    
    def test_forecast_time_format(self, mock_coordinator):
        """Test that forecast time is in ISO format."""
        entity = FMIWeatherEntity("Test", mock_coordinator)
        forecast = entity._forecast(daily_mode=False)
        
        for item in forecast:
            time_str = item[ATTR_FORECAST_TIME]
            assert time_str is not None
            assert isinstance(time_str, str)
            # Should be able to parse ISO format
            try:
                datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            except ValueError:
                pytest.fail(f"Time '{time_str}' is not in valid ISO format")
    
    def test_daily_forecast_aggregates_temperatures(self, mock_coordinator):
        """Test that daily forecast correctly aggregates high/low temperatures."""
        entity = FMIWeatherEntity("Test", mock_coordinator)
        forecast = entity._forecast(daily_mode=True)
        
        # Daily forecast should have temp_low set
        for item in forecast:
            assert ATTR_FORECAST_NATIVE_TEMP_LOW in item
            temp_high = item[ATTR_FORECAST_NATIVE_TEMP]
            temp_low = item[ATTR_FORECAST_NATIVE_TEMP_LOW]
            
            if temp_high is not None and temp_low is not None:
                assert temp_high >= temp_low, "High temp should be >= low temp"
    
    def test_hourly_forecast_no_temp_low(self, mock_coordinator):
        """Test that hourly forecast does not set temp_low."""
        entity = FMIWeatherEntity("Test", mock_coordinator)
        forecast = entity._forecast(daily_mode=False)
        
        for item in forecast:
            temp_low = item.get(ATTR_FORECAST_NATIVE_TEMP_LOW)
            assert temp_low is None, "Hourly forecast should not have temp_low"
    
    def test_empty_forecast_handling(self):
        """Test handling of empty forecast data."""
        empty_forecast = MockForecast([])
        coordinator = MockCoordinator(None, empty_forecast)
        
        entity = FMIWeatherEntity("Test", coordinator)
        forecast = entity._forecast(daily_mode=False)
        
        assert forecast is not None
        assert len(forecast) == 0
    
    def test_none_values_handling(self):
        """Test handling of None values in forecast data."""
        base_time = datetime.now(timezone.utc)
        
        # Create forecast with None values
        forecast_data = MockForecast([
            MockWeatherData(
                time=base_time,
                symbol=2,  # Use symbol 2 to avoid sun event calculation
                temperature=None,  # None value
                humidity=None,
                precipitation_amount=None,
                wind_speed=None,
                wind_direction=None,
                cloud_cover=None,
                pressure=None
            )
        ])
        
        coordinator = MockCoordinator(
            MockWeather(
                MockWeatherData(
                    time=base_time,
                    symbol=2,
                    temperature=15.0
                )
            ),
            forecast_data
        )
        
        entity = FMIWeatherEntity("Test", coordinator)
        forecast = entity._forecast(daily_mode=False)
        
        # Should still return forecast but with None values
        assert len(forecast) == 1
        assert forecast[0][ATTR_FORECAST_NATIVE_TEMP] is None
    
    def test_nan_values_handling(self):
        """Test handling of NaN values in forecast data."""
        base_time = datetime.now(timezone.utc)
        
        # Create forecast with NaN values
        forecast_data = MockForecast([
            MockWeatherData(
                time=base_time,
                symbol=2,  # Use symbol 2 to avoid sun event calculation
                temperature=float('nan'),
                humidity=70.0,
                precipitation_amount=0.0,
                wind_speed=5.0,
                wind_direction=180.0,
                cloud_cover=50.0,
                pressure=1013.0
            )
        ])
        
        coordinator = MockCoordinator(
            MockWeather(
                MockWeatherData(
                    time=base_time,
                    symbol=2,
                    temperature=15.0
                )
            ),
            forecast_data
        )
        
        entity = FMIWeatherEntity("Test", coordinator)
        forecast = entity._forecast(daily_mode=False)
        
        # NaN should be treated as None
        assert len(forecast) == 1
        assert forecast[0][ATTR_FORECAST_NATIVE_TEMP] is None
    
    def test_forecast_condition_mapping(self, mock_coordinator):
        """Test that weather symbols are correctly mapped to conditions."""
        entity = FMIWeatherEntity("Test", coordinator=mock_coordinator)
        forecast = entity._forecast(daily_mode=False)
        
        for item in forecast:
            condition = item[ATTR_FORECAST_CONDITION]
            assert condition is not None
            # Should be one of the valid Home Assistant weather conditions
            valid_conditions = [
                "clear-night", "sunny", "partlycloudy", "cloudy",
                "rainy", "pouring", "snowy", "snowy-rainy",
                "lightning", "lightning-rainy", "fog"
            ]
            assert condition in valid_conditions, f"Invalid condition: {condition}"
    
    def test_daily_forecast_has_fewer_items_than_hourly(self, mock_coordinator):
        """Test that daily forecast has fewer items than hourly forecast."""
        entity = FMIWeatherEntity("Test", mock_coordinator)
        
        hourly = entity._forecast(daily_mode=False)
        daily = entity._forecast(daily_mode=True)
        
        # Daily should aggregate hours, so should have fewer items
        assert len(daily) <= len(hourly)
    
    def test_forecast_chronological_order(self, mock_coordinator):
        """Test that forecast items are in chronological order."""
        entity = FMIWeatherEntity("Test", mock_coordinator)
        forecast = entity._forecast(daily_mode=False)
        
        if len(forecast) > 1:
            for i in range(len(forecast) - 1):
                time1 = datetime.fromisoformat(
                    forecast[i][ATTR_FORECAST_TIME].replace('Z', '+00:00')
                )
                time2 = datetime.fromisoformat(
                    forecast[i + 1][ATTR_FORECAST_TIME].replace('Z', '+00:00')
                )
                assert time1 <= time2, "Forecast should be in chronological order"


class TestWeatherForecastEdgeCases:
    """Test edge cases for weather forecast."""
    
    def test_forecast_with_missing_coordinator_data(self):
        """Test forecast when coordinator has no data."""
        coordinator = MockCoordinator(None, None)
        entity = FMIWeatherEntity("Test", coordinator)
        
        forecast = entity._forecast(daily_mode=False)
        assert forecast == []
    
    def test_forecast_after_coordinator_update_failure(self):
        """Test forecast behavior after coordinator update failure."""
        coordinator = MockCoordinator(None, None)
        coordinator.last_update_success = False
        
        entity = FMIWeatherEntity("Test", coordinator)
        forecast = entity._forecast(daily_mode=False)
        
        assert forecast == []
    
    def test_multiple_days_in_daily_forecast(self):
        """Test that daily forecast correctly handles multiple days."""
        from datetime import timedelta
        base_time = datetime.now(timezone.utc)
        forecasts = []
        
        # Create 3 days of hourly data (72 hours)
        for hour in range(72):
            time_offset = base_time + timedelta(hours=hour)
            
            forecasts.append(
                MockWeatherData(
                    time=time_offset,
                    symbol=2,  # Use symbol 2 instead of 1 to avoid sun event calculation
                    temperature=15.0 + 5 * math.sin(hour * math.pi / 12),
                    humidity=60.0,
                    precipitation_amount=0.0,
                    wind_speed=5.0,
                    wind_direction=180.0,
                    cloud_cover=30.0,
                    pressure=1013.0
                )
            )
        
        forecast_data = MockForecast(forecasts)
        weather_data = MockWeather(forecasts[0])
        coordinator = MockCoordinator(weather_data, forecast_data)
        
        entity = FMIWeatherEntity("Test", coordinator)
        daily_forecast = entity._forecast(daily_mode=True)
        
        # Should have approximately 3 days
        assert 2 <= len(daily_forecast) <= 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
