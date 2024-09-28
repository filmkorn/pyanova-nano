# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2024-XX-X
### Changed
- Reduce timeouts and allow to override them.
- Improve thread safety while sending read commands and waiting for response.
- Add ``PyAnova.get_device_info()`` which always returns `3`.
- Implement subscription to polled sensor status updates.
- Improved connection logic.
- ``PyAnova.connect()``: Use device provided to `PyAnova.__init__()` and skip discovery.

## [0.1.0] - 2024-01-21
### Initial release
- Control and query the Anova Nano via BLE.
