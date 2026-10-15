"""Combine independent control recipes with deterministic collision-free allocation."""

from typing import Any

from pydantic import Field

from .control import ControlSpec, control_ladder, native_edge
from .ir import Ladder, Model


class SystemSpec(Model):
    requirement: str = Field(min_length=1, max_length=16000)
    controls: list[ControlSpec] = Field(min_length=1, max_length=24)


def resources(spec: ControlSpec) -> dict[str, int]:
    return {
        "output": 3 if spec.kind == "star_delta" else 2 if spec.kind == "forward_reverse" else 1,
        "memory": (
            0
            if native_edge(spec) is not None
            else 3
            if spec.kind in {"toggle", "rising_edge", "falling_edge", "pulse"}
            else 1
            if spec.kind in {"off_delay", "star_delta"}
            else 0
        ),
        "timer": 2
        if spec.kind == "star_delta"
        else int(spec.kind in {"on_delay", "off_delay", "pulse"}),
        "counter": int(spec.kind == "counter"),
        "register_base": 2 if spec.kind in {"off_delay", "pulse", "star_delta"} else 0,
    }


def system_ladder(spec: SystemSpec) -> tuple[Ladder, dict[str, Any]]:
    used: dict[str, set[int]] = {name: set() for name in resources(spec.controls[0])}
    # Reserve ALL explicit ranges first so allocation never takes a later user's address.
    for index, control in enumerate(spec.controls):
        for name, width in resources(control).items():
            if not width or name not in control.model_fields_set:
                continue
            base = getattr(control, name)
            addresses = set(range(base, base + width))
            if addresses & used[name]:
                raise ValueError(f"Control {index}: explicit {name} resources overlap")
            used[name].update(addresses)
    networks = []
    symbols = {}
    designs = []
    limits = {"output": 253, "memory": 250, "timer": 48, "counter": 255, "register_base": 3838}
    for control in spec.controls:
        allocated = {}
        for name, width in resources(control).items():
            if not width or name in control.model_fields_set:
                continue
            base = next(
                (
                    base
                    for base in range(limits[name] + 1)
                    if not set(range(base, base + width)) & used[name]
                ),
                None,
            )
            if base is None:
                raise ValueError(f"Insufficient {name} resources for system")
            allocated[name] = base
            used[name].update(range(base, base + width))
        # Preserve model_fields_set: allocation must not turn omitted stop/reverse
        # controls into seemingly explicit FALSE conditions.
        resolved = control.model_copy(update=allocated)
        ladder, design = control_ladder(resolved)
        design["defaults_used"] = sorted(set(ControlSpec.model_fields) - control.model_fields_set)
        design["automatically_allocated"] = allocated
        networks.extend(ladder.networks)
        symbols.update(ladder.symbols)
        designs.append(design)
    return Ladder(networks=networks, symbols=symbols), {
        "requirement": spec.requirement,
        "controls": designs,
        "resources": {name: sorted(addresses) for name, addresses in used.items()},
        "assumptions": [
            "Independent recipes execute in listed order; no implicit process interlocks.",
            "Outputs and input signals are explicit; only internal addresses are allocated.",
            "Input signals may intentionally be shared.",
            "For dependent multi-step processes use the sequence tool instead.",
        ],
        "gui_import_verified": False,
    }
