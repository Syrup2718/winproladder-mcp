# Installation Guide

[繁體中文](installation.md) | **English**

[Home](../README.en.md) · [Quick start](quickstart.en.md)

## Requirements

- Windows, macOS, or Linux
- A writable project directory
- Network access for the first installation

The installer prepares uv, Python 3.12, an isolated environment, and locked dependencies. It does not require administrator privileges or modify the system PATH.

## Automatic Installation

Windows PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

macOS / Linux:

```sh
sh install.sh
```

Before completing, the installer performs a real stdio MCP self-check covering the tool list, `.ldr` generation, acceptance, SHA-256, file download, and component-comment output.

## Connect an MCP Client

The installer creates two configuration fragments:

- `.install/mcp-config.json`: `mcpServers` format
- `.install/mcp-config.toml`: `mcp_servers` format

Choose the format supported by your client and merge only the `winproladder` entry. Do not replace the rest of your existing configuration. The generated entry contains absolute local paths, so rerun the installer and update the configuration after moving the project or changing computers.

## Custom Workspace

Outputs go to the project's `artifacts/` directory by default. You may use a separate workspace:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Workspace "C:\Ladder Work"
```

```sh
sh install.sh "$HOME/Ladder Work"
```

A new workspace receives a strict `.winproladder-policy.json`. An existing policy is never overwritten or weakened.

## Manual Installation

Developers with uv already installed can run:

```sh
uv sync --locked --python 3.12
uv run python -m winproladder_mcp.setup check
uv run python -m winproladder_mcp.setup config --format json
```

## Updating and Removing

- After updating the source, rerun the same installation command and reconnect the client.
- Do not copy an old `.install/venv` after moving the project; reinstall in the new location.
- To remove the MCP, first delete the `winproladder` client entry, then remove `.install`. Preserve user-generated files separately.

## Troubleshooting

| Problem | Resolution |
| --- | --- |
| Network, proxy, or certificate error | Configure an organization-approved proxy and certificates, then retry. Do not disable TLS verification. |
| PowerShell blocks the script | Follow your organization's policy or use the manual uv procedure above. |
| `--locked` fails | Confirm that `pyproject.toml` and `uv.lock` come from the same revision. |
| The client cannot start the server | Confirm the configured absolute paths still exist, reinstall, and reconnect. |
| Chinese text displays incorrectly | Configuration files use UTF-8; open them with a UTF-8-capable editor. |

Installation enables `--compact-responses` by default. It shortens response content without reducing schemas or validation.
