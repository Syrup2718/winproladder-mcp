"""Bounded, local Boolean identities; never reorder PLC networks or outputs."""

from .logic import Expr, negate


def simplify(expr: Expr) -> Expr:
    """Simplify pure contact expressions without distributive expansion."""
    if expr.op not in {"and", "or"}:
        return expr
    identity, absorbing = ("true", "false") if expr.op == "and" else ("false", "true")
    dual = "or" if expr.op == "and" else "and"
    terms: list[Expr] = []
    for item in expr.items:
        item = simplify(item)
        for child in item.items if item.op == expr.op else (item,):
            if child.op == absorbing:
                return Expr(absorbing)
            if child.op != identity and child not in terms:
                terms.append(child)
    if any(negate(t) in terms for t in terms):
        return Expr(absorbing)
    # A OR (A AND B) = A; dual rule and subset absorption too.
    groups = [frozenset(t.items if t.op == dual else (t,)) for t in terms]
    terms = [
        t
        for i, t in enumerate(terms)
        if not any(
            g < groups[i] or (g == groups[i] and j < i) for j, g in enumerate(groups) if j != i
        )
    ]
    if not terms:
        return Expr(identity)
    if len(terms) == 1:
        return terms[0]
    # Factor only terms common to every branch; no exponential DNF conversion.
    groups_ordered = [list(t.items) if t.op == dual else [t] for t in terms]
    common = [t for t in groups_ordered[0] if all(t in g for g in groups_ordered[1:])]
    if common:
        remaining = []
        for group in groups_ordered:
            rest = tuple(t for t in group if t not in common)
            remaining.append(rest[0] if len(rest) == 1 else Expr(dual, items=rest))
        return simplify(Expr(dual, items=(*common, Expr(expr.op, items=tuple(remaining)))))
    return Expr(expr.op, items=tuple(terms))


def contact_count(expr: Expr) -> int:
    return int(expr.op == "contact") + sum(contact_count(t) for t in expr.items)
