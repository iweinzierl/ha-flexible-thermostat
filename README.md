# Flexible Thermostat

A custom Home Assistant integration that allows you to create virtual thermostats.

It supports:
- Heating control via a heater switch
- Optional cooling control via a cooler switch
- Configurable hysteresis (cold and hot tolerances)
- Optional fallback temperature sensor

## Installation

1. Install via HACS (Home Assistant Community Store).
2. Add a custom repository using the URL of this repository.
3. Select "Integration" as the category.
4. Install "Flexible Thermostat".
5. Restart Home Assistant.

## Configuration

1. Go to Settings -> Devices & Services.
2. Click "Add Integration".
3. Search for "Flexible Thermostat".
4. Follow the configuration steps to select your entities and tolerances.

### Required entities

- Heater switch
- Temperature sensor

### Optional entities

- Cooler switch
- Fallback temperature sensor

If no cooler switch is configured, the thermostat exposes `heat` and `off` only.
If a cooler switch is configured, the thermostat exposes `heat`, `cool`, and `off`.

## Control behavior

The thermostat uses hysteresis based on `cold_tolerance` and `hot_tolerance`.

### Heat mode

- Turns heater on when `current_temp <= target_temp - cold_tolerance`
- Turns heater off when `current_temp >= target_temp + hot_tolerance`

### Cool mode

- Turns cooler on when `current_temp >= target_temp + hot_tolerance`
- Turns cooler off when `current_temp <= target_temp - cold_tolerance`

## Cooling with floor heating and heatpumps

Some real thermostats do not provide a native cooling mode, while the heatpump does.
In that setup, configure the cooler switch so that turning it on applies your "open flow" strategy (for example setting the underlying physical thermostat to its maximum configured value).
This integration handles when cooling should be active; your cooler switch entity can implement the installation-specific actuation.
