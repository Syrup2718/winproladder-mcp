# WinProLadder MCP

[繁體中文](README.md) | **English**

[![CI](https://github.com/Syrup2718/winproladder-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/Syrup2718/winproladder-mcp/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/Syrup2718/winproladder-mcp)](https://github.com/Syrup2718/winproladder-mcp/releases/latest)
[![License](https://img.shields.io/github/license/Syrup2718/winproladder-mcp)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)

Turn control requirements into WinProLadder `.ldr` files with an AI agent. The MCP server can also read, inspect, compare, and safely modify existing files.

Current version: **v1.0.0** · Python 3.12+ · Windows, macOS, and Linux

> This is an independent project. It is not an official FATEK product and does not connect to or download programs to a PLC.

## Key features

- Generate start/stop, seal-in, timer, counter, forward/reverse, star-delta, and sequence controls.
- Build custom Ladder IR and encode or decode supported native FATEK instructions.
- Check the I/O contract, device ranges, duplicate writers, workspace policy, and emitted bytes before writing.
- Run a bounded offline scan model with optional acceptance cases.
- Read, compare, analyze, and export `.ldr` files without overwriting the source.
- Generate a separate CP950/Big5 component-comment `.txt` file when explicitly requested.

See the [feature overview](FEATURES.en.md) and [supported FUNC table](docs/supported-functions.md) for the current scope.

## Quick installation

Download or clone the repository, then run the installer from the project directory.

Windows PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

macOS or Linux:

```sh
sh install.sh
```

After installation, add the `winproladder` entry from `.install/mcp-config.json` or `.install/mcp-config.toml` to your MCP client, then reconnect it. See the [installation guide](docs/installation.md) for platform details and troubleshooting.

## Example request

Describe the control requirement and physical I/O explicitly:

> X0 starts the motor, X1=1 stops it, and Y0 is the seal-in output. Stop has priority. Validate the program and generate motor.ldr.

To request component comments as well:

> Also generate component comments: X0 is the start button and Y0 is the motor output.

The MCP server returns a downloadable `.ldr` file and, when explicitly requested, a separate `.txt` file. Outputs are stored under `artifacts/` by default and existing files are never overwritten.

## Verification boundary

This project provides offline file generation, parsing, and validation. The user remains responsible for WinProLadder GUI import, PLC download, and physical-machine verification. Passing the offline model does not prove behavior on real hardware.

## Documentation

- [Feature overview](FEATURES.en.md)
- [Supported FUNC instructions](docs/supported-functions.md)
- [5-minute quick start](docs/quickstart.md) (Traditional Chinese)
- [User and parameter reference](docs/reference.md) (Traditional Chinese)
- [Verification levels](docs/verification.md) (Traditional Chinese)
- [Contributing](CONTRIBUTING.md) (Traditional Chinese)

See the [changelog](CHANGELOG.md) for version history.

## License

Original source code and documentation are available under the [MIT License](LICENSE), Copyright © 2026 syrup2718.