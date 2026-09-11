"""Conservative semantic IR; unsupported payloads remain wholly opaque."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Contact(Model):
    device: Literal["X", "Y", "M", "T", "C"]
    address: Annotated[int, Field(strict=True, ge=0, le=65535)]
    normally_closed: bool = False


class Step(Model):
    op: Literal["load", "and", "or"]
    contact: Contact


class Coil(Model):
    device: Literal["Y", "M"] = "Y"
    address: Annotated[int, Field(strict=True, ge=0, le=65535)]


class Network(Model):
    """Left-associative logic steps, then coils. No implicit operator precedence."""

    steps: list[Step] = Field(default_factory=list, max_length=256)
    coils: list[Coil] = Field(default_factory=list, max_length=32)
    empty: bool = False


class Ladder(Model):
    networks: list[Network] = Field(min_length=1, max_length=1000)


class UnsupportedInstruction(ValueError):
    pass


# Only observed positions/device families. Address limits are an intentionally
# conservative software subset, not the PLC's physical device limits.
OPCODES: dict[tuple[Literal["load", "and", "or"], Literal["X", "Y", "M", "T", "C"], bool], int] = {
    ("load", "X", False): 0x40,
    ("load", "X", True): 0x50,
    ("and", "X", False): 0x80,
    ("and", "X", True): 0x90,
    ("or", "X", False): 0xA0,
    ("load", "Y", False): 0x41,
    ("load", "Y", True): 0x51,
    ("and", "Y", False): 0x81,
    ("and", "Y", True): 0x91,
    ("load", "M", False): 0x48,
    ("load", "M", True): 0x58,
    ("and", "M", False): 0x88,
    ("load", "T", False): 0x42,
    ("load", "C", False): 0x43,
}


def operand(device: str, address: int) -> int:
    if (device == "X" and 0 <= address <= 10) or (device == "Y" and 0 <= address <= 9):
        return address
    if device == "M" and address in {0, 2, 6}:
        return address + 0x10
    if device in {"T", "C"} and address == 1:
        return address
    raise UnsupportedInstruction(f"Unsupported device/address: {device}{address}")


def compile_network(network: Network) -> bytes:
    if network.empty:
        if network.steps or network.coils:
            raise UnsupportedInstruction("Empty network cannot have steps or coils")
        return bytes.fromhex("5feb")
    if not network.steps or not network.coils:
        raise UnsupportedInstruction("Network requires logic and at least one coil")
    payload = bytearray()
    for index, step in enumerate(network.steps):
        if (index == 0) != (step.op == "load"):
            raise UnsupportedInstruction("First step must be load; later steps must be and/or")
        contact = step.contact
        key = (step.op, contact.device, contact.normally_closed)
        if key not in OPCODES:
            raise UnsupportedInstruction(f"Unsupported contact position: {key}")
        payload.extend((OPCODES[key], operand(contact.device, contact.address)))
    for coil in network.coils:
        payload.extend((0xC1 if coil.device == "Y" else 0xC8, operand(coil.device, coil.address)))
    return bytes(payload)


def decode_network(payload: bytes) -> Network | None:
    if payload == bytes.fromhex("5feb"):
        return Network(empty=True)
    if len(payload) % 2:
        return None
    inverse = {value: key for key, value in OPCODES.items()}
    steps = []
    coils = []
    try:
        for i in range(0, len(payload), 2):
            code, value = payload[i : i + 2]
            if code in {0xC1, 0xC8}:
                device: Literal["Y", "M"] = "Y" if code == 0xC1 else "M"
                coils.append(Coil(device=device, address=value if device == "Y" else value - 0x10))
            elif code in inverse and not coils:
                op, family, nc = inverse[code]
                steps.append(
                    Step(
                        op=op,
                        contact=Contact(
                            device=family,
                            address=value - 0x10 if family == "M" else value,
                            normally_closed=nc,
                        ),
                    )
                )
            else:
                return None
        network = Network(steps=steps, coils=coils)
        return network if compile_network(network) == payload else None
    except ValueError:
        return None


def start_stop(stop_normally_closed: bool = True) -> Ladder:
    return Ladder(
        networks=[
            Network(
                steps=[
                    Step(op="load", contact=Contact(device="Y", address=0)),
                    Step(op="or", contact=Contact(device="X", address=0)),
                    Step(
                        op="and",
                        contact=Contact(
                            device="X", address=1, normally_closed=stop_normally_closed
                        ),
                    ),
                ],
                coils=[Coil(device="Y", address=0)],
            )
        ]
    )


def validation(ladder: Ladder) -> dict[str, object]:
    errors = []
    payloads = []
    for index, network in enumerate(ladder.networks):
        try:
            payloads.append(compile_network(network).hex(" "))
        except ValueError as error:
            errors.append(f"N{index:03}: {error}")
    verified = payloads == ["41 00 a0 00 90 01 c1 00"] and not errors
    coils = [f"{c.device}{c.address}" for n in ladder.networks for c in n.coils]
    warnings = [] if verified else ["Composition has not been verified by WinProLadder import."]
    if len(coils) != len(set(coils)):
        warnings.append("Repeated coils: later networks may overwrite earlier network results.")
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "payloads": payloads,
        "import_verified": verified,
        "verification_scope": (
            "User reported successful import of exact X1-NC start/stop payload; "
            "no PLC runtime verification."
        ),
    }


def simulate(
    ladder: Ladder, inputs: list[dict[str, bool]], initial: dict[str, bool]
) -> list[dict[str, bool]]:
    """Boolean-only scan model for this IR, not a PLC emulator."""
    result = validation(ladder)
    if not result["valid"]:
        raise UnsupportedInstruction(str(result["errors"]))
    if len(inputs) > 256 or len(initial) > 128:
        raise ValueError("Simulation limited to 256 scans and 128 initial devices")
    for key, value in initial.items():
        if not key or not key[1:].isdigit() or type(value) is not bool:
            raise ValueError("Initial state requires device names and boolean values")
        operand(key[0], int(key[1:]))
    state = dict(initial)
    trace = []
    for scan in inputs:
        if len(scan) > 11:
            raise ValueError("At most X0..X10 per scan")
        for key, value in scan.items():
            if not key.startswith("X") or not key[1:].isdigit() or type(value) is not bool:
                raise ValueError("Scan inputs must be boolean X devices")
            operand("X", int(key[1:]))
        # Each scan is a fresh input snapshot; unspecified X inputs are false.
        for address in range(11):
            state[f"X{address}"] = scan.get(f"X{address}", False)
        for network in ladder.networks:
            if network.empty:
                continue
            power = False
            for step in network.steps:
                contact = step.contact
                active = state.get(f"{contact.device}{contact.address}", False)
                active = not active if contact.normally_closed else active
                if step.op == "load":
                    power = active
                elif step.op == "and":
                    power = power and active
                else:
                    power = power or active
            for coil in network.coils:
                state[f"{coil.device}{coil.address}"] = power
        trace.append(dict(state))
    return trace
