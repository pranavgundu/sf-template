"""CSV validation, descriptive statistics, and figures."""

import csv
from datetime import datetime, timezone
import hashlib
import html
import io
import json
import math
from pathlib import Path
import statistics
import sys

from . import __version__


def read_measurements(raw_bytes, replicates):
    reader = csv.DictReader(io.StringIO(raw_bytes.decode("utf-8-sig"), newline=""))
    fields = reader.fieldnames or []
    if len(fields) != len(set(fields)):
        raise ValueError("CSV has duplicate column names.")
    if not {"unit_id", "group", "value"}.issubset(fields):
        raise ValueError("CSV needs unit_id,group,value columns (and optionally unit).")
    records = {}
    units = set()
    rows = 0
    for line, row in enumerate(reader, start=2):
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"Row {line}: number of fields does not match the header.")
        unit_id, group = row["unit_id"].strip(), row["group"].strip()
        if not unit_id or not group:
            raise ValueError(f"Row {line}: unit_id and group must not be empty.")
        try:
            value = float(row["value"])
        except ValueError:
            raise ValueError(f"Row {line}: value must be a number; missing values need an explicit decision.") from None
        if not math.isfinite(value):
            raise ValueError(f"Row {line}: value must be finite.")
        units.add(row.get("unit", "").strip())
        if unit_id in records:
            old_group, values = records[unit_id]
            if old_group != group:
                raise ValueError(f"Row {line}: unit {unit_id!r} occurs in multiple groups. Paired designs need a different analysis.")
            if replicates != "mean":
                raise ValueError(f"Row {line}: repeated unit {unit_id!r}; use --replicates mean only for repeated readings of that unit.")
            values.append(value)
        else:
            records[unit_id] = (group, [value])
        rows += 1
    if not records:
        raise ValueError("CSV contains no measurements.")
    if len(units) > 1:
        raise ValueError("Mixed or partially missing measurement units. Convert to one unit before analysis.")
    groups = {}
    for group, values in records.values():
        groups.setdefault(group, []).append(statistics.mean(values))
    summary = []
    for group, values in sorted(groups.items()):
        result = {
            "group": group, "n": len(values), "mean": statistics.mean(values),
            "median": statistics.median(values),
            "sd": statistics.stdev(values) if len(values) > 1 else None,
            "min": min(values), "max": max(values),
        }
        if any(isinstance(v, float) and not math.isfinite(v) for v in result.values()):
            raise ValueError("Measurements exceed the supported numeric range; rescale values.")
        summary.append(result)
    return summary, units.pop(), rows, len(records)


def chart_svg(summary, unit):
    """A dot-and-range chart: group mean and observed min/max, not inference."""
    low = min(s["min"] for s in summary)
    high = max(s["max"] for s in summary)
    span = high - low
    if not math.isfinite(span):
        raise ValueError("Measurement range is too large to chart; rescale values.")
    padding = span * 0.08 if span else max(abs(low) * 0.08, 1)
    low, high = low - padding, high + padding
    if not math.isfinite(high - low):
        raise ValueError("Measurement range is too large to chart; rescale values.")
    def x(value):
        return 270 + (value - low) / (high - low) * 470
    height = 145 + 56 * len(summary)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="840" height="{height}" viewBox="0 0 840 {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Group means and observed ranges</title>',
        '<desc id="desc">Dots show means. Lines show minimum to maximum. These are not confidence intervals.</desc>',
        '<rect width="100%" height="100%" fill="#faf9f5"/>',
        '<g font-family="system-ui, sans-serif" fill="#183d36">',
        '<text x="28" y="35" font-size="21">Group means &amp; observed ranges</text>',
        f'<text x="28" y="59" font-size="13">{html.escape(unit or "Value (unit unspecified)")} · dot = mean · line = min–max · n = independent units</text>',
    ]
    for index, row in enumerate(summary):
        y = 97 + index * 56
        name = html.escape(str(row["group"]))
        label = name if len(str(row["group"])) <= 24 else html.escape(str(row["group"])[:21] + "…")
        lines.extend([
            f'<text x="28" y="{y + 5}" font-size="14"><title>{name}</title>{label} (n={row["n"]})</text>',
            f'<line x1="{x(row["min"]):.2f}" x2="{x(row["max"]):.2f}" y1="{y}" y2="{y}" stroke="#518579" stroke-width="3"/>',
            f'<circle cx="{x(row["mean"]):.2f}" cy="{y}" r="6" fill="#183d36"><title>{name}: mean {row["mean"]:.6g}</title></circle>',
            f'<text x="765" y="{y + 5}" font-size="12">{row["mean"]:.4g}</text>',
        ])
    axis_y = height - 47
    lines.append(f'<line x1="270" x2="740" y1="{axis_y}" y2="{axis_y}" stroke="#9daaa5"/>')
    for i in range(5):
        value = low + (high - low) * i / 4
        lines.append(f'<text x="{270 + i * 117.5}" y="{axis_y + 23}" text-anchor="middle" font-size="12">{value:.4g}</text>')
    lines.append('</g></svg>\n')
    return "\n".join(lines)


def analyze(source, output, replicates="error"):
    source, output = Path(source), Path(output)
    if output.exists():
        raise ValueError(f"Output already exists: {output}. Choose a new folder to preserve previous runs.")
    raw = source.read_bytes()
    summary, unit, rows, count = read_measurements(raw, replicates)
    svg = chart_svg(summary, unit)
    manifest = {
        "tool": "sf-template", "version": __version__,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version, "input_filename": source.name,
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "input_rows": rows, "independent_units": count, "measurement_unit": unit,
        "replicates": replicates,
        "method": "Descriptive statistics across independent units; sample SD (n-1); no hypothesis test.",
    }
    output.mkdir(parents=True, exist_ok=False)
    with (output / "summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    (output / "chart.svg").write_text(svg, encoding="utf-8")
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return summary
