# Change log for Charge Amps for Home Assistant

## 1.8.3 (2023-08-05)

- Update dependencies

## 1.8.2 (2023-05-20)

- Update dependencies

## 1.8.1 (2023-01-06)

- Fix bug sensor reporting data as `wH` instead of intended `kWh`

## 1.8.0 (2023-01-03)

- Use modern Home Assistant enums, reported by @frenck

## 1.7.0 (2022-04-18)

- Add support for cable lock/unlock (Aura only) via service call.

## 1.6.1 (2022-03-06)

- Bump `python-chargeamps` requirement

## 1.6.0 (2021-12-19)

- Add device info
- Use `extra_state_attributes` instead of `device_state_attributes`

## 1.5.2 (2021-10-07)

- Bump `python-chargeamps` requirement

## 1.5.1 (2021-09-06)

- Update state class for `ChargeampsTotalEnergy`

## 1.5.0 (2021-08-11)

- Add more properties to total energy sensor in order to support long term statistics
- Remove bogus "Connector ID" attribute from total energy sensor

## 1.4.4 (2021-07-02)

- Bump requirements for updated default API endpoint

## 1.4.3 (2021-05-09)

- Add `iot_class` to manifest

## 1.4.2 (2021-04-05)

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
