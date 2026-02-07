"""Tests to verify daily forecast aggregation works correctly."""

import sys
from unittest.mock import MagicMock
from datetime import datetime, timedelta
import pytest

# Mock Home Assistant modules (same setup as test_weather_forecast.py)
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


def mock_get_astral_event_date(hass, event_type, date_val):
    """Mock function for astral event date."""
    from datetime import time
    from dateutil import tz
    if event_type == "sunset":
        return datetime.combine(date_val, time(hour=18, minute=0)).replace(tzinfo=tz.tzlocal())
    else:  # sunrise
        return datetime.combine(date_val, time(hour=6, minute=0)).replace(tzinfo=tz.tzlocal())


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
from dateutil import tz


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
        self.hass = MagicMock()
        
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


class TestDailyForecastAggregation:
    """Test class to verify daily forecast aggregation works correctly."""
    
    def test_daily_forecast_sums_precipitation(self):
        """Test that daily forecast correctly sums precipitation across the day."""
        base_time = datetime.now(tz.tzlocal()).replace(hour=0, minute=0, second=0, microsecond=0)
        forecasts = []
        
        # Create a single day with varying precipitation:
        # First hour: 0.0mm (dry)
        # Hours 6-12: 5.0mm each (heavy rain in middle of day)
        # Rest: 0.0mm
        for hour in range(24):
            precip = 5.0 if 6 <= hour <= 12 else 0.0
            forecasts.append(
                MockWeatherData(
                    time=base_time + timedelta(hours=hour),
                    symbol=2,
                    temperature=15.0,
                    humidity=70.0,
                    precipitation_amount=precip,
                    wind_speed=5.0,
                    wind_direction=180.0,
                    cloud_cover=50.0,
                    pressure=1013.0
                )
            )
        
        forecast_data = MockForecast(forecasts)
        weather_data = MockWeather(forecasts[0])
        coordinator = MockCoordinator(weather_data, forecast_data)
        
        entity = FMIWeatherEntity("Test", coordinator)
        daily = entity._forecast(daily_mode=True)
        
        # Should sum all precipitation: 7 hours * 5.0mm = 35.0mm
        assert len(daily) >= 1
        precip = daily[0][ATTR_FORECAST_NATIVE_PRECIPITATION]
        expected_total_precip = 35.0  # 7 hours * 5.0mm
        
        assert precip == pytest.approx(expected_total_precip), \
            f"Daily precipitation should be {expected_total_precip}mm (sum), got {precip}mm"
    
    def test_daily_forecast_uses_max_wind_speed(self):
        """Test that daily forecast uses maximum wind speed across the day."""
        base_time = datetime.now(tz.tzlocal()).replace(hour=0, minute=0, second=0, microsecond=0)
        forecasts = []
        
        # Create a single day with varying wind speed:
        # First hour: 5.0 m/s (calm at midnight)
        # Hour 12: 25.0 m/s (strong wind at noon)
        # Rest: 10.0 m/s
        for hour in range(24):
            if hour == 0:
                wind = 5.0
            elif hour == 12:
                wind = 25.0  # Strong wind at noon
            else:
                wind = 10.0
                
            forecasts.append(
                MockWeatherData(
                    time=base_time + timedelta(hours=hour),
                    symbol=2,
                    temperature=15.0,
                    humidity=70.0,
                    precipitation_amount=0.0,
                    wind_speed=wind,
                    wind_direction=180.0,
                    cloud_cover=50.0,
                    pressure=1013.0
                )
            )
        
        forecast_data = MockForecast(forecasts)
        weather_data = MockWeather(forecasts[0])
        coordinator = MockCoordinator(weather_data, forecast_data)
        
        entity = FMIWeatherEntity("Test", coordinator)
        daily = entity._forecast(daily_mode=True)
        
        # Should use maximum wind speed: 25.0 m/s
        assert len(daily) >= 1
        wind = daily[0][ATTR_FORECAST_NATIVE_WIND_SPEED]
        expected_max_wind = 25.0
        
        assert wind == pytest.approx(expected_max_wind), \
            f"Daily wind speed should be {expected_max_wind} m/s (max), got {wind} m/s"
    
    def test_daily_forecast_averages_humidity(self):
        """Test that daily forecast correctly averages humidity across the day."""
        base_time = datetime.now(tz.tzlocal()).replace(hour=0, minute=0, second=0, microsecond=0)
        forecasts = []
        
        # Create a single day with varying humidity:
        # First hour: 50% (dry at midnight)
        # Hours 6-18: 90% (humid during day)
        # Rest: 50%
        for hour in range(24):
            humidity = 90.0 if 6 <= hour <= 18 else 50.0
            forecasts.append(
                MockWeatherData(
                    time=base_time + timedelta(hours=hour),
                    symbol=2,
                    temperature=15.0,
                    humidity=humidity,
                    precipitation_amount=0.0,
                    wind_speed=5.0,
                    wind_direction=180.0,
                    cloud_cover=50.0,
                    pressure=1013.0
                )
            )
        
        forecast_data = MockForecast(forecasts)
        weather_data = MockWeather(forecasts[0])
        coordinator = MockCoordinator(weather_data, forecast_data)
        
        entity = FMIWeatherEntity("Test", coordinator)
        daily = entity._forecast(daily_mode=True)
        
        # Should average humidity: (11 hours * 50% + 13 hours * 90%) / 24 = 71.67%
        assert len(daily) >= 1
        humidity = daily[0][ATTR_WEATHER_HUMIDITY]
        expected_avg_humidity = (11 * 50.0 + 13 * 90.0) / 24
        
        assert humidity == pytest.approx(expected_avg_humidity, abs=0.1), \
            f"Daily humidity should be {expected_avg_humidity:.1f}% (average), got {humidity:.1f}%"
    
    def test_daily_forecast_averages_cloud_coverage(self):
        """Test that daily forecast correctly averages cloud coverage across the day."""
        base_time = datetime.now(tz.tzlocal()).replace(hour=0, minute=0, second=0, microsecond=0)
        forecasts = []
        
        # Create a single day with varying cloud coverage:
        # First hour: 10% (clear at midnight)
        # Hours 8-16: 90% (cloudy during day)
        # Rest: 10%
        for hour in range(24):
            clouds = 90.0 if 8 <= hour <= 16 else 10.0
            forecasts.append(
                MockWeatherData(
                    time=base_time + timedelta(hours=hour),
                    symbol=2,
                    temperature=15.0,
                    humidity=70.0,
                    precipitation_amount=0.0,
                    wind_speed=5.0,
                    wind_direction=180.0,
                    cloud_cover=clouds,
                    pressure=1013.0
                )
            )
        
        forecast_data = MockForecast(forecasts)
        weather_data = MockWeather(forecasts[0])
        coordinator = MockCoordinator(weather_data, forecast_data)
        
        entity = FMIWeatherEntity("Test", coordinator)
        daily = entity._forecast(daily_mode=True)
        
        # Should average cloud coverage: (15 hours * 10% + 9 hours * 90%) / 24 = 40.0%
        assert len(daily) >= 1
        clouds = daily[0][ATTR_FORECAST_CLOUD_COVERAGE]
        expected_avg_clouds = (15 * 10.0 + 9 * 90.0) / 24
        
        assert clouds == pytest.approx(expected_avg_clouds, abs=0.1), \
            f"Daily cloud coverage should be {expected_avg_clouds:.1f}% (average), got {clouds:.1f}%"
    
    def test_daily_forecast_averages_pressure(self):
        """Test that daily forecast correctly averages pressure across the day."""
        base_time = datetime.now(tz.tzlocal()).replace(hour=0, minute=0, second=0, microsecond=0)
        forecasts = []
        
        # Create a single day with varying pressure:
        # First 12 hours: 1020 hPa (high pressure)
        # Last 12 hours: 1000 hPa (low pressure)
        for hour in range(24):
            pressure = 1020.0 if hour < 12 else 1000.0
            forecasts.append(
                MockWeatherData(
                    time=base_time + timedelta(hours=hour),
                    symbol=2,
                    temperature=15.0,
                    humidity=70.0,
                    precipitation_amount=0.0,
                    wind_speed=5.0,
                    wind_direction=180.0,
                    cloud_cover=50.0,
                    pressure=pressure
                )
            )
        
        forecast_data = MockForecast(forecasts)
        weather_data = MockWeather(forecasts[0])
        coordinator = MockCoordinator(weather_data, forecast_data)
        
        entity = FMIWeatherEntity("Test", coordinator)
        daily = entity._forecast(daily_mode=True)
        
        # Should average pressure: (12 * 1020 + 12 * 1000) / 24 = 1010.0 hPa
        assert len(daily) >= 1
        pressure = daily[0][ATTR_WEATHER_PRESSURE]
        expected_avg_pressure = 1010.0
        
        assert pressure == pytest.approx(expected_avg_pressure, abs=0.1), \
            f"Daily pressure should be {expected_avg_pressure:.1f} hPa (average), got {pressure:.1f} hPa"
    
    def test_daily_forecast_keeps_temperature_aggregation(self):
        """Test that temperature high/low aggregation still works correctly."""
        base_time = datetime.now(tz.tzlocal()).replace(hour=0, minute=0, second=0, microsecond=0)
        forecasts = []
        
        # Create a single day with varying temperature
        for hour in range(24):
            # Temperature peaks at noon (hour 12)
            temp = 10.0 + 15.0 * (1 - abs(12 - hour) / 12.0)
            
            forecasts.append(
                MockWeatherData(
                    time=base_time + timedelta(hours=hour),
                    symbol=2,
                    temperature=temp,
                    humidity=70.0,
                    precipitation_amount=0.0,
                    wind_speed=5.0,
                    wind_direction=180.0,
                    cloud_cover=50.0,
                    pressure=1013.0
                )
            )
        
        forecast_data = MockForecast(forecasts)
        weather_data = MockWeather(forecasts[0])
        coordinator = MockCoordinator(weather_data, forecast_data)
        
        entity = FMIWeatherEntity("Test", coordinator)
        daily = entity._forecast(daily_mode=True)
        
        # Temperature should be correctly aggregated (high at noon, low at midnight)
        assert len(daily) >= 1
        temp_high = daily[0][ATTR_FORECAST_NATIVE_TEMP]
        temp_low = daily[0][ATTR_FORECAST_NATIVE_TEMP_LOW]
        
        assert temp_high == pytest.approx(25.0, abs=0.1), \
            f"High temperature should be ~25°C, got {temp_high}°C"
        assert temp_low == pytest.approx(10.0, abs=0.1), \
            f"Low temperature should be ~10°C, got {temp_low}°C"
        assert temp_high >= temp_low, "High temperature should be >= low temperature"


class TestDailyForecastMultipleDays:
    """Test daily forecast aggregation across multiple days."""
    
    def test_daily_forecast_aggregates_each_day_independently(self):
        """Test that each day in daily forecast is aggregated independently."""
        base_time = datetime.now(tz.tzlocal()).replace(hour=0, minute=0, second=0, microsecond=0)
        forecasts = []
        
        # Create 3 days of hourly data with different patterns each day
        for day in range(3):
            day_start = base_time + timedelta(days=day)
            
            # Each day has unique precipitation pattern:
            # Day 0: 2mm per hour for all hours = 48mm total
            # Day 1: 3mm per hour for all hours = 72mm total
            # Day 2: 4mm per hour for all hours = 96mm total
            daily_precip_rate = 2.0 + day
            
            for hour in range(24):
                forecasts.append(
                    MockWeatherData(
                        time=day_start + timedelta(hours=hour),
                        symbol=2,
                        temperature=15.0 + day,  # Vary by day for identification
                        humidity=70.0,
                        precipitation_amount=daily_precip_rate,
                        wind_speed=5.0 + day * 5.0,  # Day 0: 5, Day 1: 10, Day 2: 15
                        wind_direction=180.0,
                        cloud_cover=50.0,
                        pressure=1013.0
                    )
                )
        
        forecast_data = MockForecast(forecasts)
        weather_data = MockWeather(forecasts[0])
        coordinator = MockCoordinator(weather_data, forecast_data)
        
        entity = FMIWeatherEntity("Test", coordinator)
        daily = entity._forecast(daily_mode=True)
        
        # Should have 3 daily forecasts
        assert len(daily) >= 3
        
        # Each day should have correctly aggregated precipitation
        # Day 0: 24 hours * 2mm = 48mm
        # Day 1: 24 hours * 3mm = 72mm
        # Day 2: 24 hours * 4mm = 96mm
        expected_precips = [48.0, 72.0, 96.0]
        expected_winds = [5.0, 10.0, 15.0]
        
        for i in range(min(3, len(daily))):
            precip = daily[i][ATTR_FORECAST_NATIVE_PRECIPITATION]
            wind = daily[i][ATTR_FORECAST_NATIVE_WIND_SPEED]
            
            assert precip == pytest.approx(expected_precips[i], abs=0.1), \
                f"Day {i}: precipitation should be {expected_precips[i]}mm, got {precip}mm"
            assert wind == pytest.approx(expected_winds[i], abs=0.1), \
                f"Day {i}: wind speed should be {expected_winds[i]} m/s, got {wind} m/s"


class TestDailyForecastEdgeCases:
    """Test edge cases for daily forecast aggregation."""
    
    def test_daily_forecast_with_zero_precipitation(self):
        """Test that days with zero precipitation are handled correctly."""
        base_time = datetime.now(tz.tzlocal()).replace(hour=0, minute=0, second=0, microsecond=0)
        forecasts = []
        
        # Create a day with zero precipitation
        for hour in range(24):
            forecasts.append(
                MockWeatherData(
                    time=base_time + timedelta(hours=hour),
                    symbol=2,
                    temperature=15.0,
                    humidity=70.0,
                    precipitation_amount=0.0,
                    wind_speed=5.0,
                    wind_direction=180.0,
                    cloud_cover=50.0,
                    pressure=1013.0
                )
            )
        
        forecast_data = MockForecast(forecasts)
        weather_data = MockWeather(forecasts[0])
        coordinator = MockCoordinator(weather_data, forecast_data)
        
        entity = FMIWeatherEntity("Test", coordinator)
        daily = entity._forecast(daily_mode=True)
        
        assert len(daily) >= 1
        precip = daily[0][ATTR_FORECAST_NATIVE_PRECIPITATION]
        assert precip == 0.0, f"Precipitation should be 0.0mm, got {precip}mm"
    
    def test_daily_forecast_with_none_values(self):
        """Test that None values are handled gracefully in aggregation."""
        base_time = datetime.now(tz.tzlocal()).replace(hour=0, minute=0, second=0, microsecond=0)
        forecasts = []
        
        # Create a day with some None values
        for hour in range(24):
            # Every other hour has None for some values
            humidity = 70.0 if hour % 2 == 0 else None
            wind = 5.0 if hour % 2 == 0 else None
            
            forecasts.append(
                MockWeatherData(
                    time=base_time + timedelta(hours=hour),
                    symbol=2,
                    temperature=15.0,
                    humidity=humidity,
                    precipitation_amount=2.0,
                    wind_speed=wind,
                    wind_direction=180.0,
                    cloud_cover=50.0,
                    pressure=1013.0
                )
            )
        
        forecast_data = MockForecast(forecasts)
        weather_data = MockWeather(forecasts[0])
        coordinator = MockCoordinator(weather_data, forecast_data)
        
        entity = FMIWeatherEntity("Test", coordinator)
        daily = entity._forecast(daily_mode=True)
        
        # Should still aggregate available values
        assert len(daily) >= 1
        # Humidity should average only the non-None values (12 hours of 70%)
        humidity = daily[0][ATTR_WEATHER_HUMIDITY]
        assert humidity == pytest.approx(70.0, abs=0.1)
        
        # Wind should use max of non-None values (all are 5.0)
        wind = daily[0][ATTR_FORECAST_NATIVE_WIND_SPEED]
        assert wind == pytest.approx(5.0, abs=0.1)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
