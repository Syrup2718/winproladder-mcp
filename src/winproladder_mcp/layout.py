"""Generate flat connected logic; keep the raw compiler for forensic reads."""

from typing import Any

from .ir import Coil, Counter, Ladder, Network, Timer, compile_network, network_expression
from .logic import Expr, compile_expression, contacts, expression_text, negate, parse_expression
from .optimize import contact_count, simplify


def expressions(network: Network) -> list[Expr]:
    if network.empty:
        return []
    if isinstance(network.block, Timer):
        return [parse_expression(network.block.enable)]
    if isinstance(network.block, Counter):
        return [
            parse_expression(network.block.pulse),
            negate(parse_expression(network.block.clear)),
        ]
    if network.action is not None:
        enable = getattr(network.action, "enable", None)
        return [] if enable is None else [parse_expression(enable)]
    return [network_expression(network)]


def memory_used(ladder: Ladder) -> set[int]:
    names = {f"{c.device}{c.address}" for n in ladder.networks for c in n.coils}
    for network in ladder.networks:
        for expr in expressions(network):
            names.update(contacts(expr))
    return {int(name[1:]) for name in names if name.startswith("M")}


def requires_lowering(expr: Expr) -> bool:
    raw = compile_expression(expr)
    return any(
        raw[i : i + 2]
        in {b"\xe2\x00", b"\xe4\x43", b"\x5f\xe8", b"\x7f\xe8", b"\x9f\xe8", b"\xbf\xe8"}
        for i in range(0, len(raw), 2)
    )


def needs_lowering(network: Network, index: int, expr: Expr) -> bool:
    # Counter CLR uses inverted polarity. Its sampled 7FE8 encodes the direct
    # CLR rail, not an OPEN contact drawn inside a Boolean rung.
    if isinstance(network.block, Counter) and index == 1 and expr.op == "false":
        return False
    return requires_lowering(expr)


def lower_ladder(ladder: Ladder, reserved: set[int] | None = None) -> tuple[Ladder, dict[str, Any]]:
    occupied = memory_used(ladder) | (reserved or set())
    helpers: list[int] = []
    output: list[Network] = []
    mapping = []
    simplifications = []
    symbols = dict(ladder.symbols)
    # Reuse a declared device for a contradiction; never invent a physical input.
    source_names = {f"{c.device}{c.address}" for n in ladder.networks for c in n.coils}
    source_names.update(
        f"{'T' if isinstance(n.block, Timer) else 'C'}{n.block.address}"
        for n in ladder.networks
        if n.block is not None
    )
    source_names.update(d for n in ladder.networks for e in expressions(n) for d in contacts(e))
    contradiction = sorted(source_names)[0] if source_names else "M0"

    def allocate() -> int:
        address = next((i for i in range(256) if i not in occupied), None)
        if address is None:
            raise ValueError("No free M0..M255 for connected layout; no file written")
        occupied.add(address)
        helpers.append(address)
        return address

    def lower(expr: Expr) -> Expr:
        if expr.op == "false":
            # Wired contradiction rather than the special OPEN pseudo-contact.
            return Expr(
                "and", items=(Expr("contact", contradiction), Expr("contact", contradiction, True))
            )
        if expr.op in {"contact", "true"}:
            return expr

        def flatten(node: Expr) -> list[Expr]:
            if node.op == expr.op:
                return [term for child in node.items for term in flatten(child)]
            return [node]

        children = flatten(expr)
        # CH01 section 1.7: put a compound branch first. The first branch
        # uses ORG; following single contacts need only AND/OR, not LD joins.
        compound = next((i for i, child in enumerate(children) if child.items), None)
        if compound is not None:
            children.insert(0, children.pop(compound))
        leaves = []
        for position, child in enumerate(children):
            child = lower(child)
            if position > 0 and child.op in {"and", "or"}:
                address = allocate()
                symbols[f"M{address}"] = f"Boolean branch: {expression_text(child)}"
                output.append(
                    Network(
                        condition=expression_text(child),
                        coils=[Coil(device="M", address=address)],
                        comment=symbols[f"M{address}"],
                    )
                )
                child = Expr("contact", f"M{address}")
            leaves.append(child)
        return Expr(expr.op, items=tuple(leaves))

    for index, original in enumerate(ladder.networks):
        compile_network(original)
        first = len(output)
        network = original.model_copy(deep=True)
        exprs = expressions(original)
        simplified = [simplify(expr) for expr in exprs]
        if any(
            compile_expression(a) != compile_expression(b)
            for a, b in zip(exprs, simplified, strict=True)
        ):
            simplifications.append(index)
        fixed = [
            lower(expr) if needs_lowering(original, i, expr) else expr
            for i, expr in enumerate(simplified)
        ]
        changed = any(
            compile_expression(a) != compile_expression(b)
            for a, b in zip(exprs, fixed, strict=True)
        )
        if changed:
            if isinstance(network.block, Timer):
                network.block.enable = expression_text(fixed[0])
            elif isinstance(network.block, Counter):
                network.block.pulse = expression_text(fixed[0])
                network.block.clear = expression_text(negate(fixed[1]))
            elif network.action is not None:
                network.action.enable = expression_text(fixed[0])  # type: ignore[union-attr]
            else:
                network.steps = []
                network.condition = expression_text(fixed[0])
        output.append(network)
        if changed:
            mapping.append(
                {"source_network": index, "first_network": first, "output_network": len(output) - 1}
            )
        if len(output) > 1000:
            raise ValueError("Connected layout exceeds 1000 networks; no file written")
    result = Ladder(networks=output, symbols=symbols)
    if any(
        needs_lowering(n, i, expr) for n in result.networks for i, expr in enumerate(expressions(n))
    ):
        raise ValueError("Connected-layout postcondition failed; no file written")
    return result, {
        "normalized_networks": [m["source_network"] for m in mapping],
        "network_map": mapping,
        "helper_devices": [f"M{i}" for i in helpers],
        "simplified_networks": simplifications,
        "metrics": {
            "networks_before": len(ladder.networks),
            "networks_after": len(result.networks),
            "contacts_before": sum(
                contact_count(e) for n in ladder.networks for e in expressions(n)
            ),
            "contacts_after": sum(
                contact_count(e) for n in result.networks for e in expressions(n)
            ),
            "payload_bytes_before": sum(len(compile_network(n)) for n in ladder.networks),
            "payload_bytes_after": sum(len(compile_network(n)) for n in result.networks),
        },
        "policy": "Flat connected logic; no nested joins or Boolean OPEN constants; "
        "sampled counter CLR polarity preserved",
    }


def safe_ladder(ladder: Ladder) -> Ladder:
    return lower_ladder(ladder)[0]
