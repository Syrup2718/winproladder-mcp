import shutil
from pathlib import Path

import pytest

from winproladder_mcp.ir import Network, start_stop
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
