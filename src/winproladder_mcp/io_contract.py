"""Explicit physical I/O contract; internal allocation cannot extend field wiring."""

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class IOContract(BaseModel):
    model_config = ConfigDict(extra="forbid")
    inputs: list[str] = Field(max_length=256)
    outputs: list[str] = Field(max_length=256)

    @model_validator(mode="after")
    def canonical(self) -> "IOContract":
        for family, values in (("X", self.inputs), ("Y", self.outputs)):
            if len(values) != len(set(values)):
                raise ValueError("I/O contract contains duplicate addresses")
            for value in values:
                if not re.fullmatch(rf"{family}(0|[1-9][0-9]{{0,2}})", value):
                    raise ValueError(f"Expected canonical {family} address, got {value!r}")
                if int(value[1:]) > 255:
                    raise ValueError(f"I/O address exceeds supported range: {value}")
        return self


def check_io(devices: set[str], contract: IOContract) -> dict[str, Any]:
    actual = {d for d in devices if d.startswith(("X", "Y"))}
    allowed = set(contract.inputs) | set(contract.outputs)
    extra = sorted(actual - allowed)
    if extra:
        raise ValueError(f"Undeclared physical I/O: {', '.join(extra)}; no file written")
    return {
        "allowed": contract.model_dump(),
        "used": sorted(actual),
        "unused": sorted(allowed - actual),
        "extra": [],
    }
