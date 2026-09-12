import shutil
from pathlib import Path

import pytest

from winproladder_mcp.ir import Ladder, Network, start_stop
from winproladder_mcp.ldr import parse
from winproladder_mcp.service import Service


@pytest.fixture
def service(tmp_path: Path) -> Service:
    (tmp_path / "samples").mkdir()
    for path in (Path(__file__).parents[1] / "samples").glob("*.ldr"):
        shutil.copyfile(path, tmp_path / "samples" / path.name)
    return Service(tmp_path)


def test_create_read_export(service: Service) -> None:
    created = service.create("motor.ldr", start_stop())
    doc = service.read("artifacts/motor.ldr")
    assert doc["networks"][0]["logic"] == start_stop().networks[0].model_dump()
    exported = service.export("artifacts/motor.ldr", "motor-copy.ldr")
    assert Path(created["path"]).read_bytes() == Path(exported["path"]).read_bytes()
    assert service.inspect("artifacts/motor.ldr")["editable"]
    with pytest.raises(FileExistsError):
        service.create("motor.ldr", start_stop())


def test_edits_preserve_unknown_networks(service: Service) -> None:
    original = service.load("samples/test3.ldr")
    network = start_stop().networks[0]
    result = service.edit("samples/test3.ldr", "modified.ldr", "replace", 0, network, True)
    edited = parse(Path(result["path"]).read_bytes())
    assert edited.records[:-1] == original.records[:-1]
    assert edited.records[-1].payload == bytes.fromhex("4100a0009001c100")
    service.edit("samples/test3.ldr", "inserted.ldr", "insert", 1, Network(empty=True), True)
    assert len(service.load("artifacts/inserted.ldr").records) == 13
    service.edit("artifacts/inserted.ldr", "deleted.ldr", "delete", 1, None, True)
    assert service.load("artifacts/deleted.ldr").encode() == original.encode()


@pytest.mark.parametrize("name", ["../evil.ldr", "samples/a.ldr", "x:y.ldr", "x.txt", ".x.ldr"])
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
        service.edit("samples/test.ldr", "x.ldr", "delete", 0, None, False)
    with pytest.raises(ValueError):
        service.edit("samples/test.ldr", "x.ldr", "delete", 100, None, True)


def test_block_program_ir_roundtrip(service: Service) -> None:
    read = service.read("samples/test3.ldr")
    ladder = Ladder.model_validate(read["ladder"])
    created = service.create("block-program.ldr", ladder, True)
    assert Path(created["path"]).read_bytes() == service.source("samples/test3.ldr").read_bytes()
    analysis = service.analyze("samples/test3.ldr")
    assert analysis["decoded_count"] == 12
    assert analysis["references"]["complete"] is True
    assert analysis["references"]["devices"]["C1"] == {"reads": [10], "writes": [7]}
    assert analysis["references"]["devices"]["M2"] == {"reads": [11], "writes": [10]}
    assert "preset=256" in analysis["networks"][4]["description"]


def test_incomplete_cross_references(service: Service) -> None:
    analysis = service.analyze("samples/test4.ldr")
    assert analysis["references"]["complete"] is False
    assert analysis["references"]["opaque_networks"] == [5, 6]
    assert analysis["warnings"]
    assert service.read("samples/test4.ldr")["ladder"] is None


def test_compare_insert_delete_replace(service: Service) -> None:
    assert service.compare("samples/test3.ldr", "samples/test3.ldr")["changes"] == []
    service.edit("samples/test3.ldr", "insert.ldr", "insert", 2, start_stop().networks[0], True)
    changes = service.compare("samples/test3.ldr", "artifacts/insert.ldr")["changes"]
    assert len(changes) == 1
    assert changes[0]["operation"] == "insert"
    assert changes[0]["left_range"] == [2, 2]
    assert changes[0]["right_range"] == [2, 3]
    reverse = service.compare("artifacts/insert.ldr", "samples/test3.ldr")["changes"]
    assert reverse[0]["operation"] == "delete"
    service.edit("samples/test3.ldr", "replace.ldr", "replace", 0, start_stop().networks[0], True)
    changes = service.compare("samples/test3.ldr", "artifacts/replace.ldr")["changes"]
    assert len(changes) == 1
    assert changes[0]["operation"] == "replace"
    assert changes[0]["left_range"] == [0, 1]


def test_compare_crc_only_change(service: Service) -> None:
    data = bytearray(service.source("samples/w1.ldr").read_bytes())
    data[269] ^= 1
    (service.root / "corrupt.ldr").write_bytes(data)
    changes = service.compare("samples/w1.ldr", "corrupt.ldr")["changes"]
    assert changes[0]["left"][0]["payload_hex"] == changes[0]["right"][0]["payload_hex"]
    assert changes[0]["right"][0]["crc_valid"] is False
