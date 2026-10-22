# Quick Start

[繁體中文](quickstart.md) | **English**

[Home](../README.en.md) · [Installation](installation.en.md) · [Features](../FEATURES.en.md)

## 1. Install

Run the script for your platform from the project directory:

```powershell
# Windows
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

```sh
# macOS / Linux
sh install.sh
```

After `PASS` and `Setup complete`, add the `winproladder` entry from `.install/mcp-config.json` or `.install/mcp-config.toml` to your MCP client, then reconnect.

## 2. Describe the Requirement

State the I/O, active polarity, priority, and timing explicitly:

> X0 starts and latches Y0. X1=1 stops it, with stop taking priority. Validate the design and generate motor.ldr.

The MCP checks the X/Y addresses allowed by the request. It does not invent inputs, outputs, or external clocks.

## 3. Download the Files

The result includes a download link for the `.ldr` file and normally saves it under `artifacts/`. High-level recipes also produce a `.ldr.design.json` sidecar containing design assumptions and device allocation. Existing files are not overwritten.

To request component comments, say so explicitly:

> Add component comments: X0 is the start button and Y0 is the motor output.

You will receive a separate CP950/Big5 `.txt` file. It does not modify the `.ldr` file.

## 4. User-Side Acceptance

Import the `.ldr` file into WinProLadder, confirm the PLC model, I/O, and timing settings, then download it to a PLC if physical testing is required. The user performs these steps; offline acceptance is not the same as GUI import or physical PLC verification.

## FAQ

| Problem | Suggestion |
| --- | --- |
| The client cannot see the tools | Rerun the installer, update the client configuration, and reconnect. |
| I/O validation fails | Check the addresses, polarity, and `io_contract`. |
| An instruction cannot be generated or simulated | See [Features](../FEATURES.en.md); encoding and simulation coverage differ. |
| The output name already exists | Choose a new output filename. |

See the [usage reference](reference.en.md) for advanced parameters.
