# Chargeamps for Home Assistant

This repository contains a Chargeamps component for Home Assistant.


## Configuration

The component requires configuration via the configuration file. The following parameters are required:

    chargeamps:
      username: EMAIL_ADDRESS
      password: SECRET_PASSWORD
      api_key: SECRET_API_KEY

The default is to configure all charge points for the account. To only include some charge points a list of charge point IDs can be provided using the `chargepoints` parameter.


## Entities

Each Chargeamps chargepoint connector will be represented as a sensor with the current status of the connector as the state.

### Additional attributes

- `total_consumption_kwh`


## Services

The following services are implemented by the component:

- `set_light` -- set charge point lights
- `set_max_current` -- set max current for connector
- `enable` -- enable connector
- `disable` -- disable connector
