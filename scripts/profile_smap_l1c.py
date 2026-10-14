#!/usr/bin/env python3
"""Summarize the polar-grid content of a SMAP L1C TB HDF5 granule."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import h5py
import numpy as np


TB_FIELDS = (
    "cell_tb_v_aft",
    "cell_tb_h_aft",
    "cell_tb_v_fore",
    "cell_tb_h_fore",
    "cell_tb_v_surface_corrected_aft",
    "cell_tb_h_surface_corrected_aft",
    "cell_tb_v_surface_corrected_fore",
    "cell_tb_h_surface_corrected_fore",
)
QC_FIELDS = (
    "cell_tb_qual_flag_v_aft",
    "cell_tb_qual_flag_h_aft",
    "cell_tb_qual_flag_v_fore",
    "cell_tb_qual_flag_h_fore",
)


def _decode(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").rstrip("\x00")
    return str(value)


def _valid_numeric(dataset: h5py.Dataset) -> np.ndarray:
    values = dataset[...]
    valid = np.isfinite(values)
    fill = dataset.attrs.get("_FillValue")
    if fill is not None:
        valid &= values != fill
    minimum = dataset.attrs.get("valid_min")
    maximum = dataset.attrs.get("valid_max")
    if minimum is not None:
        valid &= values >= minimum
    if maximum is not None:
        valid &= values <= maximum
    return values[valid]


def _profile_group(group: h5py.Group) -> None:
    count = len(group["cell_lat"])
    lat = group["cell_lat"][...]
    lon = group["cell_lon"][...]
    coordinate_valid = np.isfinite(lat) & np.isfinite(lon) & (np.abs(lat) <= 90) & (np.abs(lon) <= 180)
    print(f"  cells: {count}; valid coordinates: {int(coordinate_valid.sum())}")
    if coordinate_valid.any():
        print(
            "  coverage: "
            f"lat {lat[coordinate_valid].min():.2f}..{lat[coordinate_valid].max():.2f}, "
            f"lon {lon[coordinate_valid].min():.2f}..{lon[coordinate_valid].max():.2f} degrees"
        )

    print("  note: TB counts use fill/range checks only; quality flags are reported, not applied")

    for name in TB_FIELDS:
        if name not in group:
            continue
        dataset = group[name]
        values = _valid_numeric(dataset)
        units = _decode(dataset.attrs.get("units", ""))
        if values.size:
            print(
                f"  {name}: {values.size}/{dataset.size} valid, "
                f"min/median/max {np.min(values):.2f}/{np.median(values):.2f}/{np.max(values):.2f} {units}"
            )
        else:
            print(f"  {name}: 0/{dataset.size} valid")

    for name in QC_FIELDS:
        if name in group:
            values, counts = np.unique(group[name][...], return_counts=True)
            common = Counter(dict(zip(values.tolist(), counts.tolist()))).most_common(8)
            print(f"  {name} most common raw codes: {common}")

    if "cell_grid_surface_status" in group:
        values, counts = np.unique(group["cell_grid_surface_status"][...], return_counts=True)
        print(
            "  surface status counts (0=land, 1=water, 2=ice shelf):",
            dict(zip(values.tolist(), counts.tolist())),
        )

    for name in ("cell_tb_time_utc_aft", "cell_tb_time_utc_fore"):
        if name in group:
            times = sorted({_decode(x) for x in group[name][...] if _decode(x)})
            if times:
                print(f"  {name}: {times[0]} .. {times[-1]} UTC")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("h5_file", type=Path, help="Path to a SMAP L1C TB .h5 granule")
    parser.add_argument(
        "--hemisphere",
        choices=("north", "south", "both"),
        default="north",
        help="Polar projection group(s) to summarize (default: north)",
    )
    args = parser.parse_args()

    if not args.h5_file.is_file():
        parser.error(f"file not found: {args.h5_file}")

    print(f"file: {args.h5_file.name} ({args.h5_file.stat().st_size:,} bytes)")
    with h5py.File(args.h5_file, "r") as h5:
        groups = ("North_Polar_Projection", "South_Polar_Projection")
        selected = groups if args.hemisphere == "both" else (groups[0] if args.hemisphere == "north" else groups[1],)
        for name in selected:
            if name not in h5:
                raise KeyError(f"missing HDF5 group: {name}")
            print(f"{name}:")
            _profile_group(h5[name])


if __name__ == "__main__":
    main()
