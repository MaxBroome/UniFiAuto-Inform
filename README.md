# UniFi Auto-Inform Tool

This Python script helps you discover Ubiquiti devices on your network and provides the option to run a `set-inform` command on all of the discovered devices at once.
## Prerequisites

- Python 3.11
- Paramiko library (`pip install paramiko`)

## Usage

1. Clone the repository or download the script file to your local machine.
2. Open a terminal or command prompt and navigate to the directory where the script is located.
3. Run the script using the Python interpreter: `python UniFi Device Discovery and Inform Tool.py`.
4. The script will run and search for Ubiquiti devices on your network and display the results.
5. If you choose to run the `set-inform` command, follow the prompts to enter the required information, such as your UniFi controller's IP/FQDN and optional custom SSH credentials.

## Features

- Automatic discovery of Ubiquiti devices using ARP scanning.
- Multi-threaded scanning for faster discovery.
- Option to run a `set-inform` command on all of the discovered devices.
- Customizable SSH credentials for connecting to the devices.

## Disclaimer

- Use this script responsibly and ensure that you have proper authorization to interact with all of the Ubiquiti devices on the network.
- The script is provided as-is without any warranty. Use it at your own risk (especially the .exe installer file/script).

## Contributing

Contributions are welcome and encouraged! If you have any suggestions, bug reports, or feature requests, please open an issue or submit a pull request.

## License

[MIT License](LICENSE)
