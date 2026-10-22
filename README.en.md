<div align="center">
  <h1>WinProLadder MCP</h1>
  <p><strong>Turn control requirements into WinProLadder <code>.ldr</code> files with an AI agent</strong></p>
  <p>Read, inspect, compare, and safely modify existing files</p>
  <p>
    <a href="https://github.com/Syrup2718/winproladder-mcp/releases/latest"><img alt="Release" src="https://img.shields.io/github/v/release/Syrup2718/winproladder-mcp"></a>
    <a href="LICENSE"><img alt="License" src="https://img.shields.io/github/license/Syrup2718/winproladder-mcp"></a>
    <a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white"></a>
    <a href="https://github.com/Syrup2718/winproladder-mcp/stargazers">
    <img alt="GitHub Stars" src="https://img.shields.io/github/stars/Syrup2718/winproladder-mcp">
    </a>
    <a href="https://github.com/Syrup2718/winproladder-mcp">
    <img alt="Repo Size" src="https://img.shields.io/github/repo-size/Syrup2718/winproladder-mcp">
    </a>
  </p>
  <p><a href="README.md">繁體中文</a> · <strong>English</strong></p>
</div>

<p align="center">
  <a href="docs/quickstart.en.md">Quick start</a> ·
  <a href="FEATURES.en.md">Features</a> ·
  <a href="docs/supported-functions.md">FUNC support</a> ·
  <a href="docs/README.md">Documentation</a>
</p>

> [!IMPORTANT]
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

### Windows PowerShell

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

### macOS / Linux

```sh
sh install.sh
```

After installation, add the `winproladder` entry from `.install/mcp-config.json` or `.install/mcp-config.toml` to your MCP client, then reconnect it. See the [installation guide](docs/installation.en.md) for platform details and troubleshooting.

## Example request

Describe the control requirement and physical I/O explicitly:

> X0 starts the motor, X1=1 stops it, and Y0 is the seal-in output. Stop has priority. Validate the program and generate motor.ldr.

To request component comments as well:

> Also generate component comments: X0 is the start button and Y0 is the motor output.

The MCP server returns a downloadable `.ldr` file and, when explicitly requested, a separate `.txt` file. Outputs are stored under `artifacts/` by default and existing files are never overwritten.

## Verification boundary

This project provides offline file generation, parsing, and validation. The user remains responsible for WinProLadder GUI import, PLC download, and physical-machine verification. Passing the offline model does not prove behavior on real hardware.

## Documentation

| Category | Documents |
| --- | --- |
| Getting started | [5-minute quick start](docs/quickstart.en.md) · [Installation](docs/installation.en.md) |
| Features | [Feature overview](FEATURES.en.md) · [FUNC support table](docs/supported-functions.md) |
| Reference | [User and parameter reference](docs/reference.en.md) · [Documentation index](docs/README.md) |
| Verification and development | [Verification levels](docs/verification.en.md) · [Contributing](CONTRIBUTING.en.md) |

See the [changelog](CHANGELOG.en.md) for version history.

## License

Original source code and documentation are available under the [MIT License](LICENSE), Copyright © 2026 syrup2718.
