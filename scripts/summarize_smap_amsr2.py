#!/usr/bin/env python3
"""Write a descriptive QA report for a collocated SMAP-AMSR2 CSV."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from statistics import mean, pstdev


def _numbers(rows: list[dict[str, str]], field: str) -> list[float]:
    values = []
    for row in rows:
        value = row.get(field, "")
        if value:
            try:
                number = float(value)
            except ValueError:
                continue
            if math.isfinite(number):
                values.append(number)
    return values


def _percentile(values: list[float], percent: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * percent / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _correlation(x: list[float], y: list[float]) -> float | None:
    if len(x) != len(y) or len(x) < 2:
        return None
    x_mean, y_mean = mean(x), mean(y)
    x_centered = [value - x_mean for value in x]
    y_centered = [value - y_mean for value in y]
    denominator = math.sqrt(sum(value**2 for value in x_centered) * sum(value**2 for value in y_centered))
    if denominator == 0:
        return None
    return sum(a * b for a, b in zip(x_centered, y_centered)) / denominator


def _stats(values: list[float], total: int) -> str:
    if not values:
        return "0 | — | — | — | — | — | —"
    return " | ".join(
        (
            str(len(values)),
            f"{100 * (1 - len(values) / total):.2f}%",
            f"{mean(values):.3f}",
            f"{pstdev(values):.3f}",
            f"{_percentile(values, 5):.3f}",
            f"{_percentile(values, 50):.3f}",
            f"{_percentile(values, 95):.3f}",
        )
    )


def summarize(input_csv: Path, output_md: Path) -> dict[str, int | float]:
    with input_csv.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"No rows found in {input_csv}")

    distance = _numbers(rows, "amsr2_center_distance_km")
    latitude = _numbers(rows, "cell_lat")
    sic = _numbers(rows, "amsr2_product_sic_dsc_percent")
    channel_fields = [
        field
        for field in rows[0]
        if field.startswith("amsr2_") and field.endswith("_tb_k") and "_dsc_" in field
    ]

    lines = [
        "# SMAP-AMSR2 collocation: exploratory QA",
        "",
        f"Input: `{input_csv.as_posix()}`",
        "",
        "## Sample and spatial match",
        "",
        f"- SMAP quality-screened candidate rows: {len(rows):,}",
        f"- AMSR2 matches within the configured radius: {sum(row.get('amsr2_within_distance', '').lower() == 'true' for row in rows):,}",
        f"- Latitude span: {min(latitude):.2f}°N to {max(latitude):.2f}°N",
        f"- SMAP-to-AMSR2 center distance: median { _percentile(distance, 50):.2f} km; 95th percentile { _percentile(distance, 95):.2f} km; maximum {max(distance):.2f} km",
        "",
        "## Brightness-temperature coverage",
        "",
        "All temperatures are in kelvin. Missing percentage is measured against the collocated candidate rows.",
        "",
        "| Channel | Valid | Missing | Mean | Std. dev. | P05 | Median | P95 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for field in channel_fields:
        values = _numbers(rows, field)
        lines.append(f"| {field} | {_stats(values, len(rows))} |")

    lines.extend(
        (
            "",
            "## AMSR2 product concentration field",
            "",
            f"- Valid descending-pass product values: {len(sic):,} / {len(rows):,}",
        )
    )
    if sic:
        lines.extend(
            (
                f"- Range: {min(sic):.1f}%–{max(sic):.1f}%; mean {mean(sic):.2f}%; standard deviation {pstdev(sic):.2f} percentage points.",
                "- The source product codes 0 as open water, 110 as missing/not calculated, and 120 as land. The collocation CSV leaves 110 and 120 blank.",
            )
        )

    lines.extend(
        (
            "",
            "## Descriptive cross-sensor correlations",
            "",
            "Pearson r uses valid row pairs. SMAP aft H/V brightness temperatures are compared with descending-pass AMSR2 10.7 GHz and 36.5 GHz H/V channels.",
            "",
            "| SMAP channel | AMSR2 channel | Pairs | Pearson r |",
            "|---|---|---:|---:|",
        )
    )
    for smap_field in ("cell_tb_v_aft", "cell_tb_h_aft"):
        for amsr_field in (
            "amsr2_10H_dsc_tb_k",
            "amsr2_10V_dsc_tb_k",
            "amsr2_36H_dsc_tb_k",
            "amsr2_36V_dsc_tb_k",
        ):
            paired = [(float(row[smap_field]), float(row[amsr_field])) for row in rows if row.get(smap_field) and row.get(amsr_field)]
            r = _correlation([pair[0] for pair in paired], [pair[1] for pair in paired])
            rendered = "—" if r is None else f"{r:.3f}"
            lines.append(f"| {smap_field} | {amsr_field} | {len(paired):,} | {rendered} |")

    lines.extend(
        (
            "",
            "## Interpretation and limits",
            "",
            "This is a single-date, one-half-orbit exploratory sample. Spatial nearest-neighbor coverage is good for this sample, but the AMSR2 data are daily composites and are not instantaneous matches to the SMAP measurements. The AMSR2 concentration field is an existing sensor-product retrieval, not independent validation truth. Its narrow value range on this date also provides little target variation for training. These summaries do not estimate retrieval accuracy or establish physical causation between channels.",
            "",
        )
    )

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines), encoding="utf-8")
    return {
        "rows": len(rows),
        "valid_sic": len(sic),
        "median_distance_km": _percentile(distance, 50),
        "max_distance_km": max(distance),
        "output_bytes": output_md.stat().st_size,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("collocated_csv", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/processed/smap_amsr2_20160131_summary.md"))
    args = parser.parse_args()
    if not args.collocated_csv.is_file():
        parser.error(f"collocation CSV not found: {args.collocated_csv}")
    stats = summarize(args.collocated_csv, args.output)
    print(f"Wrote {args.output} ({stats['output_bytes']:,} bytes)")
    for name, value in stats.items():
        if name != "output_bytes":
            print(f"{name}: {value}")


if __name__ == "__main__":
    main()
