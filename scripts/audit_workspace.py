"""Read-only workspace inventory and integrity audit; never deletes or moves files."""

import argparse
import ast
import hashlib
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote

from winproladder_mcp.ldr import parse


def audit(root: Path) -> dict:
    root = root.resolve(strict=True)
    files = []
    errors = []
    links = []
    local_links = []
    duplicates = defaultdict(list)
    totals = defaultdict(lambda: {"files": 0, "bytes": 0})
    ldrs = []
    for current, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(current) / d).is_symlink())
        for name in sorted(names):
            p = Path(current) / name
            if p.is_symlink():
                continue
            rel = p.relative_to(root).as_posix()
            parts = p.relative_to(root).parts
            try:
                size = p.stat().st_size
                totals[parts[0]]["files"] += 1
                totals[parts[0]]["bytes"] += size
                environment = parts[0] in {
                    ".git",
                    ".venv",
                    ".install",
                    ".mypy_cache",
                    ".pytest_cache",
                    ".ruff_cache",
                }
                environment |= "__pycache__" in parts
                environment |= (
                    len(parts) > 1
                    and parts[0] == "tmp"
                    and (parts[1] == "mypy-pure" or parts[1].startswith("wheel-v"))
                )
                if environment:
                    continue  # Count environment files; do not audit third-party implementation.
                raw = p.read_bytes()
                digest = hashlib.sha256(raw).hexdigest()
                files.append({"path": rel, "size": size, "sha256": digest})
                if size:
                    duplicates[digest].append(rel)
                current_code = parts[0] in {"src", "tests", "scripts"} and "research" not in parts
                if p.suffix == ".py" and current_code:
                    ast.parse(raw, filename=rel)
                if p.suffix == ".json" and parts[0] != "tmp":
                    json.loads(raw)
                if p.suffix.lower() == ".ldr" and parts[0] in {"samples", "artifacts", "tests"}:
                    try:
                        doc = parse(raw)
                        ldrs.append(
                            {
                                "path": rel,
                                "records": len(doc.records),
                                "crc_valid": True,
                                "editable": doc.editable,
                            }
                        )
                    except ValueError as exc:
                        ldrs.append({"path": rel, "error": str(exc)})
                if p.suffix == ".md" and parts[0] not in {"tmp", ".git"}:
                    text = raw.decode("utf-8-sig")
                    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
                        if "://" in target or target.startswith("#"):
                            continue
                        dest = (p.parent / unquote(target.split("#", 1)[0])).resolve()
                        if not dest.exists():
                            links.append({"document": rel, "target": target})
                        if (
                            dest != root
                            and dest.is_relative_to(root)
                            and dest.relative_to(root).parts[0]
                            in {
                                "tmp",
                                "artifacts",
                                "dist",
                            }
                        ):
                            local_links.append({"document": rel, "target": target})
            except (OSError, ValueError, SyntaxError) as exc:
                errors.append({"path": rel, "error": str(exc)})
    return {
        "root": str(root),
        "scope": "All regular files counted; Git/venv/tool environments "
        "and caches excluded from content audit; symlinks not traversed. "
        "No secret contents emitted.",
        "totals": dict(sorted(totals.items())),
        "inventory": files,
        "duplicate_content": [v for v in duplicates.values() if len(v) > 1],
        "content_errors": errors,
        "broken_links": links,
        "local_only_links": local_links,
        "ldr_checks": ldrs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--output", type=Path, required=True, help="New JSON report; never overwrite"
    )
    args = parser.parse_args()
    result = audit(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(
        json.dumps(
            {
                "report": str(args.output),
                "files": sum(t["files"] for t in result["totals"].values()),
                "content_errors": result["content_errors"],
                "broken_links": result["broken_links"],
                "ldr_errors": [r for r in result["ldr_checks"] if "error" in r],
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
