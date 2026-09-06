"""Run a configured analysis: uv run python -m project.main."""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import tomllib

from .analysis import analyze

ROOT = Path(__file__).resolve().parent.parent


def load_config(path):
    config = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    if config.get("method") not in ("summary", "source-inventory"):
        raise ValueError("method must be summary or source-inventory")
    if not isinstance(config.get("input"), str) or not config["input"].strip():
        raise ValueError("input must be a nonempty file path")
    if config.get("replicates", "error") not in ("error", "mean"):
        raise ValueError("replicates must be error or mean")
    return config


def source_inventory(source, output):
    raw = source.read_bytes()
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    fields = reader.fieldnames or []
    if len(set(fields)) != len(fields) or not {"source_id", "title", "url_or_doi"}.issubset(fields):
        raise ValueError("Source CSV needs unique headers including source_id,title,url_or_doi")
    ids = set()
    for line, row in enumerate(reader, 2):
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"Row {line}: wrong number of fields")
        source_id = row["source_id"].strip()
        if not source_id or source_id in ids or not row["title"].strip():
            raise ValueError(f"Row {line}: source IDs must be unique and IDs and titles nonempty")
        ids.add(source_id)
    output.mkdir(parents=True, exist_ok=False)
    (output / "inventory.json").write_text(json.dumps({
        "sources": len(ids), "input_sha256": hashlib.sha256(raw).hexdigest(),
    }, indent=2) + "\n", encoding="utf-8")


def run(config_path, output):
    config = load_config(config_path)
    output = Path(output)
    if output.exists():
        raise ValueError(f"Output already exists: {output}")
    source = ROOT / config["input"]
    # Record the effective configuration and the exact code used for this run.
    record = {
        "config": config,
        "python": sys.version,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "code_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((ROOT / "project").rglob("*.py"))
        },
    }
    if config["method"] == "summary":
        analyze(source, output, config.get("replicates", "error"))
    else:
        source_inventory(source, output)
    (output / "run.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run an experiment from a TOML config.")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/experiment.toml")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    output = args.output or ROOT / "results" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    try:
        run(args.config, output)
    except (ValueError, OSError, UnicodeError, csv.Error, OverflowError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    print(f"Results: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
