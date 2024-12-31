# Tesy Water Heater Integration for Home Assistant

This is a custom integration for Home Assistant that allows you to control Tesy water heaters via the Home Assistant platform. It is specially designed for devices with Atheros AR9331 chipset which exposes API such as status. With this integration, you can manage the water heater’s power state, temperature settings, operation modes, and more directly from Home Assistant.

## Features

- **Power Control**: Turn the water heater on or off. While it is Off the only available mode is On while the previous operation mode is preserved. While On you can set any of the available operation modes such as:
  - Manual - it is designed for manually control the requited temperature
  - P1 to P3 
  - 3 Eco programs
  - Powerfull state which is triggered by a boost switch
- **Temperature Control**: Set the desired water temperature. In case you are in any other operation Mode, Manual is automatically set. 
- **Away Mode**: Configure the vacation mode with custom end times and temperatures.(still under work)
- **Real-Time Updates**: Sync device status and temperatures with Home Assistant.

## Installation

### Manual Installation

1. Download the repository as a ZIP file and extract it.
2. Copy the `tesy` folder to your Home Assistant `custom_components` directory.
   - Typically, the directory is located at `~/.homeassistant/custom_components/`.
   - If the `custom_components` directory does not exist, create it.
3. Restart Home Assistant.

### HACS Installation

1.Add this repo as a "Custom repository" with type "Integration"
2. Click "Install" in the new "Tesy" card in HACS.
3. Install
4. Restart Home Assistant
5. Click Add Integration and choose "Tesy ModEco Water Heater". Follow the configuration flow

## Configuration

1. Go to **Settings** > **Devices & Services** > **Integrations**.
2. Click on **Add Integration** and search for "Tesy Water Heater."
3. Enter the required configuration details:
   - IP address of your Tesy water heater.

After configuration, the Tesy water heater should be available as a controllable entity in Home Assistant as well most of the availiable sensors

## Entities

This integration adds the following entities:

- **Water Heater**: Main control for the device, including power, temperature, and operation mode.

## Services

### `tesy.set_vacation_mode`

Allows you to configure the vacation mode for the water heater.

#### Service Data:

- `vacation_end`: The end time for the vacation mode (format: `YYYY-MM-DD HH:MM:SS`).
- `vacation_temp`: The temperature to set after vacation ends.

### Example YAML for Vacation Mode

```yaml
service: tesy.set_vacation_mode
data:
  vacation_end: '2024-01-01 10:00:00'
  vacation_temp: 40
```

## Known Issues

- Ensure all required entities (e.g., `input_datetime` and `input_number` helpers) are properly configured.
- During the initial setup there is a non critial error "Failed to load integration: tesy". You can ignore it as I work to remove it. 
- Setting Off and On triggers FE error which is also a fake one as Device state is updated
- Others

## Contributing

Contributions are welcome! If you encounter any issues or have feature requests, feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

