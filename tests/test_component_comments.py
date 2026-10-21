"""Exact component-comment text format and MCP artifact delivery."""

import asyncio
import base64
import hashlib
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import BlobResourceContents, EmbeddedResource, ResourceLink
from pydantic import AnyUrl, ValidationError

from winproladder_mcp.component_comments import ComponentComment, render_component_comments
from winproladder_mcp.service import Service

SAMPLE_ENTRIES = [
    ComponentComment(ref="X0", comment="owo"),
    ComponentComment(ref="Y0", comment="早安"),
    ComponentComment(ref="M0", comment="meow", description="wad"),
    ComponentComment(ref="S0", comment="cialo"),
    ComponentComment(ref="T0", comment="momo"),
    ComponentComment(ref="C0", comment="meme", description="awa"),
    ComponentComment(ref="R0", comment="www"),
    ComponentComment(ref="D0", comment="aaa"),
    ComponentComment(ref="D1", description="wwwawads"),
]
SAMPLE_BYTES = bytes.fromhex(
    "52454609434f4d4d454e54094445534352495054494f4e0d0a"
    "5830096f776f090d0a593009a6ada677090d0a4d30096d656f77097761640d0a"
    "5330096369616c6f090d0a5430096d6f6d6f090d0a4330096d656d6509617761"
    "0d0a523009777777090d0a443009616161090d0a4431090977777761776164730d0a"
)


def test_component_comment_bytes_match_supplied_sample() -> None:
    data = render_component_comments(SAMPLE_ENTRIES)
    assert data == SAMPLE_BYTES
    assert len(data) == 123
    assert hashlib.sha256(data).hexdigest() == (
        "16b60fcf79bcaead9fdf54b0b462b62263d139d843750e5816e32ddc9c85555a"
    )
    assert data.decode("cp950").splitlines()[0] == "REF\tCOMMENT\tDESCRIPTION"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("ref", "X 0"),
        ("comment", "bad\ttab"),
        ("description", "bad\nline"),
        ("comment", "emoji 😀"),
    ],
)
def test_component_comment_rejects_invalid_fields(field: str, value: str) -> None:
    values = {"ref": "X0", "comment": "", "description": "", field: value}
    with pytest.raises(ValidationError):
        ComponentComment.model_validate(values)


def test_component_comment_writer_is_scoped_and_never_overwrites(tmp_path: Path) -> None:
    service = Service(tmp_path)
    result = service.write_component_comments("comments.txt", SAMPLE_ENTRIES)
    assert Path(result["path"]).read_bytes() == SAMPLE_BYTES
    assert result["format"]["encoding"] == "CP950/Big5"
    with pytest.raises(FileExistsError):
        service.write_component_comments("comments.txt", SAMPLE_ENTRIES)
    with pytest.raises(ValueError, match=r"plain \.txt filename"):
        service.write_component_comments("../escape.txt", SAMPLE_ENTRIES)
    with pytest.raises(ValueError, match="duplicate REF"):
        render_component_comments(
            [ComponentComment(ref="X0"), ComponentComment(ref="x0")]
        )


def test_component_comment_stdio_generation_and_download(tmp_path: Path) -> None:
    async def run() -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "winproladder_mcp.server", "--root", str(tmp_path)],
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "generate_component_comments",
                {
                    "output_name": "元件註解.txt",
                    "entries": [entry.model_dump() for entry in SAMPLE_ENTRIES],
                },
            )
            assert not result.isError, result.content
            metadata = result.structuredContent
            assert metadata is not None
            assert metadata["entry_count"] == 9
            assert metadata["artifact"]["mime_type"] == (
                "text/tab-separated-values; charset=big5"
            )
            link = next(item for item in result.content if isinstance(item, ResourceLink))
            embedded = next(item for item in result.content if isinstance(item, EmbeddedResource))
            assert link.name == "元件註解.txt"
            assert isinstance(embedded.resource, BlobResourceContents)
            assert base64.b64decode(embedded.resource.blob, validate=True) == SAMPLE_BYTES
            downloaded = await session.read_resource(AnyUrl(metadata["artifact"]["uri"]))
            resource = downloaded.contents[0]
            assert isinstance(resource, BlobResourceContents)
            assert base64.b64decode(resource.blob, validate=True) == SAMPLE_BYTES

    asyncio.run(asyncio.wait_for(run(), timeout=60))
