# Change log for Charge Amps for Home Assistant

## 1.4.1 (2021-04-05)  

- Bump requirements

## 1.4.0 (2021-02-26)

- Update default icons for charger

## 1.3.0 (2020-11-20)

- Fix updating multiple chargepoints (incorrectly throttled)
- Add `scan_interval` option (default 30 seconds, minimum 5 seconds).

## 1.2.0 (2020-11-01)

- Add `charge_point_id` attribute to all entities.
- Add `connector_id` attribute to sensors and switches.
- Fix log level in light

## 1.1.0 (2020-06-30)

- Add sensor for total energy.
- Add power sensors.
- Add light platform.
- Different icons for charge port and Schuko.
- Fix deprecation warning of SwitchDevice.

## 1.0.0 (2020-03-13)

- Better support for multiple Charge points.
- Add switch for each Charge point connector.
- Do not throttle status updates for explicit state changes.

## 0.0.1 (2020-01-12)

- Initial release.
