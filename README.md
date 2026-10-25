# homeassistant-4heat

Home Assistant Component for 4heat stove devices

<a href="https://www.buymeacoffee.com/zauberertz" target="_blank"><img height="41px" width="167px" src="https://cdn.buymeacoffee.com/buttons/default-blue.png" alt="Buy Me A Coffee"></a>

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)

### Installation

Copy this folder to `<config_dir>/custom_components/4heat/`.

### HACS
Search for 4Heat

### Configuration

The integration is configurated via UI

BETA * BETA * BETA - Not finished yet - BETA * BETA * BETA

### Thermostat (room setpoint)

If the stove reports a room setpoint (`J30138`), a `climate` entity is created:
target temperature = J30138 (whole °C), current temperature = 30006, HVAC mode = ON/OFF.
The setpoint is written with `["SEC","1","J30138000000000020"]` (20 °C) and also works
through the `4heat.set_value` service on the `UN 30138` / `Room setpoint` sensor.

If the stove loses its wireless room probe it falls back to its internal probe and
reports wrong values (e.g. room 29 °C, setpoint 38 °C): the integration keeps the
last trusted values meanwhile and shows `room_probe: lost since HH:MM` on the thermostat.

### Connection to the Wi-Fi module

The module's local server saturates easily, so the integration makes only one TCP
exchange at a time, polls every 120 s, waits 5 min after a failure and re-reads the
stove 25 s after a command. Avoid sending read commands for ids the stove does not
report: on some modules this freezes the local server until a power cycle.

### Todo:
- [x] Monitorig of all status values
- [ ] Discover more sensor meanings
- [ ] Find a way to get model and serial
- [x] Add Service to set value like target temp
- [x] Add Icons


