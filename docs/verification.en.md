# Verification Scope

[繁體中文](verification.md) | **English**

[Documentation index](README.md) · [Feature list](../FEATURES.en.md)

This project records encoding, model, software, and hardware verification separately. Passing a CRC check or reusing a header from one PLC model does not automatically establish GUI or PLC verification for a new feature.

## Verification Levels

| Level | Confirms | Does not mean |
| --- | --- | --- |
| Container and encoding | Length, CRC, raw-byte round trip, and recognizable records | The instruction behaves correctly at runtime |
| Static checks | Schema, parameter ranges, I/O, register spans, and workspace policy | Every hardware condition and dynamic value is known |
| Independent offline model | Separate modeling of a specific requirement or algorithm | The MCP includes the same simulation |
| Built-in MCP simulation | Implemented Boolean and Timer/Counter scan models | Every native function can be simulated |
| MCP integration | Real stdio calls, file generation, resource download, and SHA-256 | WinProLadder has imported the file |
| GUI import | Manual confirmation for a specific file and project | Every variation or physical PLC behavior works |
| Physical PLC | Execution on a specific model, project, and site configuration | Untested combinations behave identically |

## Samples and Tests

The [sample directory](../samples/README.md) contains **31 exports and 219 networks**. `tests/test_sample_integrity.py` protects the original hashes. Format round trips, semantic decoding, generation policy, and MCP delivery are tested separately. Sample decoding coverage does not mean every sample complies with the current generation policy.

See the [test guide](../tests/README.md) for categories and commands. Test counts in instruction-research documents are snapshots from that work, not a continuously updated total. Rerun the tests for the current commit.

## Existing Manual Confirmations

- Self-hold template: `(Y0 OR X0) AND NOT X1 → Y0`, 281 bytes, payload `4100A0009001C100`, record CRC `0x5048`. Other addresses, polarities, and headers do not inherit this status automatically.
- Traffic-light import baseline: `tests/fixtures/traffic_light-connected-verified.ldr`, 25 networks, 713 bytes, SHA-256 `a4694aa8db73737ada925742ebc6ba164aee52e56137bd5ae201017c203b3b94`. It contains historical helper-M structures and is retained for defect and import comparison; it does not represent current generation policy.
- Comparison contacts: selected FUN170–175 files were confirmed in first-segment and series positions. Original samples and automated tests remain under `samples/` and `tests/`.

Other GUI screenshots help identify original exports but do not prove importability of reconstructed files or new parameter variants. Anything without recorded physical PLC verification must not be labeled as physically verified.

## Reproduction

```powershell
uv run python -m pytest -q
uv run python -m winproladder_mcp.setup check
```

`setup check` uses a temporary workspace. To retain integration artifacts, run `scripts/verify_release.py` as described in the [development guide](development.md). The script name does not mean it builds or publishes a release.

Historical `artifacts/` reports mentioned in research documents are local outputs and are not published with Git. Publicly traceable evidence consists of repository samples, tests, IR examples, and recorded hashes. See [Features](../FEATURES.en.md) and the [documentation index](README.md) for instruction-level limits.
