"""Files must reach an MCP client even without a shared server filesystem."""

import asyncio
import base64
import hashlib
import json
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import McpError
from mcp.types import BlobResourceContents, EmbeddedResource, ResourceLink, TextContent
from pydantic import AnyUrl


def test_binary_artifact_delivery_and_scope(tmp_path: Path) -> None:
    output = tmp_path / "delivery folder"
    (tmp_path / "private.ldr").write_bytes(b"outside output directory")

    async def run() -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=[
                "-m",
                "winproladder_mcp.server",
                "--root",
                str(tmp_path),
                "--output-dir",
                str(output),
            ],
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            templates = (await session.list_resource_templates()).resourceTemplates
            assert any(t.uriTemplate == "winproladder://artifacts/{name}" for t in templates)
            for name in ["motor.ldr", "馬達 控制 #100%23.ldr"]:
                result = await session.call_tool("create_start_stop", {"output_name": name})
                assert not result.isError, result.content
                assert result.structuredContent is not None
                metadata = result.structuredContent
                assert isinstance(result.content[0], TextContent)
                assert json.loads(result.content[0].text) == metadata
                link = next(item for item in result.content if isinstance(item, ResourceLink))
                assert link.name == name
                assert link.mimeType == "application/octet-stream"
                assert str(link.uri) == metadata["artifact"]["uri"]
                downloaded = await session.read_resource(link.uri)
                resource = downloaded.contents[0]
                assert isinstance(resource, BlobResourceContents)
                data = base64.b64decode(resource.blob, validate=True)
                assert data == (output / name).read_bytes()
                assert link.size == metadata["size"] == len(data)
                assert hashlib.sha256(data).hexdigest() == metadata["sha256"]
                via_tool = await session.call_tool("get_ldr_artifact", {"output_name": name})
                assert not via_tool.isError, via_tool.content
                embedded = next(c for c in via_tool.content if isinstance(c, EmbeddedResource))
                assert isinstance(embedded.resource, BlobResourceContents)
                assert base64.b64decode(embedded.resource.blob, validate=True) == data
                assert via_tool.structuredContent["artifact"] == metadata["artifact"]
                duplicate = await session.call_tool("create_start_stop", {"output_name": name})
                assert duplicate.isError
                assert (output / name).read_bytes() == data
            (output / "notes.txt").write_text("not an LDR", encoding="utf-8")
            for name in ["../private.ldr", "..\\private.ldr", "notes.txt", "missing.ldr"]:
                denied = await session.call_tool("get_ldr_artifact", {"output_name": name})
                assert denied.isError, name
            with pytest.raises(McpError):
                await session.read_resource(AnyUrl("winproladder://artifacts/..%2Fprivate.ldr"))

        # Artifact links remain usable after a server restart; no in-memory registry is needed.
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            downloaded = await session.read_resource(link.uri)
            resource = downloaded.contents[0]
            assert isinstance(resource, BlobResourceContents)
            assert base64.b64decode(resource.blob, validate=True) == data

    asyncio.run(asyncio.wait_for(run(), timeout=60))
