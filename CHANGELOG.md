# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.x] - to be released
- Update to protobuf-6 
- Update minimum python version to 3.11 to reflect actual compatibility.

## [0.2.4] - 2025-06-20
- Fix AttributeError on ``PyAnova.get_status()`` (#17)
- Mock device in unittests (#2)
- Bump protobuf (#20)

## [0.2.3] - 2024-11-11
- Update to protobuf-5 (#15)

## [0.2.2] - 2024-10-03
- Fix incompatibility with ESPHome Bluetooth Proxies.
  
  Subscribe callback only once to 'read' characteristics.
  Avoid sharing result array and future across subsequent calls.
  
- Add debug log statements
- Retry connection attempt

## [0.2.1] - 2024-09-29
### Changed
- Fix BleakError raised on subsequent read commands on ``bleak-esphome`` backend.

## [0.2.0] - 2024-09-29

### Breaking
- ``PyAnova``: Removed `auto_reconnect` argument.

### Changed
- Add ``PyAnova.add_on_disconnect`` to subscribe callbacks to device going offline.
- Reduce timeouts and allow to override them.
- Improve thread safety while sending read commands and waiting for response.
- Add ``PyAnova.get_device_info()`` which always returns `3`.
- Implement subscription to polled sensor status updates.
- Improved connection logic.
- ``PyAnova.connect()``: Use device provided to `PyAnova.__init__()` and skip discovery.

## [0.1.0] - 2024-01-21
### Initial release
- Control and query the Anova Nano via BLE.
