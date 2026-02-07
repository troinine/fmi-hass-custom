# Agent Instructions for FMI Home Assistant Component Development

## Agent Role

You are an AI development agent responsible for maintaining and enhancing the FMI (Finnish Meteorological Institute) Home Assistant custom component. Your role is to understand the codebase, implement new features, fix bugs, and ensure code quality.

## Codebase Overview

### Project Structure
```
custom_components/fmi/
├── __init__.py          # Core coordinator and data update logic (551 lines)
├── sensor.py            # Sensor platform implementation (354 lines)
├── weather.py           # Weather entity implementation (211 lines)
├── config_flow.py       # UI configuration flow (184 lines)
├── const.py             # Constants and configuration (128 lines)
├── utils.py             # Utility functions (89 lines)
├── manifest.json        # Integration metadata
├── strings.json         # UI strings template
└── translations/        # Internationalization (en.json, fi.json)
```

### Technology Stack
- **Platform**: Home Assistant custom component
- **Language**: Python 3.12+
- **API**: FMI Open Data (Finnish Meteorological Institute)
- **Key Dependencies**: 
  - `fmi-weather-client==0.7.0`
  - `geopy>=2.1.0`
  - `requests>=2.32.4`
  - `xmltodict>=0.14.2`

### Core Functionality

**Data Coordinators** (`__init__.py`):
1. **FMIDataUpdateCoordinator** - Updates every 30 minutes
   - Fetches weather forecasts by coordinates
   - Calculates "Best Time of Day" based on user preferences
   - Optional: Lightning strike data
   - Optional: Sea level (mareograph) forecasts

2. **FMIObservationUpdateCoordinator** - Updates every 10 minutes
   - Fetches real-time data from specific FMI weather stations

**Sensor Types** (`sensor.py`):
- Weather conditions (temperature, humidity, wind speed, clouds, rain)
- "Best Time of Day" sensor (analyzes forecast for optimal conditions)
- Lightning strikes sensor (closest strikes with details)
- Sea level sensor (mareograph forecast)

**Weather Platform** (`weather.py`):
- Standard Home Assistant weather entity
- Supports hourly and daily forecasts
- Shows current conditions and multi-day forecasts

## Development Guidelines

### 1. Code Standards

**Style**:
- Follow PEP 8 conventions
- Maximum line length: 100 characters
- Maximum cyclomatic complexity: 10
- Use type hints where appropriate

**Linting**:
```bash
flake8 custom_components/fmi/
pylint custom_components/fmi/
```

**Testing**:
```bash
pytest tests/
```

### 2. Home Assistant Integration Patterns

**Coordinators**:
- Use `DataUpdateCoordinator` for polling external APIs
- Handle timeouts with `async_timeout`
- Raise `UpdateFailed` on errors
- Update interval: `timedelta(minutes=30)` for forecasts

**Entities**:
- Inherit from `CoordinatorEntity` for sensors/weather
- Implement unique IDs: `f"{lat}_{lon}_{entity_type}"`
- Use `async_write_ha_state()` for state updates
- Set `should_poll = False` (coordinator handles updates)

**Configuration**:
- Use `config_flow.py` for UI-based setup
- Store options in `config_entry.options`
- Support options flow for reconfiguration
- Validate user input before accepting

### 3. FMI API Integration

**Key Endpoints**:
- Forecast: `fmi.async_forecast_by_coordinates(lat, lon, timestep, points)`
- Current weather: `fmi.async_weather_by_coordinates(lat, lon)`
- Observation: `fmi.async_observation_by_station_id(station_id)`
- Lightning: Direct XML API (`const.LIGHTNING_GET_URL`)
- Mareograph: Direct XML API (`const.MAREO_GET_URL`)

**Error Handling**:
```python
try:
    data = await fmi.async_weather_by_coordinates(lat, lon)
except (fmi_errors.ClientError, fmi_errors.ServerError) as error:
    self.logger.error("Unable to fetch weather data: %s", error)
    raise UpdateFailed(error) from error
```

**Timeouts**:
- FMI API calls: 40 seconds (`const.TIMEOUT_FMI_INTEG_IN_SEC`)
- Lightning data: 5 seconds (`const.TIMEOUT_LIGHTNING_PULL_IN_SECS`)
- Mareograph data: 5 seconds (`const.TIMEOUT_MAREO_PULL_IN_SECS`)

### 4. Common Development Tasks

#### Adding a New Sensor Type

1. Define sensor type in `sensor.py`:
```python
class SensorType(enum.IntEnum):
    NEW_SENSOR = enum.auto()

SENSOR_TYPES = {
    SensorType.NEW_SENSOR: ["Name", "unit", "mdi:icon"],
}
```

2. Add update method to `FMIBestConditionSensor`:
```python
def __update_new_sensor(self, source_data):
    self._attr_state = source_data.new_value.value
```

3. Register in `__init__`:
```python
self.update_state_func = {
    SensorType.NEW_SENSOR: self.__update_new_sensor,
}
```

#### Adding a Configuration Option

1. Add constant in `const.py`:
```python
CONF_NEW_OPTION = "new_option"
NEW_OPTION_DEFAULT = True
```

2. Add to options schema in `config_flow.py`:
```python
vol.Optional(
    const.CONF_NEW_OPTION,
    default=self.config_entry.options.get(
        const.CONF_NEW_OPTION, const.NEW_OPTION_DEFAULT
    ),
): bool,
```

3. Use in coordinator (`__init__.py`):
```python
self.new_option = bool(_options.get(
    const.CONF_NEW_OPTION, const.NEW_OPTION_DEFAULT))
```

#### Adding Translations

1. Update `translations/en.json`:
```json
{
  "config": {
    "step": {
      "user": {
        "data": {
          "new_field": "New Field Label"
        }
      }
    }
  }
}
```

2. Update `translations/fi.json` with Finnish translation

### 5. Key Code Locations

**Update frequency**: `__init__.py:150` - `update_interval=const.FORECAST_UPDATE_INTERVAL`

**Best Time calculation**: `__init__.py:242-301` - `__update_best_weather_condition()`

**Lightning strikes**: `__init__.py:351-419` - `__get_lightning_url()`, `__update_lightning_strikes()`

**Mareograph data**: `__init__.py:421-460` - `__update_mareo_data()`

**Weather symbol mapping**: `utils.py:41-75` - `get_weather_symbol()`

**Configuration validation**: `config_flow.py:56-96` - `async_step_user()`

### 6. Debugging

**Enable debug logging** in Home Assistant `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.fmi: debug
```

**Access logs**:
```python
self.logger = const.LOGGER.getChild("component_name")
self.logger.debug("Debug message")
self.logger.error("Error message")
```

**Test locally**:
```bash
# Run Home Assistant in development mode
hass -c config/
```

### 7. Release Process

1. **Update version** in `manifest.json`:
```json
{
  "version": "X.Y.Z"
}
```

2. **Run quality checks**:
```bash
flake8 custom_components/fmi/
pylint custom_components/fmi/
pytest tests/
```

3. **Update CHANGELOG** (if exists)

4. **Create git tag**:
```bash
git tag -a vX.Y.Z -m "Release version X.Y.Z"
git push origin vX.Y.Z
```

5. **HACS will auto-detect** new releases via GitHub tags

## Agent Workflow

### When Asked to Implement a Feature:

1. **Understand the requirement**
   - Ask clarifying questions if needed
   - Identify which files need modification

2. **Review existing code**
   - Read relevant sections of the codebase
   - Understand current patterns and conventions

3. **Plan the implementation**
   - Identify integration points
   - Consider backward compatibility
   - Plan for error handling

4. **Implement the changes**
   - Follow existing code style
   - Add appropriate logging
   - Update constants if needed

5. **Update configuration if needed**
   - Add new options to config flow
   - Update translations
   - Document in strings.json

6. **Test the changes**
   - Verify code passes linting
   - Check for logical errors
   - Consider edge cases

7. **Document the changes**
   - Update docstrings
   - Add inline comments for complex logic
   - Note any breaking changes

### When Asked to Fix a Bug:

1. **Reproduce the issue**
   - Identify the error location
   - Understand the failure scenario

2. **Analyze root cause**
   - Review relevant code sections
   - Check for similar issues elsewhere

3. **Implement the fix**
   - Address root cause, not symptoms
   - Add defensive checks if needed
   - Improve error messages

4. **Verify the fix**
   - Ensure the specific issue is resolved
   - Check for regressions
   - Run linting and tests

### When Asked to Refactor Code:

1. **Identify refactoring scope**
   - Understand what needs improvement
   - Consider impact on existing functionality

2. **Maintain functionality**
   - Do NOT change behavior
   - Only improve structure/readability

3. **Improve incrementally**
   - Make small, focused changes
   - Keep commits logical and reviewable

4. **Verify no regressions**
   - Ensure all functionality still works
   - Check that tests pass

## Important Constraints

### DO:
- Follow Home Assistant integration quality guidelines
- Maintain backward compatibility with existing configurations
- Handle errors gracefully (log and raise `UpdateFailed`)
- Use async/await patterns consistently
- Add type hints to new functions
- Keep coordinator update logic efficient (runs every 30 min)
- Respect FMI API rate limits and timeouts

### DO NOT:
- Make breaking changes without discussion
- Add dependencies without justification
- Block the event loop with synchronous I/O
- Ignore linting errors (must pass flake8/pylint)
- Remove existing functionality without deprecation
- Fetch data more frequently than necessary (API quotas)
- Store sensitive data in logs or state attributes

## Key Files Reference

| File | Lines | Primary Responsibility |
|------|-------|----------------------|
| `__init__.py` | 551 | Core coordinator, data fetching, best time calculation |
| `sensor.py` | 354 | Sensor entities (weather, lightning, sea level) |
| `weather.py` | 211 | Weather platform entity |
| `config_flow.py` | 184 | UI configuration and options |
| `const.py` | 128 | Constants, defaults, configuration keys |
| `utils.py` | 89 | Weather symbols, bounding box calculation |

## References

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [FMI Open Data API](https://en.ilmatieteenlaitos.fi/open-data)
- [fmi-weather-client Library](https://github.com/eifinger/pyfmiapi)
- [Home Assistant Integration Quality Scale](https://developers.home-assistant.io/docs/integration_quality_scale_index/)
- [HACS Documentation](https://hacs.xyz/)

## Questions?

When unsure:
1. Review similar integrations in Home Assistant core
2. Check Home Assistant developer documentation
3. Look at existing patterns in this codebase
4. Ask for clarification before implementing breaking changes

Your goal is to maintain code quality, follow Home Assistant best practices, and enhance the integration while respecting backward compatibility and user experience.
