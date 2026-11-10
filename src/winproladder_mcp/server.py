"""WinProLadder MCP stdio entry point. Logs belong on stderr."""

import argparse
import base64
import functools
import hashlib
import json
from pathlib import Path
from typing import Annotated, Any, Literal
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
from pydantic import AnyUrl, BaseModel, ConfigDict, Field, StrictBool, StrictInt

from .acceptance import AcceptanceCase
from .capabilities import capability_summary, instruction_capabilities, instruction_families
from .component_comments import ComponentComment
from .control import ControlSpec, control_ladder
from .design import design_guide
from .io_contract import IOContract
from .ir import Ladder, Network, validation
from .layout import lower_ladder
from .ldr import MAX_SIZE
from .manual_reference import RTCSnapshot, analyze_rtc_snapshot, manual_reference
from .pdw import PdwRung
from .pdw_project import PdwSection
from .profiles import HeaderProfile
from .runtime import MODEL_SCOPE, Scalar, simulate_runtime
from .sequence import SequenceSpec, sequence_ladder
from .service import Service, capabilities
from .system import SystemSpec, system_ladder


class ArtifactDescriptor(BaseModel):
    """Download metadata shared by generated and retrieved artifacts."""

    uri: str = Field(description="MCP resource URI for the artifact bytes.")
    name: str = Field(description="Plain artifact filename.")
    mime_type: str = Field(description="Media type of the returned bytes.")
    size: int = Field(ge=0, description="Artifact size in bytes.")
    sha256: str = Field(description="Lowercase SHA-256 digest of the exact artifact bytes.")


class ArtifactToolOutput(BaseModel):
    """Structured result for artifact-writing and artifact-retrieval tools."""

    model_config = ConfigDict(extra="allow")

    response_mode: Literal["compact", "full"] = Field(
        description="Whether repeated design metadata was compacted or returned in full."
    )
    artifact: ArtifactDescriptor | None = Field(
        default=None,
        description="Artifact metadata on success; absent when validation fails before writing.",
    )
    error: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Structured error code, message and written=false on handled validation failure."
        ),
    )
    warnings: list[Any] = Field(
        default_factory=list,
        description="Generation or verification warnings; empty when none were reported.",
    )


def build_server(
    root: Path, output_dir: Path | None = None, *, compact_responses: bool = True
) -> FastMCP:
    service = Service(root, output_dir)
    mcp = FastMCP(
        "WinProLadder",
        instructions=(
            "Prefer generate_control_ldr for one control and generate_sequence_ldr for ordered "
            "steps; use custom Ladder IR only when needed. Declare exactly the user-specified X/Y "
            "and never invent physical I/O or external clocks. Honor the workspace architecture "
            "policy: redesign forbidden M-to-M chains with native instructions, never hidden relay "
            "helpers. Use get_design_guide(detail=true) for the full IR schema and "
            "get_instruction_capabilities for focused limits. Return artifact links and every "
            "validation warning. Generated files are offline artifacts only: no GUI import, PLC "
            "connection or runtime verification is implied. MCP never renames or deletes "
            "artifacts; those are filesystem operations."
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
        warnings = result.get("warnings")
        if warnings is None:
            validation_result = result.get("validation")
            if isinstance(validation_result, dict):
                warnings = validation_result.get("warnings")
        result["warnings"] = list(warnings or [])
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
            "warnings": metadata["warnings"],
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
    def get_capabilities(
        detail: Annotated[
            bool,
            Field(
                description=(
                    "False returns the compact server summary; true includes full instruction, "
                    "generation and simulation capability details."
                )
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Return server-wide support, policies and limits as metadata only.

        Includes build/version, generation and simulation scope, architecture policy, workspace,
        output directory and artifact delivery. detail=true expands instruction-specific limits.
        This never reads or modifies program content; use modify_network to edit one network.
        PLC access and artifact rename/delete are intentionally outside this offline server.
        """
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
    def get_instruction_capabilities(
        family: Annotated[
            str | None,
            Field(
                description=(
                    "Exact instruction-family identifier returned by this tool's family list; "
                    "omit to list valid families instead of requesting one family's limits."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Return implemented limits and evidence for one instruction family.

        Omit family to discover valid identifiers; provide one returned identifier for its operand,
        encoding and runtime-model boundaries. Use this for implemented MCP coverage, not general
        PLC legality: get_manual_reference provides manual maxima and edition differences, while
        get_capabilities provides server-wide support. Unknown family identifiers return an error.
        """
        if family is None:
            families = instruction_families()
            return {"families": families, "count": len(families)}
        return instruction_capabilities(family)

    @mcp.tool(annotations=read)
    def get_manual_reference() -> dict[str, Any]:
        """Return bundled PLC-manual semantics, operand maxima and cited source pages.

        Use this to decide documented PLC legality, manual-edition differences or RTC register and
        control procedures. Use get_instruction_capabilities instead for implemented encoder and
        simulation coverage, or get_design_guide for generation workflow. This reads no project or
        PLC state and returns static reference data only.
        """
        return manual_reference()

    @mcp.tool(annotations=read)
    def inspect_rtc_snapshot(
        registers: Annotated[
            RTCSnapshot,
            Field(
                description=(
                    "Caller-supplied RTC snapshot keyed by R4128 through R4134, with optional "
                    "packed R4135; values are integers, not PLC addresses to read."
                )
            ),
        ],
    ) -> dict[str, Any]:
        """Validate a caller-supplied FATEK RTC register snapshot offline.

        Use this after obtaining R4128..R4134 externally; optionally include packed R4135 to check
        hour/minute consistency. It checks field ranges and month/day, then returns decoded fields,
        expected_R4135 and consistency when supplied. Invalid or unknown fields return an error and
        nothing is written. This server has no PLC-access tool; use get_manual_reference for RTC
        register meanings and setting procedure.
        """
        return analyze_rtc_snapshot(registers.model_dump(exclude_none=True))

    @mcp.tool(annotations=read)
    def get_design_guide(
        detail: Annotated[
            bool,
            Field(
                description=(
                    "False returns compact control recipes, architecture policy and workflow; "
                    "true adds instruction notes, complete examples and the Ladder IR schema."
                )
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Return offline workflow guidance for designing supported WinProLadder programs.

        Use this before generation to choose a control, sequence, system or custom-Ladder tool and
        to obtain acceptance-test patterns. With detail=false it returns compact control recipes,
        architecture policy and workflow; detail=true adds instruction notes, complete examples
        and the Ladder IR schema. This is not runtime capability metadata (get_capabilities),
        instruction operand evidence (get_instruction_capabilities), or manual/RTC reference data
        (get_manual_reference), and it does not validate IR or create a file.
        """
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
        output_name: Annotated[
            str,
            Field(
                description="New plain .ldr filename in the artifact directory; never overwrites."
            ),
        ],
        spec: Annotated[
            SystemSpec,
            Field(description="System requirement plus one or more independent control recipes."),
        ],
        io_contract: Annotated[
            IOContract,
            Field(description="Complete user-authorized physical X inputs and Y outputs."),
        ],
        acceptance: Annotated[
            list[AcceptanceCase] | None,
            Field(description="Optional executable scan cases checked before and after encoding."),
        ] = None,
        require_acceptance: Annotated[
            bool,
            Field(description="When true, reject generation unless acceptance cases are supplied."),
        ] = False,
        strict_writers: Annotated[
            bool,
            Field(description="When true, reject conflicting or unsafe multiple device writers."),
        ] = True,
        target_profile: Annotated[
            HeaderProfile | None,
            Field(
                description="Optional sampled CPU/header profile; omit to use the default profile."
            ),
        ] = None,
    ) -> Annotated[CallToolResult, ArtifactToolOutput]:
        """Generate a new .ldr for two or more independent ControlSpec recipes in one SystemSpec.

        Never use this for one recipe, dependent ordered steps or caller-authored IR: use
        generate_control_ldr, generate_sequence_ldr or generate_ldr respectively. This tool
        allocates internal M/T/C, permits shared inputs, rejects explicit overlaps, checks
        acceptance and writes only a new artifact. Validation failure writes nothing. It does not
        execute existing IR or return a trace; use simulate_ladder for that.
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
        output_name: Annotated[
            str,
            Field(
                description="New plain .ldr filename in the artifact directory; never overwrites."
            ),
        ],
        spec: Annotated[
            ControlSpec,
            Field(description="One supported control recipe with its requirement and addresses."),
        ],
        io_contract: Annotated[
            IOContract,
            Field(description="Complete user-authorized physical X inputs and Y outputs."),
        ],
        acceptance: Annotated[
            list[AcceptanceCase] | None,
            Field(description="Optional executable scan cases checked before and after encoding."),
        ] = None,
        require_acceptance: Annotated[
            bool,
            Field(description="When true, reject generation unless acceptance cases are supplied."),
        ] = False,
        strict_writers: Annotated[
            bool,
            Field(description="When true, reject conflicting or unsafe multiple device writers."),
        ] = True,
        target_profile: Annotated[
            HeaderProfile | None,
            Field(
                description="Optional sampled CPU/header profile; omit to use the default profile."
            ),
        ] = None,
    ) -> Annotated[CallToolResult, ArtifactToolOutput]:
        """Generate a new .ldr for exactly one supported control recipe in a ControlSpec.

        Never use this for multiple independent controls, ordered steps or caller-authored IR: use
        generate_system_ldr, generate_sequence_ldr or generate_ldr respectively. Supports latch,
        toggle, edges, delays, pulse, counter, direction interlock and star/delta. Physical I/O must
        be explicit; validation failure writes nothing. generate_component_comments creates only a
        separate comment-import .txt.
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
        output_name: Annotated[
            str,
            Field(
                description="New plain .ldr filename in the artifact directory; never overwrites."
            ),
        ],
        spec: Annotated[
            SequenceSpec,
            Field(
                description="Ordered step requirement, start signal, timing and output definitions."
            ),
        ],
        io_contract: Annotated[
            IOContract,
            Field(description="Complete user-authorized physical X inputs and Y outputs."),
        ],
        acceptance: Annotated[
            list[AcceptanceCase] | None,
            Field(description="Optional executable scan cases checked before and after encoding."),
        ] = None,
        require_acceptance: Annotated[
            bool,
            Field(description="When true, reject generation unless acceptance cases are supplied."),
        ] = False,
        strict_writers: Annotated[
            bool,
            Field(description="When true, reject conflicting or unsafe multiple device writers."),
        ] = True,
        target_profile: Annotated[
            HeaderProfile | None,
            Field(
                description="Optional sampled CPU/header profile; omit to use the default profile."
            ),
        ] = None,
    ) -> Annotated[CallToolResult, ArtifactToolOutput]:
        """Generate a new .ldr for dependent ordered steps defined by a SequenceSpec.

        Never use this for one control, independent controls or caller-authored IR: use
        generate_control_ldr, generate_system_ldr or generate_ldr respectively. validate_ladder
        checks existing IR and cannot derive steps. Uses native T timers or FUN87 register state for
        pause/resume, never adds X/Y, and requires an explicit clock for pulse counting. Validation
        failure writes nothing; no GUI or PLC verification is implied.
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
        output_name: Annotated[
            str,
            Field(
                description="New plain .ldr filename in the artifact directory; never overwrites."
            ),
        ],
        ladder: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Complete caller-authored Ladder IR object to validate and compile; obtain its "
                    "full schema from get_design_guide(detail=true)."
                )
            ),
        ],
        io_contract: Annotated[
            IOContract,
            Field(description="Complete user-authorized physical X inputs and Y outputs."),
        ],
        acceptance: Annotated[
            list[AcceptanceCase] | None,
            Field(description="Optional executable scan cases checked before and after encoding."),
        ] = None,
        require_acceptance: Annotated[
            bool,
            Field(description="When true, reject generation unless acceptance cases are supplied."),
        ] = False,
        strict_writers: Annotated[
            bool,
            Field(description="When true, reject conflicting or unsafe multiple device writers."),
        ] = False,
    ) -> Annotated[CallToolResult, ArtifactToolOutput]:
        """Compile complete Ladder IR the caller already provides into a new binary .ldr file.

        Never translate a ControlSpec, SequenceSpec or SystemSpec to call this tool; use
        generate_control_ldr, generate_sequence_ldr or generate_system_ldr. It does not design
        recipes, resolve defaults or allocate recipe resources. generate_component_comments creates
        only a separate comment .txt. Returns SHA-256, a resource link and warnings; validation
        failure writes nothing and existing files are never overwritten.
        """
        ladder_model = Ladder.model_validate(ladder)
        return artifact_result(
            service.generate(
                output_name,
                ladder_model,
                acceptance,
                io_contract=io_contract,
                require_acceptance=require_acceptance,
                strict_writers=strict_writers,
            )
        )

    @mcp.tool(annotations=read)
    def inspect_pdw(
        path: Annotated[
            str,
            Field(
                description="Existing .pdw path that must resolve inside the configured workspace."
            ),
        ],
    ) -> dict[str, Any]:
        """Inspect the structure and metadata of one existing workspace PDW project.

        Use this for CPU/profile data, modules, sections, Chinese comments, network offsets and
        known checksums. It does not return the downloadable binary; use get_pdw_artifact for exact
        generated bytes. FUNC199 and unsupported layouts remain opaque, invalid files return an
        error, and nothing is written or sent to a PLC.
        """
        return service.inspect_pdw(path)

    @mcp.tool(annotations=write)
    @structured_write_errors
    def generate_project_pdw(
        output_name: Annotated[
            str,
            Field(
                description="New plain .pdw filename in the artifact directory; never overwrites."
            ),
        ],
        template_path: Annotated[
            str,
            Field(
                description="Existing sampled .pdw template path inside the configured workspace."
            ),
        ],
        ladder: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Complete Ladder IR object whose profile must match the template CPU; obtain "
                    "its full schema from get_design_guide(detail=true)."
                )
            ),
        ],
        io_contract: Annotated[
            IOContract,
            Field(description="Complete user-authorized physical X inputs and Y outputs."),
        ],
        acceptance: Annotated[
            list[AcceptanceCase] | None,
            Field(description="Optional executable scan cases checked before and after encoding."),
        ] = None,
        sections: Annotated[
            list[PdwSection] | None,
            Field(
                description="Optional named sections keyed by zero-based source network indexes."
            ),
        ] = None,
        comments: Annotated[
            list[ComponentComment] | None,
            Field(description="Optional component comments to embed in the PDW project."),
        ] = None,
        require_acceptance: Annotated[
            bool,
            Field(description="When true, reject generation unless acceptance cases are supplied."),
        ] = False,
        module_order: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Optional exact module-name order; null preserves template modules and an "
                    "empty list removes them."
                )
            ),
        ] = None,
        module_template_paths: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Optional workspace PDW templates supplying module records; requires an "
                    "explicit module_order."
                )
            ),
        ] = None,
    ) -> Annotated[CallToolResult, ArtifactToolOutput]:
        """Create or revise a PDW non-destructively by compiling Ladder IR into a new project.

        Supply an existing local PDW as template_path and a different output_name; opaque project
        settings are retained while requested program and annotations are replaced. This writes a
        variable-length PDW binary with optional embedded sections and comments;
        generate_component_comments writes only a separate comment-import .txt and cannot create a
        PDW project. Sampled FBs-20MC/32MC/40MC/60MC layouts are supported.

        Module records come from local templates.

        Match ladder.profile to the template CPU. Template must be inside workspace.
        Network.comment supports CR/LF. Section indexes refer to zero-based source networks.
        Optional embedded SECT text uses only the sampled even-byte encoding. FUNC199 and
        control flow are not generated. New files only, no PLC connection or GUI guarantee.
        module_order=null preserves all modules; [] removes them explicitly. Names copy exact
        records from the template and optional workspace-scoped module_template_paths. Order and
        duplicates are retained. Missing or conflicting records are rejected. No automatic I/O
        allocation, module parameter editing, slot-capacity or hardware compatibility validation.
        """
        ladder_model = Ladder.model_validate(ladder)
        result = service.generate_project_pdw(
            output_name,
            template_path,
            ladder_model,
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
        output_name: Annotated[
            str,
            Field(
                description="New plain .pdw filename in the artifact directory; never overwrites."
            ),
        ],
        template_path: Annotated[
            str,
            Field(description="Existing FBs-60MC .pdw template path inside the workspace."),
        ],
        rungs: Annotated[
            list[PdwRung],
            Field(description="One or two replacement X-to-Y rungs matching the template count."),
        ],
        io_contract: Annotated[
            IOContract,
            Field(description="Complete user-authorized physical X inputs and Y outputs."),
        ],
        acceptance: Annotated[
            list[AcceptanceCase] | None,
            Field(description="Optional executable scan cases checked against the replacement."),
        ] = None,
    ) -> Annotated[CallToolResult, ArtifactToolOutput]:
        """Create a new fixed-size PDW binary by replacing one or two X-to-Y template rungs.

        Same rung count required. Only X0/X1, Y0/Y1/Y2 and NO/NC contacts supported.
        No branches, functions, comments or PLC operations. Templates are workspace-scoped.
        This generates a PDW binary; generate_component_comments produces only a separate .txt.
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
    def get_pdw_artifact(
        output_name: Annotated[
            str,
            Field(
                description=(
                    "Exact plain .pdw filename previously created in the artifact directory."
                )
            ),
        ],
    ) -> Annotated[CallToolResult, ArtifactToolOutput]:
        """Return the exact bytes and download link for one previously generated PDW artifact.

        Use this after PDW generation when the client needs an embedded binary resource; use
        inspect_pdw to interpret project structure, or get_ldr_artifact for an .ldr. output_name
        must be the exact plain .pdw filename in the artifact directory. Missing, oversized or
        wrong-extension files return an error. This reads only and returns URI, size and SHA-256.
        """
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
        output_name: Annotated[
            str,
            Field(
                description="New plain .txt filename in the artifact directory; never overwrites."
            ),
        ],
        entries: Annotated[
            list[ComponentComment],
            Field(
                description="Rows with ref, description, and COMMENT (max 16 CP950/Big5 bytes)."
            ),
        ],
    ) -> Annotated[CallToolResult, ArtifactToolOutput]:
        """Create only a separate CP950 WinProLadder component-comment import .txt file.

        Call this only when the user explicitly requests 新增元件註解 or component comments. It
        does not inspect, analyze, generate or modify ladder logic or PDW projects; use analyze_ldr
        to explain the logic and device references in an existing .ldr.
        Rows use REF/COMMENT/DESCRIPTION, tabs, CRLF and CP950/Big5; COMMENT is at most 16
        encoded bytes. Never overwrites a file.
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
    def get_ldr_artifact(
        output_name: Annotated[
            str,
            Field(
                description=(
                    "Exact plain .ldr filename previously created in the artifact directory."
                )
            ),
        ],
    ) -> Annotated[CallToolResult, ArtifactToolOutput]:
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
    def inspect_ldr(
        path: Annotated[
            str,
            Field(
                description="Existing .ldr path that must resolve inside the configured workspace."
            ),
        ],
    ) -> dict[str, Any]:
        """Inspect the binary container of one existing .ldr file without decoding its logic.

        Use this for framing, record offsets, raw payload bytes and stored/calculated CRC evidence.
        It reads one workspace-scoped file and returns metadata only; it never writes or connects to
        a PLC. Use read_ldr for decoded networks or analyze_ldr for device reads, writes and
        meaning.
        Invalid framing or file constraints return an error rather than partial interpretation.
        """
        return service.inspect(path)

    @mcp.tool(annotations=read)
    def read_ldr(
        path: Annotated[
            str,
            Field(
                description="Existing .ldr path that must resolve inside the configured workspace."
            ),
        ],
    ) -> dict[str, Any]:
        """Decode one existing .ldr into display-order network records and optional Ladder IR.

        Use this for decoded logic and raw payloads; use inspect_ldr for container offsets or
        bad-CRC forensics, and analyze_ldr for device reads/writes and semantic summaries.
        Unsupported payloads remain opaque, complete Ladder IR is returned only when every network
        decodes, and
        bad CRC or unknown framing returns an error. The workspace file is never modified.
        """
        return service.read(path)

    @mcp.tool(annotations=read)
    def analyze_ldr(
        path: Annotated[
            str,
            Field(
                description="Existing .ldr path that must resolve inside the configured workspace."
            ),
        ],
    ) -> dict[str, Any]:
        """Explain the behavior and device usage of one existing valid .ldr file.

        Use this for per-network meaning, decoded counts, device read/write references, timer
        settings and completeness warnings. Use read_ldr when full decoded logic or raw payloads
        are needed, or inspect_ldr for framing and CRC evidence. Bad CRC or unknown framing returns
        an error; opaque networks produce an explicit incomplete-analysis warning. Nothing is
        written or sent to a PLC.
        """
        return service.analyze(path)

    @mcp.tool(annotations=read)
    def compare_ldr(
        left_path: Annotated[
            str,
            Field(description="Existing baseline .ldr path inside the configured workspace."),
        ],
        right_path: Annotated[
            str,
            Field(description="Existing comparison .ldr path inside the configured workspace."),
        ],
    ) -> dict[str, Any]:
        """Compare two existing .ldr files and report their structural and CRC differences.

        This only aligns decoded display-order networks as insert/delete/replace. It does not
        validate IR, simulate behavior or write a file: use validate_ladder, simulate_ladder or
        generate_ldr for those actions. Use read_ldr for either file's decoded network contents.
        """
        return service.compare(left_path, right_path)

    @mcp.tool(annotations=read)
    def validate_ladder(
        ladder: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Caller-supplied Ladder IR object to check without creating a file; obtain its "
                    "full schema from get_design_guide(detail=true)."
                )
            ),
        ],
    ) -> dict[str, Any]:
        """Validate one caller-supplied Ladder IR object without reading or writing .ldr files.

        Returns simplified connected IR, layout and resource/policy errors; it is not PLC syntax
        validation. To report differences between two existing .ldr files, use compare_ldr instead.
        """
        ladder_model = Ladder.model_validate(ladder)
        lowered, layout = lower_ladder(ladder_model)
        source_architecture = service.architecture(ladder_model, enforce=False)
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
        ladder: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Caller-supplied Ladder IR object for the bounded model; obtain its full "
                    "schema from get_design_guide(detail=true)."
                )
            ),
        ],
        inputs: Annotated[
            list[dict[str, StrictBool]],
            Field(
                description=(
                    "Ordered scan inputs; each object maps X device names to Boolean values."
                )
            ),
        ],
        initial: Annotated[
            dict[str, Scalar] | None,
            Field(
                description="Optional initial Boolean or integer values keyed by modeled device."
            ),
        ] = None,
        scan_ms: Annotated[
            StrictInt | None,
            Field(
                ge=1,
                description=(
                    "Milliseconds per scan; required when the Ladder uses timers, counters or "
                    "FUN87/88/89."
                ),
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Simulate caller-supplied Ladder IR and return a bounded per-scan behavior trace.

        This neither generates a system .ldr nor compares existing files; use generate_system_ldr
        for multi-control generation and compare_ldr for file differences. This is a
        Boolean/direct R/D model, not PLC emulation. scan_ms is required for T/C and FUN87/88/89.
        Supports the explicitly listed
        numeric/native subset; unsupported actions fail without a partial trace.
        Words use unsigned 16-bit storage. Missing X inputs reset false each scan.
        See get_capabilities simulation_model for assumptions and supported actions.
        """
        ladder_model = Ladder.model_validate(ladder)
        return {
            "trace": simulate_runtime(ladder_model, inputs, initial or {}, scan_ms),
            "scope": MODEL_SCOPE,
        }

    @mcp.tool(annotations=write)
    @structured_write_errors
    def export_ldr(
        path: Annotated[
            str,
            Field(description="Existing .ldr source path inside the configured workspace."),
        ],
        output_name: Annotated[
            str,
            Field(
                description="New plain .ldr filename in the artifact directory; never overwrites."
            ),
        ],
    ) -> Annotated[CallToolResult, ArtifactToolOutput]:
        """Re-encode one existing .ldr into a separate new .ldr artifact.

        Use this for a lossless round trip that preserves unknown payloads and the source file's CRC
        validity state; it does not change network logic. The source remains untouched and an
        existing output_name is rejected. Returns the new artifact link, size, SHA-256 and warnings.
        Use modify_network to insert, replace or delete logic, or generate_ldr for new Ladder IR.
        """
        return artifact_result(service.export(path, output_name))

    @mcp.tool(annotations=write)
    @structured_write_errors
    def modify_network(
        path: Annotated[
            str,
            Field(description="Existing source .ldr path inside the configured workspace."),
        ],
        output_name: Annotated[
            str,
            Field(
                description="New plain .ldr filename in the artifact directory; never overwrites."
            ),
        ],
        operation: Annotated[
            Literal["replace", "insert", "delete"],
            Field(description="Edit action: replace or delete index, or insert before index."),
        ],
        index: Annotated[
            int,
            Field(
                ge=0,
                description="Zero-based display-order network index; 0 identifies N000.",
            ),
        ],
        network: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Replacement or inserted Network IR object; required for replace/insert and "
                    "omitted for delete. Its full schema is in get_design_guide(detail=true)."
                )
            ),
        ] = None,
        allow_unverified: Annotated[
            bool,
            Field(
                description=(
                    "False rejects edits when unknown records prevent policy verification; true "
                    "permits that explicit risk while still preserving untouched records."
                )
            ),
        ] = False,
    ) -> Annotated[CallToolResult, ArtifactToolOutput]:
        """Edit one network in an existing .ldr and write the result to a new .ldr file.

        Use operation replace, insert or delete; index 0 is N000 and untouched raw records are
        preserved. Unlike get_capabilities, this changes program content; get_capabilities returns
        server metadata only. The source file is never overwritten.
        """
        network_model = Network.model_validate(network) if network is not None else None
        return artifact_result(
            service.edit(path, output_name, operation, index, network_model, allow_unverified)
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
