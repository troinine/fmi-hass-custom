"""Common utilities for the FMI Weather and Sensor integrations."""

import math
import aiohttp
from datetime import date, datetime
from dateutil import tz
from typing import Optional, Dict, List

try:
    from homeassistant.helpers.sun import get_astral_event_date
    from homeassistant.const import SUN_EVENT_SUNSET, SUN_EVENT_SUNRISE
except ImportError:
    get_astral_event_date = None
    SUN_EVENT_SUNSET = None
    SUN_EVENT_SUNRISE = None

try:
    from . import const
except ImportError:
    import const


class BoundingBox():
    def __init__(self, lat_min=None, lon_min=None,
                 lat_max=None, lon_max=None):
        self.lat_min = lat_min
        self.lon_min = lon_min
        self.lat_max = lat_max
        self.lon_max = lon_max


def get_bounding_box_covering_finland():
    """Bounding box to covert while Finland."""
    box = BoundingBox()
    box.lat_min = const.BOUNDING_BOX_LAT_MIN
    box.lon_min = const.BOUNDING_BOX_LONG_MIN
    box.lat_max = const.BOUNDING_BOX_LAT_MAX
    box.lon_max = const.BOUNDING_BOX_LONG_MAX

    return box


def get_bounding_box(latitude_in_degrees, longitude_in_degrees, half_side_in_km):
    """Calculate min and max coordinates for bounding box."""
    assert 0 < half_side_in_km
    assert -90.0 <= latitude_in_degrees <= 90.0
    assert -180.0 <= longitude_in_degrees <= 180.0

    lat = math.radians(latitude_in_degrees)
    lon = math.radians(longitude_in_degrees)

    radius = 6371
    # Radius of the parallel at given latitude
    parallel_radius = radius * math.cos(lat)

    lat_min = lat - half_side_in_km / radius
    lat_max = lat + half_side_in_km / radius
    lon_min = lon - half_side_in_km / parallel_radius
    lon_max = lon + half_side_in_km / parallel_radius
    rad2deg = math.degrees

    box = BoundingBox()
    box.lat_min = rad2deg(lat_min)
    box.lon_min = rad2deg(lon_min)
    box.lat_max = rad2deg(lat_max)
    box.lon_max = rad2deg(lon_max)

    return box


def get_weather_symbol(symbol, hass=None):
    """Get a weather symbol for the symbol value."""
    ret_val = const.FMI_WEATHER_SYMBOL_MAP.get(symbol, "")

    if hass is None or symbol != 1:  # was ret_val != 1 <- always False
        return ret_val

    # Clear as per FMI
    today = date.today()
    sunset = get_astral_event_date(hass, SUN_EVENT_SUNSET, today)
    sunset = sunset.astimezone(tz.tzlocal())

    sunrise = get_astral_event_date(hass, SUN_EVENT_SUNRISE, today)
    sunrise = sunrise.astimezone(tz.tzlocal())

    time_now = datetime.now().astimezone(tz.tzlocal())
    if time_now <= sunrise or time_now >= sunset:
        # Clear night
        ret_val = const.FMI_WEATHER_SYMBOL_MAP[0]

    return ret_val


def select_daily_condition(hourly_conditions_with_times):
    """
    Select the most appropriate condition for a daily forecast using hybrid approach.
    
    This implements a "Threshold with Safety Override" algorithm:
    1. Safety Override: Any severe condition (lightning) ≥1 hour shown
    2. Significant Precipitation: Rain/snow ≥3 hours shown
    3. Visibility Issues: Fog ≥4 hours shown
    4. Fallback: Most common condition during daytime (07:00-20:00)
    
    For tie-breaking within the same severity tier, uses time-weighted selection
    (conditions closer to midday are preferred).
    
    Always prefers 'sunny' over 'clear-night' for daily forecasts.
    
    Args:
        hourly_conditions_with_times: List of (datetime, condition) tuples
        
    Returns:
        str: The selected weather condition for the day
    """
    if not hourly_conditions_with_times:
        return 'sunny'  # Default
    
    from collections import Counter, defaultdict
    
    # Replace 'clear-night' with 'sunny' for daily forecasts
    normalized_conditions = [
        (time, 'sunny' if cond == 'clear-night' else cond)
        for time, cond in hourly_conditions_with_times
    ]
    
    # Count occurrences of each condition
    condition_counts = Counter(cond for _, cond in normalized_conditions)
    
    # Track conditions by severity tier with time information
    severe_conditions = defaultdict(list)      # {condition: [times]}
    precipitation_conditions = defaultdict(list)
    visibility_conditions = defaultdict(list)
    
    for time, condition in normalized_conditions:
        severity = const.WEATHER_CONDITION_SEVERITY.get(condition, 0)
        
        if severity >= 90:  # Tier 1: Severe
            severe_conditions[condition].append(time)
        elif severity >= 55:  # Tier 2-3: Precipitation
            precipitation_conditions[condition].append(time)
        elif severity >= 37:  # Tier 4: Visibility
            visibility_conditions[condition].append(time)
    
    # Helper function to select condition with time-weighting for ties
    def select_from_tier(conditions_dict, threshold):
        """
        Select condition from tier based on severity and time-weighting.
        
        Returns condition if it meets threshold, otherwise None.
        Time-weighting prefers conditions closer to midday (12:00).
        """
        if not conditions_dict:
            return None
        
        # Filter conditions that meet threshold
        qualifying = {
            cond: times for cond, times in conditions_dict.items()
            if len(times) >= threshold
        }
        
        if not qualifying:
            return None
        
        # Find the highest severity among qualifying conditions
        max_severity = max(
            const.WEATHER_CONDITION_SEVERITY.get(cond, 0)
            for cond in qualifying.keys()
        )
        
        # Get all conditions with max severity
        top_conditions = [
            (cond, times) for cond, times in qualifying.items()
            if const.WEATHER_CONDITION_SEVERITY.get(cond, 0) == max_severity
        ]
        
        if len(top_conditions) == 1:
            return top_conditions[0][0]
        
        # Tie-break using time-weighting (prefer conditions closer to noon)
        def time_weight(times_list):
            """Calculate weight favoring midday occurrences."""
            # Distance from 12:00 - smaller is better
            distances = [abs(t.hour - 12) for t in times_list]
            # Average distance (lower = better = closer to noon)
            return sum(distances) / len(distances)
        
        best_condition = min(top_conditions, key=lambda x: time_weight(x[1]))
        return best_condition[0]
    
    # STEP 1: Safety Override - Any severe condition ≥1 hour
    severe_result = select_from_tier(severe_conditions, 
                                    const.CONDITION_THRESHOLDS['severe'])
    if severe_result:
        return severe_result
    
    # STEP 2: Significant Precipitation - ≥3 hours
    precip_result = select_from_tier(precipitation_conditions,
                                    const.CONDITION_THRESHOLDS['precipitation'])
    if precip_result:
        return precip_result
    
    # STEP 3: Visibility Issues - ≥4 hours
    vis_result = select_from_tier(visibility_conditions,
                                  const.CONDITION_THRESHOLDS['visibility'])
    if vis_result:
        return vis_result
    
    # STEP 4: Fallback to most common during daytime
    daytime_conditions = [
        cond for time, cond in normalized_conditions
        if const.DAYTIME_START_HOUR <= time.hour <= const.DAYTIME_END_HOUR
    ]
    
    if daytime_conditions:
        counter = Counter(daytime_conditions)
        most_common_count = counter.most_common(1)[0][1]
        
        # Get all conditions with the highest count
        most_common = [cond for cond, count in counter.items() 
                      if count == most_common_count]
        
        if len(most_common) == 1:
            return most_common[0]
        
        # Tie-break by time-weighting
        condition_times = defaultdict(list)
        for time, cond in normalized_conditions:
            if cond in most_common and \
               const.DAYTIME_START_HOUR <= time.hour <= const.DAYTIME_END_HOUR:
                condition_times[cond].append(time)
        
        def time_weight(times_list):
            distances = [abs(t.hour - 12) for t in times_list]
            return sum(distances) / len(distances)
        
        best = min(condition_times.items(), key=lambda x: time_weight(x[1]))
        return best[0]
    
    # STEP 5: Ultimate fallback - most common overall
    most_common_overall = condition_counts.most_common(1)[0][0]
    return most_common_overall


class UVIndexData:
    """Structure to hold UV index forecast data from Open-Meteo."""

    def __init__(self, time: datetime, uv_index: float, uv_index_clear_sky: Optional[float] = None):
        """Initialize UV index data point."""
        self.time = time
        self.uv_index = uv_index
        self.uv_index_clear_sky = uv_index_clear_sky


async def fetch_uv_index_data(
    session: aiohttp.ClientSession,
    latitude: float,
    longitude: float,
    forecast_days: int = 7,
    timeout_seconds: int = 10
) -> Optional[Dict[datetime, UVIndexData]]:
    """
    Fetch UV index forecast data from Open-Meteo API.

    Args:
        session: aiohttp ClientSession for making requests
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        forecast_days: Number of days to forecast (default 7, max 16)
        timeout_seconds: Request timeout in seconds

    Returns:
        Dictionary mapping datetime to UVIndexData, or None on error
    """
    try:
        # Construct API URL
        url = (
            f"{const.OPEN_METEO_BASE_URL}"
            f"?latitude={latitude}&longitude={longitude}"
            f"&hourly=uv_index,uv_index_clear_sky"
            f"&daily=uv_index_max,uv_index_clear_sky_max"
            f"&forecast_days={min(forecast_days, 16)}"
            f"&timezone=auto"
        )

        # Make API request
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout_seconds)) as response:
            if response.status != 200:
                const.LOGGER.error(
                    "Open-Meteo API returned status %d for UV index data",
                    response.status
                )
                return None

            data = await response.json()

            # Parse hourly UV index data
            uv_data_dict = {}
            if "hourly" in data and "time" in data["hourly"] and "uv_index" in data["hourly"]:
                times = data["hourly"]["time"]
                uv_indices = data["hourly"]["uv_index"]
                uv_clear_sky = data["hourly"].get("uv_index_clear_sky", [None] * len(times))

                # Parse each time/UV pair
                for time_str, uv_val, uv_clear in zip(times, uv_indices, uv_clear_sky):
                    try:
                        # Parse ISO 8601 datetime
                        dt = datetime.fromisoformat(time_str)
                        uv_data_dict[dt] = UVIndexData(
                            time=dt,
                            uv_index=float(uv_val) if uv_val is not None else 0.0,
                            uv_index_clear_sky=float(uv_clear) if uv_clear is not None else None
                        )
                    except (ValueError, TypeError) as parse_error:
                        const.LOGGER.warning(
                            "Failed to parse UV index data point: %s", parse_error
                        )
                        continue

            const.LOGGER.debug(
                "Fetched %d UV index data points from Open-Meteo for coordinates (%f, %f)",
                len(uv_data_dict), latitude, longitude
            )

            return uv_data_dict if uv_data_dict else None

    except aiohttp.ClientError as error:
        const.LOGGER.error("Error fetching UV index data from Open-Meteo: %s", error)
        return None
    except Exception as error:
        const.LOGGER.error("Unexpected error fetching UV index data: %s", error)
        return None

