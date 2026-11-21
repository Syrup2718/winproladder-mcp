from pathlib import Path

import pytest

from winproladder_mcp.ir import Ladder, Network, start_stop
from winproladder_mcp.ldr import parse
from winproladder_mcp.service import Service


@pytest.fixture
def service(tmp_path: Path) -> Service:
    instance = Service(tmp_path)
    instance.create("source.ldr", start_stop())
    return instance


def test_create_read_export(service: Service) -> None:
    document = service.read("artifacts/source.ldr")
    assert document["networks"][0]["logic"] == start_stop().networks[0].model_dump()
    exported = service.export("artifacts/source.ldr", "source-copy.ldr")
    assert (
        service.source("artifacts/source.ldr").read_bytes() == Path(exported["path"]).read_bytes()
    )
    assert service.inspect("artifacts/source.ldr")["editable"]
    with pytest.raises(FileExistsError):
        service.create("source.ldr", start_stop())


def test_insert_delete_replace_and_compare(service: Service) -> None:
    service.edit("artifacts/source.ldr", "inserted.ldr", "insert", 1, Network(empty=True), True)
    assert len(service.load("artifacts/inserted.ldr").records) == 2
    service.edit("artifacts/inserted.ldr", "deleted.ldr", "delete", 1, None, True)
    assert (
        service.load("artifacts/deleted.ldr").encode()
        == service.load("artifacts/source.ldr").encode()
    )
    replacement = Network(condition="X2", coils=[{"address": 2}])
    service.edit("artifacts/source.ldr", "replaced.ldr", "replace", 0, replacement, True)
    changes = service.compare("artifacts/source.ldr", "artifacts/replaced.ldr")["changes"]
    assert [change["operation"] for change in changes] == ["replace"]


@pytest.mark.parametrize("name", ["../evil.ldr", "nested/a.ldr", "x:y.ldr", "x.txt", ".x.ldr"])
def test_write_path_rejected(service: Service, name: str) -> None:
    with pytest.raises(ValueError):
        service.create(name, start_stop())


def test_read_escape_and_output_source_rejected(service: Service, tmp_path: Path) -> None:
    with pytest.raises((ValueError, FileNotFoundError)):
        service.source("../escape.ldr")
    with pytest.raises(ValueError):
        Service(tmp_path, tmp_path / "samples")
    with pytest.raises(ValueError):
        Service(tmp_path, tmp_path.parent)
    with pytest.raises(ValueError):
        service.create("unverified.ldr", start_stop(False))
    with pytest.raises(ValueError):
        service.edit("artifacts/source.ldr", "x.ldr", "delete", 100, None, True)


def test_generated_program_ir_roundtrip_and_analysis(service: Service) -> None:
    read = service.read("artifacts/source.ldr")
    ladder = Ladder.model_validate(read["ladder"])
    created = service.create("roundtrip.ldr", ladder, True)
    assert Path(created["path"]).read_bytes() == service.source("artifacts/source.ldr").read_bytes()
    analysis = service.analyze("artifacts/source.ldr")
    assert analysis["decoded_count"] == 1
    assert analysis["references"]["complete"] is True


def test_compare_crc_only_change(service: Service) -> None:
    data = bytearray(service.source("artifacts/source.ldr").read_bytes())
    document = parse(bytes(data))
    first_record_end = 256 + len(document.records[0].encode())
    data[first_record_end - 1] ^= 1
    (service.root / "corrupt.ldr").write_bytes(data)
    changes = service.compare("artifacts/source.ldr", "corrupt.ldr")["changes"]
    assert changes[0]["left"][0]["payload_hex"] == changes[0]["right"][0]["payload_hex"]
    assert changes[0]["right"][0]["crc_valid"] is False
