"""WinProLadder MCP stdio entry point. Logs belong on stderr."""

import argparse
import base64
import functools
import hashlib
import json
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote, unquote

from mcp.server.fastmcp import FastMCP
from mcp.types import (
    BlobResourceContents,
    CallToolResult,
    EmbeddedResource,
    ResourceLink,
    TextContent,
    ToolAnnotations,
)
from pydantic import AnyUrl, StrictBool, StrictInt

from .acceptance import AcceptanceCase
from .capabilities import capability_summary, instruction_capabilities, instruction_families
from .component_comments import ComponentComment
from .control import ControlSpec, control_ladder
from .design import design_guide
from .io_contract import IOContract
from .ir import Ladder, Network, validation
from .layout import lower_ladder
from .ldr import MAX_SIZE
from .manual_reference import analyze_rtc_snapshot, manual_reference
from .pdw import PdwRung
from .pdw_project import PdwSection
from .profiles import HeaderProfile
from .runtime import MODEL_SCOPE, Scalar, simulate_runtime
from .sequence import SequenceSpec, sequence_ladder
from .service import Service, capabilities
from .system import SystemSpec, system_ladder


def build_server(
    root: Path, output_dir: Path | None = None, *, compact_responses: bool = True
) -> FastMCP:
    service = Service(root, output_dir)
    mcp = FastMCP(
        "WinProLadder",
        instructions=(
            "For common functions prefer generate_control_ldr; for sequential pause/resume "
            "use generate_sequence_ldr. Copy only user-specified X/Y into io_contract. "
            "Never invent physical I/O or external clocks. Require signal and output addresses. "
            "Ordinary T and sampled FUN87/88/89 accumulative timers are supported. "
            "Use get_design_guide only when guidance is needed; detail=true expands notes. "
            "Call get_instruction_capabilities without a family to list families, then pass one "
            "family for focused limits. "
            "Honor its workspace architecture policy; forbidden M-to-M chains must be "
            "redesigned using native instructions, not renamed or hidden in helpers. "
            "Call generate_ldr for an actual file; inferred encodings are enabled. "
            "Do not ask the user for JSON or samples for supported expressions/parameters. "
            "Include acceptance cases in generation; avoid repeating the same simulation. "
            "Set require_acceptance=true when behavior checks are mandatory. "
            "Return file links and validation warnings. "
            "Generation results include an MCP resource link to the actual binary .ldr. "
            "Use resources/read or get_ldr_artifact to deliver its bytes to clients without "
            "access to the server filesystem. "
            "When the user explicitly requests 新增元件註解 or component comments, call "
            "generate_component_comments and return its separate .txt artifact link. "
            "Stop polarity is the PLC input logic, not physical button wiring. No PLC operations."
        ),
    )
    read = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
    write = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)

    def error_result(error: Exception, output_name: str | None = None) -> CallToolResult:
        message = str(error)
        if isinstance(error, FileExistsError):
            code = "ARTIFACT_ALREADY_EXISTS"
            filename = output_name or Path(error.filename or "artifact").name
            stem, suffix = Path(filename).stem, Path(filename).suffix
            suggested_name = f"{stem}-2{suffix}" if suffix else f"{stem}-2"
            user_message = f"Will not overwrite existing artifact {filename}"
            details: dict[str, Any] = {"suggested_name": suggested_name}
        elif "Undeclared physical I/O" in message:
            code = "IO_CONTRACT_VIOLATION"
            user_message = message
            details = {}
        elif "architecture" in message.lower() or "M-to-M" in message:
            code = "ARCHITECTURE_POLICY_VIOLATION"
            user_message = message
            details = {}
        else:
            code = "VALIDATION_ERROR"
            user_message = message
            details = {}
        payload = {
            "error": {
                "code": code,
                "message": user_message,
                **details,
                "written": False,
            },
            "response_mode": "compact" if compact_responses else "full",
        }
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))],
            structuredContent=payload,
        )

    def structured_write_errors(function: Any) -> Any:
        @functools.wraps(function)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            try:
                return function(*args, **kwargs)
            except (FileExistsError, ValueError) as error:
                output_name = kwargs.get("output_name")
                if output_name is None and args:
                    output_name = args[0]
                return error_result(error, output_name)

        return wrapped

    def artifact_path(name: str, suffixes: frozenset[str] = frozenset({".ldr"})) -> Path:
        if (
            not name
            or Path(name).name != name
            or any(c in name for c in "/\\:")
            or any(c in name for c in '<>"|?*')
            or Path(name).is_reserved()
            or Path(name).suffix.lower() not in suffixes
            or name.startswith(".")
        ):
            allowed = ", ".join(sorted(suffixes))
            raise ValueError(f"Artifact name must be a plain filename ending in {allowed}")
        target = (service.output / name).resolve(strict=True)
        if target.parent != service.output:
            raise ValueError("Artifact must be directly inside the configured output directory")
        if not target.is_file() or target.stat().st_size > MAX_SIZE:
            raise ValueError("Not a file or exceeds 16 MiB limit")
        return target

    def artifact_bytes(name: str, suffixes: frozenset[str] = frozenset({".ldr"})) -> bytes:
        with artifact_path(name, suffixes).open("rb") as stream:
            data = stream.read(MAX_SIZE + 1)
        if len(data) > MAX_SIZE:
            raise ValueError("Artifact exceeds 16 MiB limit")
        return data

    def artifact_result(
        result: dict[str, Any],
        data: bytes | None = None,
        *,
        mime_type: str = "application/octet-stream",
        description: str = "Download the generated WinProLadder ladder resource file.",
    ) -> CallToolResult:
        result = {
            **result,
            "response_mode": "compact" if compact_responses else "full",
        }
        if compact_responses:
            assumptions = result.get("design", {}).get("assumptions")
            result = {
                key: value
                for key, value in result.items()
                if key not in {"design", "design_summary", "network_notes", "symbols"}
            }
            if assumptions:
                result["design_assumptions"] = assumptions
        name = Path(result["path"]).name
        uri = AnyUrl(f"winproladder://artifacts/{quote(name, safe='')}")
        metadata = {
            **result,
            "artifact": {
                "uri": str(uri),
                "name": name,
                "mime_type": mime_type,
                "size": result["size"],
                "sha256": result["sha256"],
            },
        }
        summary = {
            "artifact": metadata["artifact"],
            "response_mode": metadata["response_mode"],
            "assumed_profile": metadata.get("assumed_profile"),
            "profile_warning": metadata.get("profile_warning"),
            "warnings": metadata.get("warnings", []),
        }
        response = CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=json.dumps(
                        summary if compact_responses else metadata,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                ),
                ResourceLink(
                    type="resource_link",
                    uri=uri,
                    name=name,
                    title=name,
                    description=description,
                    mimeType=mime_type,
                    size=result["size"],
                ),
            ],
            structuredContent=metadata,
        )
        if data is not None:
            response.content.append(
                EmbeddedResource(
                    type="resource",
                    resource=BlobResourceContents(
                        uri=uri,
                        mimeType=mime_type,
                        blob=base64.b64encode(data).decode("ascii"),
                    ),
                )
            )
        return response

    @mcp.tool(annotations=read)
    def get_capabilities(detail: bool = False) -> dict[str, Any]:
        """Get server-wide support, policies and limits; not individual instruction details."""
        base = capabilities() if detail or not compact_responses else capability_summary()
        result = {
            **base,
            "response_mode": "full" if detail or not compact_responses else "compact",
            "workspace": str(service.root),
            "architecture_policy": service.architecture_policy(),
            "output_directory": str(service.output),
            "artifact_delivery": {
                "resource_template": "winproladder://artifacts/{name}",
                "tool": "get_ldr_artifact",
                "ldr_tool": "get_ldr_artifact",
                "pdw_tool": "get_pdw_artifact",
                "component_comment_tool": "generate_component_comments",
                "format": "MCP binary resources (base64 on the wire); .ldr, .pdw or CP950 .txt",
            },
        }
        if compact_responses and not detail:
            keys = {
                "version",
                "build",
                "transport",
                "pdw",
                "pdw_project",
                "generation",
                "address_subset",
                "simulation_model",
                "workspace",
                "architecture_policy",
                "output_directory",
                "artifact_delivery",
                "instruction_family_count",
                "instruction_discovery",
                "no_plc_connection",
                "writes",
                "response_mode",
            }
            return {
                **{k: v for k, v in result.items() if k in keys},
                "more": "Use detail=true for instruction-specific limits and full schema.",
            }
        return result

    @mcp.tool(annotations=read)
    def get_instruction_capabilities(family: str | None = None) -> dict[str, Any]:
        """List instruction families, or get limits and evidence for one selected family."""
        if family is None:
            families = instruction_families()
            return {"families": families, "count": len(families)}
        return instruction_capabilities(family)

    @mcp.tool(annotations=read)
    def get_manual_reference() -> dict[str, Any]:
        """Get manual operand maxima, edition differences and RTC register/control procedures."""
        return manual_reference()

    @mcp.tool(annotations=read)
    def inspect_rtc_snapshot(registers: dict[str, StrictInt]) -> dict[str, Any]:
        """Validate supplied R4128..R4134 values and optional packed R4135; no PLC access."""
        return analyze_rtc_snapshot(registers)

    @mcp.tool(annotations=read)
    def get_design_guide(detail: bool = False) -> dict[str, Any]:
        """Get design guidance. Use detail=true for instruction notes and full examples."""
        if compact_responses and not detail:
            return {
                "response_mode": "compact",
                "control_recipes": design_guide()["control_recipes"],
                "architecture_policy": service.architecture_policy(),
                "workflow": [
                    "Use control recipes for common functions, sequence for steps, system for "
                    "independent controls, generate_ldr for custom logic.",
                    "Use only requested X/Y and timing; do not invent inputs or clocks.",
                    "Supply acceptance cases with generation; "
                    "source and emitted bytes are checked.",
                    "Return the artifact link and warnings; GUI/PLC checks are separate.",
                ],
                "more": "Use detail=true for instruction-specific notes, examples and schema.",
            }
        return {
            "response_mode": "full",
            **design_guide(),
            "architecture_policy": service.architecture_policy(),
            "ladder_schema": Ladder.model_json_schema(),
        }

    @mcp.tool(annotations=write)
    @structured_write_errors
    def generate_system_ldr(
        output_name: str,
        spec: SystemSpec,
        io_contract: IOContract,
        acceptance: list[AcceptanceCase] | None = None,
        require_acceptance: bool = False,
        strict_writers: bool = True,
        target_profile: HeaderProfile | None = None,
    ) -> CallToolResult:
        """Generate independent controls with automatic internal M/T/C allocation.
        Explicit overlapping resources are rejected, not silently reassigned. Inputs can be shared.
        """
        ladder, design = system_ladder(spec)
        if target_profile is not None:
            ladder = ladder.model_copy(update={"profile": target_profile})
        return artifact_result(
            service.generate_design(
                output_name,
                ladder,
                design,
                acceptance,
                io_contract=io_contract,
                require_acceptance=require_acceptance,
                strict_writers=strict_writers,
            )
        )

    @mcp.tool(annotations=write)
    @structured_write_errors
    def generate_control_ldr(
        output_name: str,
        spec: ControlSpec,
        io_contract: IOContract,
        acceptance: list[AcceptanceCase] | None = None,
        require_acceptance: bool = False,
        strict_writers: bool = True,
        target_profile: HeaderProfile | None = None,
    ) -> CallToolResult:
        """Generate common control functions from customer requirements translated by the host.
        Physical I/O must be explicit and within io_contract. Supports latch, toggle, edges, delays,
        pulse, counter, interlocked direction and star/delta; returns actual .ldr + assumptions.
        """
        ladder, design = control_ladder(spec)
        if target_profile is not None:
            ladder = ladder.model_copy(update={"profile": target_profile})
        return artifact_result(
            service.generate_design(
                output_name,
                ladder,
                design,
                acceptance,
                io_contract=io_contract,
                require_acceptance=require_acceptance,
                strict_writers=strict_writers,
            )
        )

    @mcp.tool(annotations=write)
    @structured_write_errors
    def generate_sequence_ldr(
        output_name: str,
        spec: SequenceSpec,
        io_contract: IOContract,
        acceptance: list[AcceptanceCase] | None = None,
        require_acceptance: bool = False,
        strict_writers: bool = True,
        target_profile: HeaderProfile | None = None,
    ) -> CallToolResult:
        """Generate ordered steps using native T timers, with no automatic X/Y additions.
          Native pause/resume uses FUN87 with register state and no relay copy chains.
        External pulse counting is only for requirements explicitly specifying a clock input.
        Return symbols and actual .ldr; not GUI or PLC verified.
        """
        ladder, design = sequence_ladder(spec)
        if target_profile is not None:
            ladder = ladder.model_copy(update={"profile": target_profile})
        return artifact_result(
            service.generate_design(
                output_name,
                ladder,
                design,
                acceptance,
                io_contract=io_contract,
                require_acceptance=require_acceptance,
                strict_writers=strict_writers,
            )
        )

    @mcp.tool(annotations=write)
    @structured_write_errors
    def generate_ldr(
        output_name: str,
        ladder: Ladder,
        io_contract: IOContract,
        acceptance: list[AcceptanceCase] | None = None,
        require_acceptance: bool = False,
        strict_writers: bool = False,
    ) -> CallToolResult:
        """Compile caller-supplied custom Ladder IR to an actual .ldr file.

        Use generate_control_ldr for common controls and generate_sequence_ldr for ordered steps.
        Returns SHA-256, a binary resource link and verification warnings. Never overwrites files.
        """
        return artifact_result(
            service.generate(
                output_name,
                ladder,
                acceptance,
                io_contract=io_contract,
                require_acceptance=require_acceptance,
                strict_writers=strict_writers,
            )
        )

    @mcp.tool(annotations=read)
    def inspect_pdw(path: str) -> dict[str, Any]:
        """Inspect PDW sections, Chinese comments and known checksums; FUNC199 stays opaque."""
        return service.inspect_pdw(path)

    @mcp.tool(annotations=write)
    @structured_write_errors
    def generate_project_pdw(
        output_name: str,
        template_path: str,
        ladder: Ladder,
        io_contract: IOContract,
        acceptance: list[AcceptanceCase] | None = None,
        sections: list[PdwSection] | None = None,
        comments: list[ComponentComment] | None = None,
        require_acceptance: bool = False,
        module_order: list[str] | None = None,
        module_template_paths: list[str] | None = None,
    ) -> CallToolResult:
        """Compile Ladder IR to sampled FBs-20MC/32MC/40MC/60MC PDW layouts.

        Module records come from local templates.

        Match ladder.profile to the template CPU. Template must be inside workspace. Program and
        annotations are replaced by the explicit request; opaque project settings are retained.
        Network.comment supports CR/LF. Section indexes refer to zero-based source networks.
        Optional embedded SECT text uses only the sampled even-byte encoding. FUNC199 and
        control flow are not generated. New files only, no PLC connection or GUI guarantee.
        module_order=null preserves all modules; [] removes them explicitly. Names copy exact
        records from the template and optional workspace-scoped module_template_paths. Order and
        duplicates are retained. Missing or conflicting records are rejected. No automatic I/O
        allocation, module parameter editing, slot-capacity or hardware compatibility validation.
        """
        result = service.generate_project_pdw(
            output_name,
            template_path,
            ladder,
            io_contract,
            acceptance,
            sections=sections,
            comments=comments,
            require_acceptance=require_acceptance,
            module_order=module_order,
            module_template_paths=module_template_paths,
        )
        return artifact_result(
            result,
            artifact_bytes(output_name, frozenset({".pdw"})),
            description="Download the compiled WinProLadder PDW project.",
        )

    @mcp.tool(annotations=write)
    @structured_write_errors
    def generate_pdw(
        output_name: str,
        template_path: str,
        rungs: list[PdwRung],
        io_contract: IOContract,
        acceptance: list[AcceptanceCase] | None = None,
    ) -> CallToolResult:
        """Experimental PDW: replace one/two X -> Y rungs in a local FBs-60MC template.

        Same rung count required. Only X0/X1, Y0/Y1/Y2 and NO/NC contacts supported.
        No branches, functions, comments or PLC operations. Templates are workspace-scoped.
        Keep private templates outside Git; configure --root to their private directory.
        Return the actual binary artifact and warnings. Never overwrite.
        """
        result = service.generate_pdw(output_name, template_path, rungs, io_contract, acceptance)
        return artifact_result(
            result,
            artifact_bytes(output_name, frozenset({".pdw"})),
            description="Download the generated WinProLadder PDW project.",
        )

    @mcp.tool(annotations=read)
    def get_pdw_artifact(output_name: str) -> CallToolResult:
        """Retrieve a generated PDW artifact's exact bytes from the configured output directory."""
        target = artifact_path(output_name, frozenset({".pdw"}))
        data = artifact_bytes(output_name, frozenset({".pdw"}))
        return artifact_result(
            {"path": str(target), "size": len(data), "sha256": hashlib.sha256(data).hexdigest()},
            data,
            description="Download the generated WinProLadder PDW project.",
        )

    @mcp.tool(annotations=write)
    @structured_write_errors
    def generate_component_comments(
        output_name: str, entries: list[ComponentComment]
    ) -> CallToolResult:
        """Generate a separate WinProLadder component-comment import .txt.

        Call this when the user explicitly requests 新增元件註解 or component comments.
        Each row has ref, comment and description. Output exactly follows the supplied sample:
        REF/COMMENT/DESCRIPTION columns, tabs, CRLF and CP950/Big5. Never overwrites a file.
        """
        result = service.write_component_comments(output_name, entries)
        data = artifact_bytes(output_name, frozenset({".txt"}))
        return artifact_result(
            result,
            data,
            mime_type="text/tab-separated-values; charset=big5",
            description="Download the generated WinProLadder component-comment text file.",
        )

    @mcp.tool(annotations=read)
    def get_ldr_artifact(output_name: str) -> CallToolResult:
        """Retrieve a generated .ldr as an embedded MCP binary resource and download link.

        Use the original output_name, including .ldr. Returns exact file bytes as base64
        with SHA-256; only reads the configured output directory. Useful when the client
        cannot access local server paths or cannot invoke resources/read directly.
        """
        target = artifact_path(output_name)
        data = artifact_bytes(output_name)
        return artifact_result(
            {"path": str(target), "size": len(data), "sha256": hashlib.sha256(data).hexdigest()},
            data,
        )

    @mcp.tool(annotations=read)
    def inspect_ldr(path: str) -> dict[str, Any]:
        """Inspect binary framing, raw bytes, offsets and CRC only; does not explain logic."""
        return service.inspect(path)

    @mcp.tool(annotations=read)
    def read_ldr(path: str) -> dict[str, Any]:
        """Decode Ladder networks in display order; unknown payloads stay opaque. Reject bad CRC."""
        return service.read(path)

    @mcp.tool(annotations=read)
    def analyze_ldr(path: str) -> dict[str, Any]:
        """Analyze decoded network meaning and device reads/writes; not a raw-byte inspection."""
        return service.analyze(path)

    @mcp.tool(annotations=read)
    def compare_ldr(left_path: str, right_path: str) -> dict[str, Any]:
        """Align display-order networks and report insert/delete/replace, including CRC changes."""
        return service.compare(left_path, right_path)

    @mcp.tool(annotations=read)
    def validate_ladder(ladder: Ladder) -> dict[str, Any]:
        """Preview simplified connected IR and resource costs; not PLC syntax validation."""
        lowered, layout = lower_ladder(ladder)
        source_architecture = service.architecture(ladder, enforce=False)
        architecture = service.architecture(lowered, enforce=False)
        result: dict[str, Any] = dict(validation(lowered))
        if not source_architecture["valid"] or not architecture["valid"]:
            result["valid"] = False
            result["errors"].append("Workspace architecture forbids M-to-M networks")
        try:
            service.check_layout(layout)
        except ValueError as error:
            result["valid"] = False
            result["errors"].append(str(error))
        return {
            **result,
            "architecture": architecture,
            "source_architecture": source_architecture,
            "layout": layout,
            "optimized_ladder": lowered.model_dump(),
        }

    @mcp.tool(annotations=read)
    def simulate_ladder(
        ladder: Ladder,
        inputs: list[dict[str, StrictBool]],
        initial: dict[str, Scalar] | None = None,
        scan_ms: StrictInt | None = None,
    ) -> dict[str, Any]:
        """Bounded Boolean/direct R/D model, not PLC emulation.

        scan_ms is required for T/C and FUN87/88/89. Supports the explicitly listed
        numeric/native subset; unsupported actions fail without a partial trace.
        Words use unsigned 16-bit storage. Missing X inputs reset false each scan.
        See get_capabilities simulation_model for assumptions and supported actions.
        """
        return {
            "trace": simulate_runtime(ladder, inputs, initial or {}, scan_ms),
            "scope": MODEL_SCOPE,
        }

    @mcp.tool(annotations=write)
    @structured_write_errors
    def export_ldr(path: str, output_name: str) -> CallToolResult:
        """Re-encode to a NEW file, preserving opaque bytes and any original invalid CRC."""
        return artifact_result(service.export(path, output_name))

    @mcp.tool(annotations=write)
    @structured_write_errors
    def modify_network(
        path: str,
        output_name: str,
        operation: Literal["replace", "insert", "delete"],
        index: int,
        network: Network | None = None,
        allow_unverified: bool = False,
    ) -> CallToolResult:
        """Edit in a NEW file; index 0 is N000. Preserve untouched raw records."""
        return artifact_result(
            service.edit(path, output_name, operation, index, network, allow_unverified)
        )

    @mcp.resource(
        "winproladder://artifacts/{name}",
        name="generated_artifact",
        title="Generated WinProLadder artifact",
        mime_type="application/octet-stream",
    )
    def artifact_resource(name: str) -> bytes:
        """Read a generated .ldr, .pdw or component-comment .txt artifact."""
        return artifact_bytes(unquote(name, errors="strict"), frozenset({".ldr", ".txt", ".pdw"}))

    @mcp.resource("winproladder://capabilities")
    def capability_resource() -> str:
        return json.dumps(get_capabilities(detail=True), ensure_ascii=False)

    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    response_group = parser.add_mutually_exclusive_group()
    response_group.add_argument(
        "--compact-responses",
        dest="compact_responses",
        action="store_true",
        help="Use compact responses (default)",
    )
    response_group.add_argument(
        "--full-responses",
        dest="compact_responses",
        action="store_false",
        help="Include repeated design metadata and full schemas",
    )
    parser.set_defaults(compact_responses=True)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Workspace allowed for reads")
    parser.add_argument(
        "--output-dir", type=Path, help="Absolute output subdirectory (default ROOT/artifacts)"
    )
    args = parser.parse_args()
    build_server(args.root, args.output_dir, compact_responses=args.compact_responses).run(
        transport="stdio"
    )


if __name__ == "__main__":
    main()
