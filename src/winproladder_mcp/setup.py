"""Portable client configuration and real MCP connection self-check."""

import argparse
import asyncio
import base64
import hashlib
import json
import sys
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import BlobResourceContents, EmbeddedResource, ResourceLink
from pydantic import AnyUrl

from .design import design_guide
from .service import Service


def client_config(root: Path, output_dir: Path | None = None) -> dict[str, object]:
    root = root.resolve(strict=True)
    if output_dir is not None and not output_dir.is_absolute():
        output_dir = root / output_dir
    service = Service(root, output_dir)
    arguments = [
        "-m",
        "winproladder_mcp.server",
        "--compact-responses",
        "--root",
        str(service.root),
    ]
    if output_dir is not None:
        arguments.extend(["--output-dir", str(service.output)])
    return {
        "command": sys.executable,
        "args": arguments,
    }


def render_config(settings: dict[str, object], format_name: str) -> str:
    if format_name == "json":
        return json.dumps({"mcpServers": {"winproladder": settings}}, indent=2) + "\n"
    return (
        "[mcp_servers.winproladder]\n"
        "command = " + json.dumps(settings["command"]) + "\n"
        "args = " + json.dumps(settings["args"]) + "\n"
        "startup_timeout_sec = 30\ntool_timeout_sec = 60\n"
    )


def prepare(root: Path, config_dir: Path) -> None:
    """Create a workspace and standalone snippets; leave client settings untouched."""
    root.mkdir(parents=True, exist_ok=True)
    policy = root / ".winproladder-policy.json"
    try:
        with policy.open("x", encoding="utf-8") as stream:
            json.dump({"forbid_m_to_m": True, "allow_function_m_to_m": True}, stream, indent=2)
            stream.write("\n")
    except FileExistsError:
        pass
    settings = client_config(root)
    Service(root).architecture_policy()
    config_dir.mkdir(parents=True, exist_ok=True)
    for format_name, filename in [("json", "mcp-config.json"), ("codex", "mcp-config.toml")]:
        destination = config_dir / filename
        destination.write_text(render_config(settings, format_name), encoding="utf-8")
        print(f"Client configuration: {destination.resolve()}")
    print(f"Workspace: {root.resolve()}")
    print("Setup complete. Merge ONE configuration snippet into your MCP client and reconnect.")
    print("Keep this installation directory in place; configuration uses its absolute Python path.")


async def check(root: Path) -> None:
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "winproladder_mcp.server", "--root", str(root)]
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = (await session.list_tools()).tools
        required = {
            "generate_control_ldr",
            "generate_sequence_ldr",
            "generate_system_ldr",
            "generate_ldr",
            "get_design_guide",
            "get_capabilities",
            "get_ldr_artifact",
            "generate_component_comments",
            "create_start_stop",
            "read_ldr",
            "analyze_ldr",
            "compare_ldr",
        }
        if not required.issubset({tool.name for tool in tools}):
            raise RuntimeError("Missing required MCP tools")
        result = await session.call_tool("create_start_stop", {"output_name": "self-check.ldr"})
        if result.isError:
            raise RuntimeError(str(result.content))
        data = (root / "artifacts/self-check.ldr").read_bytes()
        if (
            hashlib.sha256(data).hexdigest()
            != "b917c9e8d50f38f6d6b568637e3afd3f0ef6091ea49a8aaca6b1b4f73db025b9"
        ):
            raise RuntimeError("Start-stop output does not match verified file")
        metadata = result.structuredContent
        if metadata is None or not any(isinstance(c, ResourceLink) for c in result.content):
            raise RuntimeError("Generation did not return a structured artifact and resource link")
        resource = await session.read_resource(AnyUrl(metadata["artifact"]["uri"]))
        if (
            len(resource.contents) != 1
            or not isinstance(resource.contents[0], BlobResourceContents)
            or base64.b64decode(resource.contents[0].blob, validate=True) != data
        ):
            raise RuntimeError("Resource download does not match the generated LDR")
        download = await session.call_tool("get_ldr_artifact", {"output_name": "self-check.ldr"})
        embedded = [item for item in download.content if isinstance(item, EmbeddedResource)]
        if (
            download.isError
            or len(embedded) != 1
            or not isinstance(embedded[0].resource, BlobResourceContents)
            or base64.b64decode(embedded[0].resource.blob, validate=True) != data
        ):
            raise RuntimeError("Artifact tool did not return the original binary LDR")
        comments = await session.call_tool(
            "generate_component_comments",
            {
                "output_name": "self-check-comments.txt",
                "entries": [
                    {"ref": "X0", "comment": "啟動", "description": "Start input"},
                    {"ref": "Y0", "comment": "馬達", "description": "Motor output"},
                ],
            },
        )
        comment_data = (root / "artifacts/self-check-comments.txt").read_bytes()
        if comments.isError or not comment_data.startswith(b"REF\tCOMMENT\tDESCRIPTION\r\n"):
            raise RuntimeError("Component-comment generation failed")
        comment_metadata = comments.structuredContent
        if comment_metadata is None:
            raise RuntimeError("Component-comment metadata is missing")
        comment_resource = await session.read_resource(AnyUrl(comment_metadata["artifact"]["uri"]))
        if (
            len(comment_resource.contents) != 1
            or not isinstance(comment_resource.contents[0], BlobResourceContents)
            or base64.b64decode(comment_resource.contents[0].blob, validate=True) != comment_data
        ):
            raise RuntimeError("Component-comment resource download does not match the text file")
        generated = await session.call_tool(
            "generate_control_ldr",
            {
                "output_name": "requirement-check.ldr",
                "io_contract": {"inputs": ["X0", "X1"], "outputs": ["Y0"]},
                "spec": {
                    "requirement": "X0 starts Y0, X1 stops it; keep running after releasing X0",
                    "kind": "start_stop",
                    "signal": "X0",
                    "stop": "X1",
                    "output": 0,
                },
                "acceptance": design_guide()["acceptance_example"],
            },
        )
        if generated.isError or generated.structuredContent is None:
            raise RuntimeError("Requirement-to-LDR generation failed")
        if not generated.structuredContent["acceptance"]["passed"]:
            raise RuntimeError("Generated control failed its behavior acceptance cases")
        for name, arguments in [
            ("analyze_ldr", {"path": "artifacts/self-check.ldr"}),
            (
                "compare_ldr",
                {"left_path": "artifacts/self-check.ldr", "right_path": "artifacts/self-check.ldr"},
            ),
        ]:
            if (await session.call_tool(name, arguments)).isError:
                raise RuntimeError(f"{name} self-check failed")
        print(
            f"PASS: MCP connection, {len(tools)} tools, requirement-to-LDR acceptance, "
            "verified SHA-256, LDR download and CP950 component-comment artifact"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    config = sub.add_parser("config", help="Print client config; never overwrite existing settings")
    config.add_argument("--format", choices=["codex", "json"], default="codex")
    config.add_argument("--root", type=Path, default=Path.cwd())
    config.add_argument(
        "--output-dir", type=Path, help="Output subdirectory; relative paths are resolved from root"
    )
    sub.add_parser("check", help="Test real stdio MCP in a temporary workspace; repeatable")
    prepare_parser = sub.add_parser("prepare", help="Create workspace and client config snippets")
    prepare_parser.add_argument("--root", type=Path, required=True)
    prepare_parser.add_argument("--config-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "check":
        with tempfile.TemporaryDirectory(prefix="winproladder-check-") as directory:
            asyncio.run(asyncio.wait_for(check(Path(directory)), timeout=60))
    elif args.command == "prepare":
        try:
            prepare(args.root, args.config_dir)
        except (OSError, ValueError) as error:
            parser.error(str(error))
    else:
        try:
            settings = client_config(args.root, args.output_dir)
        except (OSError, ValueError) as error:
            parser.error(str(error))
        print(render_config(settings, args.format), end="")


if __name__ == "__main__":
    main()
