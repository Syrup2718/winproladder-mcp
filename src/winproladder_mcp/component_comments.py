"""WinProLadder component-comment interchange text format."""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .ldr import MAX_SIZE

ENCODING = "cp950"
HEADER = "REF\tCOMMENT\tDESCRIPTION"
MAX_ENTRIES = 10_000


class ComponentComment(BaseModel):
    """One row in a WinProLadder component-comment table."""

    model_config = ConfigDict(extra="forbid")

    ref: str = Field(min_length=1, max_length=64)
    comment: str = Field(default="", max_length=1000)
    description: str = Field(default="", max_length=4000)

    @field_validator("ref")
    @classmethod
    def canonical_ref(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", value):
            raise ValueError("REF must be an ASCII component identifier such as X0, M0 or D1")
        return value

    @field_validator("comment", "description")
    @classmethod
    def tab_safe_cp950(cls, value: str) -> str:
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError("COMMENT and DESCRIPTION cannot contain tabs, newlines or controls")
        try:
            value.encode(ENCODING, errors="strict")
        except UnicodeEncodeError as error:
            message = "COMMENT and DESCRIPTION must be representable in CP950/Big5"
            raise ValueError(message) from error
        return value


def render_component_comments(entries: list[ComponentComment]) -> bytes:
    """Render the sampled CP950, CRLF, tab-delimited import format."""
    if not 1 <= len(entries) <= MAX_ENTRIES:
        raise ValueError(f"Component comments require 1..{MAX_ENTRIES} entries")
    folded = [entry.ref.upper() for entry in entries]
    if len(folded) != len(set(folded)):
        raise ValueError("Component comments contain duplicate REF values")
    text = "\r\n".join(
        [HEADER, *(f"{entry.ref}\t{entry.comment}\t{entry.description}" for entry in entries)]
    ) + "\r\n"
    data = text.encode(ENCODING, errors="strict")
    if len(data) > MAX_SIZE:
        raise ValueError("Component-comment file exceeds 16 MiB limit")
    return data
