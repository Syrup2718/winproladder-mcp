"""Structured, fail-closed diagnostics for the existing LDR generation pipeline."""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

GenerationCode = Literal[
    "INVALID_IR",
    "UNSUPPORTED_INSTRUCTION",
    "UNSUPPORTED_OPERAND",
    "UNSUPPORTED_NETWORK_STRUCTURE",
    "MISSING_ENCODING_EVIDENCE",
    "ENCODING_FAILURE",
    "ARTIFACT_VALIDATION_FAILURE",
    "IMPORT_UNVERIFIED",
]
GENERATION_CODES: tuple[GenerationCode, ...] = (
    "INVALID_IR",
    "UNSUPPORTED_INSTRUCTION",
    "UNSUPPORTED_OPERAND",
    "UNSUPPORTED_NETWORK_STRUCTURE",
    "MISSING_ENCODING_EVIDENCE",
    "ENCODING_FAILURE",
    "ARTIFACT_VALIDATION_FAILURE",
    "IMPORT_UNVERIFIED",
)


class GenerationDiagnostic(BaseModel):
    """Stable failure details returned to MCP clients without weakening any gate."""

    model_config = ConfigDict(extra="forbid")

    code: GenerationCode
    stage: str
    network_index: int | None
    instruction: str | None
    operands: dict[str, Any] | None
    reason: str
    safe_to_retry: bool
    retry_condition: str | None
    verified_alternative: str | None
    next_step: str
    artifact_created: Literal[False] = False
    verification_level: str
    validation_levels: dict[str, str]
    missing_evidence: list[str]
    recovery: dict[str, Any]
    original_request_preserved: Literal[True] = True


class GenerationFailure(ValueError):
    """Existing generation exception enriched with a serializable diagnosis."""

    def __init__(self, diagnostic: GenerationDiagnostic):
        self.diagnostic = diagnostic
        super().__init__(diagnostic.reason)


def _as_mapping(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        result = dump(exclude_none=True)
        return result if isinstance(result, dict) else None
    return None


def _networks(ladder: Any) -> list[Any]:
    mapping = _as_mapping(ladder)
    networks = mapping.get("networks") if mapping is not None else getattr(ladder, "networks", None)
    return networks if isinstance(networks, list) else []


def _network_context(
    ladder: Any, index: int | None
) -> tuple[int | None, str | None, dict[str, Any] | None]:
    networks = _networks(ladder)
    candidates = [index] if index is not None else list(range(len(networks)))
    for candidate in candidates:
        if candidate is None or not 0 <= candidate < len(networks):
            continue
        network = _as_mapping(networks[candidate])
        if network is None:
            continue
        for field in ("action", "block", "edge"):
            instruction = _as_mapping(network.get(field))
            if instruction is not None:
                kind = instruction.get("type") or instruction.get("kind") or field
                operands = {key: value for key, value in instruction.items() if key != "type"}
                return candidate, str(kind), operands
        if network.get("condition") is not None or network.get("coils"):
            return (
                candidate,
                "relay_network",
                {key: network[key] for key in ("condition", "coils") if key in network},
            )
    return None, None, None


def _validation_error(error: Exception) -> tuple[str, int | None, str | None, str | None]:
    if not isinstance(error, ValidationError):
        return str(error), None, None, None
    issues = error.errors(include_url=False)
    if not issues:
        return str(error), None, None, None
    issue = issues[0]
    location = list(issue.get("loc", ()))
    network_index = None
    if "networks" in location:
        position = location.index("networks") + 1
        if position < len(location) and isinstance(location[position], int):
            network_index = int(location[position])
    operand = next(
        (
            str(item)
            for item in reversed(location)
            if isinstance(item, str)
            and item
            not in {
                "networks",
                "action",
                "block",
                "edge",
                "function-after[validate(), Network]",
            }
        ),
        None,
    )
    return str(issue.get("msg", str(error))), network_index, operand, str(issue.get("type", ""))


def _code_for(
    reason: str, stage: str, error_type: str | None, operand: str | None
) -> GenerationCode:
    text = reason.lower()
    if stage == "import_verification" or "import-verified" in text:
        return "IMPORT_UNVERIFIED"
    if "acceptance failed" in text or stage == "artifact_validation":
        return "ARTIFACT_VALIDATION_FAILURE"
    if error_type in {"union_tag_invalid", "union_tag_not_found"}:
        return "UNSUPPORTED_INSTRUCTION"
    if any(
        marker in text
        for marker in (
            "nested/crossed",
            "nested loop",
            "without matching",
            "missing next",
            "next without",
            "break requires",
            "helper",
            "connected layout",
            "connected-layout",
            "network limit",
            "multiple device writers",
            "single-writer",
            "architecture",
            "m-to-m",
        )
    ):
        return "UNSUPPORTED_NETWORK_STRUCTURE"
    if any(
        marker in text
        for marker in (
            "decode-only",
            "encoding remains",
            "encoding is not established",
            "not established by",
            "unresolved",
            "unencoded mode",
            "exact complete",
        )
    ):
        return "MISSING_ENCODING_EVIDENCE"
    if operand is not None or any(
        marker in text
        for marker in (
            "operand",
            "address exceeds",
            "outside supported",
            "currently supports",
            "currently requires",
            "requires register",
            "constant division",
            "undeclared physical i/o",
        )
    ):
        return "UNSUPPORTED_OPERAND"
    if stage == "encoding":
        return "ENCODING_FAILURE"
    return "INVALID_IR"


def _verification(stage: str) -> tuple[str, dict[str, str]]:
    levels = {
        "source_ir": "not_run",
        "lowered_ir": "not_run",
        "emitted_bytes": "not_run",
        "mcp_simulation": "not_run",
        "gui_import": "not_verified",
        "physical_plc": "not_verified",
    }
    if stage in {"source_validation", "lowering"}:
        levels["source_ir"] = "failed" if stage == "source_validation" else "passed"
        return "source_ir", levels
    if stage in {"lowered_validation", "encoding", "import_verification"}:
        levels["source_ir"] = "passed"
        levels["lowered_ir"] = "failed" if stage == "lowered_validation" else "passed"
        return "lowered_ir", levels
    if stage == "artifact_validation":
        levels["source_ir"] = "passed"
        levels["lowered_ir"] = "passed"
        levels["emitted_bytes"] = "failed"
        return "emitted_bytes_failed", levels
    return "request_only", levels


def _advice(code: GenerationCode) -> tuple[bool, str | None, str | None, str, list[str]]:
    if code == "INVALID_IR":
        return (
            True,
            "Correct the reported schema or request field, then submit a new request.",
            None,
            "Use get_design_guide(detail=true), preserve the original requirement, and "
            "correct only the invalid field.",
            [],
        )
    if code == "UNSUPPORTED_INSTRUCTION":
        return (
            False,
            None,
            None,
            "Query get_instruction_capabilities. If the PLC instruction is required, provide a "
            "minimal native WinProLadder export before adding codec support.",
            ["Exact native instruction bytes for the target CPU/profile and operand form"],
        )
    if code == "UNSUPPORTED_OPERAND":
        return (
            False,
            None,
            None,
            "Keep the requested operand contract. Query the instruction family limits and "
            "provide a same-instruction export for the missing operand form.",
            [
                "Same instruction exported with the requested operand bank, mode, and "
                "boundary values"
            ],
        )
    if code == "UNSUPPORTED_NETWORK_STRUCTURE":
        return (
            False,
            None,
            None,
            "Simplify only with validate_ladder-confirmed Boolean equivalence, or provide a "
            "native export demonstrating the required connected structure.",
            [
                "Native export of the complete network topology when existing lowering cannot "
                "encode it"
            ],
        )
    if code == "MISSING_ENCODING_EVIDENCE":
        return (
            False,
            None,
            None,
            "Do not retry unchanged. Export the smallest native WinProLadder program containing "
            "this exact instruction and operands, with CPU/profile and GUI evidence.",
            [
                "Original WinProLadder-exported .ldr",
                "Target CPU/profile and WinProLadder version",
                "One-variable operand comparison or before/after export",
            ],
        )
    if code == "ENCODING_FAILURE":
        return (
            False,
            None,
            None,
            "Treat this as an encoder defect. Preserve the IR and failure log; do not substitute "
            "an opcode or bypass validation.",
            [],
        )
    if code == "ARTIFACT_VALIDATION_FAILURE":
        return (
            False,
            None,
            None,
            "Keep the artifact unwritten. Compare source IR, lowered IR, encoded bytes, and "
            "decoded bytes before changing the codec.",
            [],
        )
    return (
        True,
        "Retry only when explicitly requesting an offline candidate; GUI and PLC status remain "
        "unverified.",
        None,
        "Run validate_ladder first, then explicitly allow an unverified candidate without "
        "labeling it GUI verified.",
        [],
    )


def diagnose_generation_failure(
    error: Exception,
    *,
    stage: str,
    ladder: Any = None,
) -> GenerationDiagnostic:
    """Convert an existing failure into stable data; never changes or retries the request."""

    if isinstance(error, GenerationFailure):
        return error.diagnostic
    reason, network_index, operand, error_type = _validation_error(error)
    match = re.search(r"\bN(\d{3})\b", reason)
    if match is not None:
        network_index = int(match.group(1))
    context_index, instruction, operands = _network_context(ladder, network_index)
    code = _code_for(reason, stage, error_type, operand)
    if network_index is None and code == "MISSING_ENCODING_EVIDENCE":
        network_index = context_index
    safe_to_retry, retry_condition, alternative, next_step, missing = _advice(code)
    verification_level, validation_levels = _verification(stage)
    return GenerationDiagnostic(
        code=code,
        stage=stage,
        network_index=network_index,
        instruction=instruction,
        operands=operands,
        reason=reason,
        safe_to_retry=safe_to_retry,
        retry_condition=retry_condition,
        verified_alternative=alternative,
        next_step=next_step,
        verification_level=verification_level,
        validation_levels=validation_levels,
        missing_evidence=missing,
        recovery={
            "attempted": ["schema_normalization", "verified_boolean_lowering"],
            "applied": [],
            "status": "no_safe_automatic_recovery",
            "policy_bypassed": False,
            "semantic_changes": False,
        },
    )


@contextmanager
def generation_stage(stage: str, ladder: Any) -> Iterator[None]:
    """Attach one pipeline stage to existing fail-closed exceptions."""

    try:
        yield
    except GenerationFailure:
        raise
    except ValueError as error:
        raise GenerationFailure(
            diagnose_generation_failure(error, stage=stage, ladder=ladder)
        ) from error


def recovery_report(layout: dict[str, Any]) -> dict[str, Any]:
    """Describe only transformations already performed by the established lowering pipeline."""

    applied = []
    simplified = set(layout.get("simplified_networks", []))
    normalized = set(layout.get("normalized_networks", []))
    if simplified:
        applied.append("boolean_simplification")
    if normalized - simplified or layout.get("helper_devices"):
        applied.append("verified_connected_layout_lowering")
    return {
        "attempted": ["schema_normalization", "verified_boolean_lowering"],
        "applied": applied,
        "status": "recovered" if applied else "not_needed",
        "semantic_equivalence": (
            "Existing Boolean truth-table/lowering tests plus emitted-byte replay"
            if applied
            else "No recovery transformation was needed"
        ),
        "policy_bypassed": False,
        "semantic_changes": False,
        "unverified_encoding_substitution": False,
    }


def diagnostic_capabilities() -> dict[str, Any]:
    """Public scope of failure classification and strictly bounded recovery."""

    return {
        "codes": list(GENERATION_CODES),
        "availability": {
            "INVALID_IR": "public request path",
            "UNSUPPORTED_INSTRUCTION": "public request path",
            "UNSUPPORTED_OPERAND": "public request path",
            "UNSUPPORTED_NETWORK_STRUCTURE": "public request and lowering paths",
            "MISSING_ENCODING_EVIDENCE": "public validation/encoding-evidence path",
            "ENCODING_FAILURE": "defensive encoder gate",
            "ARTIFACT_VALIDATION_FAILURE": "defensive emitted-byte and acceptance gates",
            "IMPORT_UNVERIFIED": (
                "strict service candidate gate; normal MCP candidates remain explicitly unverified"
            ),
        },
        "automatic_recovery": [
            "Pydantic IR normalization that does not change requested semantics",
            "existing truth-table-tested Boolean simplification and connected-layout lowering",
        ],
        "verified_encoding_alternatives": [],
        "encoding_alternative_policy": (
            "No distinct equivalent encoding is currently evidence-backed for automatic "
            "substitution"
        ),
        "never": [
            "guess opcode or binary layout",
            "drop unsupported networks",
            "remove interlocks or safety logic",
            "bypass workspace policy",
            "claim GUI or PLC verification without exact evidence",
        ],
        "defensive_only": ["ENCODING_FAILURE", "ARTIFACT_VALIDATION_FAILURE"],
    }
