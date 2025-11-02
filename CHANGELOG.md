# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
- No unreleased changes so far

## [0.7.4] - 2025-11-02
### Changed
- Updated some dependencies

## [0.7.3] - 2025-04-19
### Fixed
- Problems with connectors after changing to PyJWT

### Changed
- remove old force update mechanism in favour of new update command #102

## [0.7.2] - 2025-04-19
### Fixed
- Conflicting dependencies with carconnectivity connectors

## [0.7.1] - 2025-04-18
### Fixed
- Fixed ignore_for config option

## [0.7] - 2025-04-17
### Added
- Example for autostart with systemd

### Fixed
- Docker is now consistently using ubuntu 24.04

### Changed
- Values are now rounded to the expected precision. This is in particular useful with locales that convert values.
- Bump carconnectivity dependency to 0.7

## [0.6] - 2025-04-02
### Changed
- Bump carconnectivity dependency to 0.6
- Allowing empty broker username and password when login is not required

## [0.5] - 2025-03-20
### Changed
- Bump carconnectivity dependency to 0.5

## [0.4.2] - 2025-03-04
### Fixed
- Fixed publishing to broken topic on disconnect
- Fixed locale settings on docker container

## [0.4.1] - 2025-03-02
### Changed
- Docker container now comes with all officially maintained plugins and connectors pre-installed

## [0.4] - 2025-03-02
### Added
- Improved documentation
- Improved access to connection state
- Improved access to health state
- Access to a full json topic with all attributes (beta)
- Added callback support for third party plugins to send and receive MQTT messages
- Added writeable attributes also in readable attributes list

## [0.3.1] - 2025-02-20
### Fixed
- Fixes bug due to template ambiguity

### Added
- Plugin UI root

## [0.3] - 2025-02-19
### Added
- Added support for images
- Added support for webui plugin

## [0.2] - 2025-02-02
### Changed
- Updated version of bundled connectors

## [0.1] - 2025-01-25
Initial release, let's go and give this to the public to try out...

[unreleased]: https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/compare/v0.7.4...HEAD
[0.7.4]: https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/releases/tag/v0.7.4
[0.7.3]: https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/releases/tag/v0.7.3
[0.7.2]: https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/releases/tag/v0.7.2
[0.7.1]: https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/releases/tag/v0.7.1
[0.7]: https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/releases/tag/v0.7
[0.6]: https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/releases/tag/v0.6
[0.5]: https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/releases/tag/v0.5
[0.4.2]: https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/releases/tag/v0.4.2
[0.4.1]: https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/releases/tag/v0.4.1
[0.4]: https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/releases/tag/v0.4
[0.3.1]: https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/releases/tag/v0.3.1
[0.3]: https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/releases/tag/v0.3
[0.2]: https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/releases/tag/v0.2
[0.1]: https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/releases/tag/v0.1
