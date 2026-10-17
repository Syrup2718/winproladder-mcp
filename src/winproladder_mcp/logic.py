"""Inferred Boolean stack compiler. No eval and no external code execution."""

import ast
import re
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Expr:
    op: str
    name: str = ""
    nc: bool = False
    items: tuple["Expr", ...] = ()


def bit_address(name: str) -> int:
    if not re.fullmatch(r"[XYMTC](0|[1-9][0-9]{0,3})", name):
        raise ValueError(f"Invalid device {name!r}; use X/Y/T/C0..255 or M0..1911")
    address = int(name[1:])
    if address > (1911 if name[0] == "M" else 255):
        raise ValueError(f"Device outside supported X/Y/T/C0..255 or M0..1911 range: {name}")
    return {"X": 0, "Y": 0x100, "T": 0x200, "C": 0x300, "M": 0x810}[name[0]] + address


def device_name(value: int) -> str:
    if 0x810 <= value <= 0xF87:
        return f"M{value - 0x810}"
    if 0 <= value <= 0x3FF:
        return f"{'XYTC'[value >> 8]}{value & 255}"
    raise ValueError(f"Unknown device operand 0x{value:03X}")


def negate(expr: Expr) -> Expr:
    if expr.op == "contact":
        return Expr("contact", expr.name, not expr.nc)
    if expr.op in {"true", "false"}:
        return Expr("false" if expr.op == "true" else "true")
    return Expr("or" if expr.op == "and" else "and", items=tuple(negate(x) for x in expr.items))


def parse_expression(expression: str) -> Expr:
    if len(expression) > 4096:
        raise ValueError("Expression exceeds 4096 characters")
    normalized = expression.strip()
    if normalized == "always_on":
        normalized = "TRUE"
    for word, symbol in [("AND", "&"), ("OR", "|"), ("NOT", "~")]:
        normalized = re.sub(rf"\b{word}\b", symbol, normalized, flags=re.IGNORECASE)
    normalized = normalized.replace("!", "~")
    try:
        tree = ast.parse(normalized, mode="eval")
    except (SyntaxError, RecursionError) as error:
        raise ValueError("Invalid expression; use devices, AND/OR/NOT and parentheses") from error
    count = 0

    def convert(node: ast.AST, depth: int = 0) -> Expr:
        nonlocal count
        count += 1
        if count > 256 or depth > 32:
            raise ValueError("Expression limited to 256 nodes and depth 32")
        if isinstance(node, ast.Name):
            name = node.id.upper()
            if name in {"TRUE", "FALSE"}:
                return Expr(name.lower())
            bit_address(name)
            return Expr("contact", name)
        if isinstance(node, ast.Constant) and type(node.value) is bool:
            return Expr("true" if node.value else "false")
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Invert):
            return negate(convert(node.operand, depth + 1))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitAnd | ast.BitOr):
            # Flat chains must not consume the nested-branch depth budget.
            operator = type(node.op)
            tail = [node.right]
            head = node.left
            while isinstance(head, ast.BinOp) and type(head.op) is operator:
                count += 1
                if count > 256:
                    raise ValueError("Expression limited to 256 nodes and depth 32")
                tail.append(head.right)
                head = head.left
            return Expr(
                "and" if isinstance(node.op, ast.BitAnd) else "or",
                items=tuple(convert(item, depth + 1) for item in [head, *reversed(tail)]),
            )
        raise ValueError("Expression permits only devices, TRUE/FALSE, AND/OR/NOT and parentheses")

    return convert(tree.body)


def instruction(expr: Expr, base: int) -> bytes:
    if expr.op == "contact":
        value, nc = bit_address(expr.name), expr.nc
    elif expr.op in {"true", "false"}:
        value, nc = 0xFE8, expr.op == "false"
    else:
        raise ValueError("Expected a contact")
    return bytes((base + (0x10 if nc else 0) + (value >> 8), value & 255))


def compile_expression(expr: Expr, *, nested: bool = False, depth: int = 0) -> bytes:
    if depth > 32:
        raise ValueError("Branch depth exceeds 32")
    if expr.op in {"contact", "true", "false"}:
        return instruction(expr, 0x60 if nested else 0x40)
    if expr.op not in {"and", "or"} or len(expr.items) < 2:
        raise ValueError("Invalid Boolean tree")
    result = compile_expression(expr.items[0], nested=nested, depth=depth + 1)
    for child in expr.items[1:]:
        if child.op in {"contact", "true", "false"}:
            result += instruction(child, 0x80 if expr.op == "and" else 0xA0)
        else:
            result += compile_expression(child, nested=True, depth=depth + 1)
            result += bytes.fromhex("e200" if expr.op == "and" else "e443")
    return result


def decode_expression(data: bytes) -> Expr:
    if not data or len(data) % 2:
        raise ValueError("Invalid expression bytes")
    stack: list[Expr] = []
    current: Expr | None = None
    for i in range(0, len(data), 2):
        word = data[i : i + 2]
        if word in {b"\xe2\x00", b"\xe4\x43"}:
            if current is None or not stack:
                raise ValueError("Branch stack underflow")
            current = Expr("and" if word == b"\xe2\x00" else "or", items=(stack.pop(), current))
            continue
        code, low = word
        base = code & 0xE0
        value = ((code & 0x0F) << 8) + low
        nc = bool(code & 0x10)
        term = (
            Expr("false" if nc else "true")
            if value == 0xFE8
            else Expr("contact", device_name(value), nc)
        )
        if base == 0x40:
            if current is not None:
                raise ValueError("Unexpected load")
            current = term
        elif base == 0x60:
            if current is None or len(stack) >= 32:
                raise ValueError("Invalid branch stack")
            stack.append(current)
            current = term
        elif base in {0x80, 0xA0} and current is not None:
            current = Expr("and" if base == 0x80 else "or", items=(current, term))
        else:
            raise ValueError("Unknown expression instruction")
    if stack or current is None:
        raise ValueError("Unclosed branch")
    return current


def expression_text(expr: Expr) -> str:
    if expr.op == "contact":
        return ("NOT " if expr.nc else "") + expr.name
    if expr.op in {"true", "false"}:
        return expr.op.upper()
    return "(" + f" {expr.op.upper()} ".join(expression_text(x) for x in expr.items) + ")"


def evaluate(expr: Expr, state: Mapping[str, bool | int]) -> bool:
    if expr.op == "contact":
        value = bool(state.get(expr.name, False))
        return not value if expr.nc else value
    if expr.op in {"true", "false"}:
        return expr.op == "true"
    values = (evaluate(x, state) for x in expr.items)
    return all(values) if expr.op == "and" else any(values)


def contacts(expr: Expr) -> set[str]:
    if expr.op == "contact":
        return {expr.name}
    return set().union(*(contacts(x) for x in expr.items))
