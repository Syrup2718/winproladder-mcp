"""Generate the user-authorized, unverified start/stop LDR candidate."""

from pathlib import Path

from winproladder_mcp.research import crc16, inspect

ROOT = Path(__file__).resolve().parents[1]
payload = bytes.fromhex("41 00 A0 00 90 01 C1 00")
body = len(payload).to_bytes(2, "little") + payload + bytes.fromhex("01 00 00")
record = (
    bytes.fromhex("12 10")
    + (len(payload) + 5).to_bytes(2, "little")
    + body
    + crc16(body).to_bytes(2, "little")
)
data = (ROOT / "samples/w1.ldr").read_bytes()[:256] + record + bytes.fromhex("FF FF 00 00 00 00")
report = inspect(data)
assert report["size"] == 281
assert report["records"][0]["crc_valid"]
assert report["records"][0]["payload"] == payload.hex(" ")
output = ROOT / "artifacts/start_stop_candidate.ldr"
output.parent.mkdir(exist_ok=True)
with output.open("xb") as stream:
    stream.write(data)
assert output.read_bytes() == data
print(f"Created {output}; {len(data)} bytes; CRC=0x{crc16(body):04X}")
print("Candidate only: (Y0 OR X0) AND NOT X1 -> Y0; import validation pending.")
