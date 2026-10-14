#!/usr/bin/env python3
"""Export SMAP L1C north-polar cells with transparent Arctic/ocean/QC masks."""

from __future__ import annotations

import argparse
import csv
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
# Bits are numbered from zero as in the NSIDC SPL1CTB User Guide. For an
# aft H/V pair, reject: unacceptable quality, out-of-range TB, uncorrectable
# RFI, unacceptable NEDT, null TB, outside the half orbit, or not declared
# RFI-clean. Correctable RFI detection (bit 2 alone) is retained.
REJECT_MASK = (1 << 0) | (1 << 1) | (1 << 3) | (1 << 4) | (1 << 12) | (1 << 13) | (1 << 15)


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
    return valid


def _text_values(dataset: h5py.Dataset) -> list[str]:
    result = []
    for value in dataset[...]:
        if isinstance(value, bytes):
            result.append(value.decode("utf-8", errors="replace").rstrip("\x00 "))
        else:
            result.append(str(value).rstrip("\x00 "))
    return result


def prepare(input_path: Path, output_path: Path, min_lat: float, hemisphere: str) -> dict[str, int]:
    group_name = {"north": "North_Polar_Projection", "south": "South_Polar_Projection"}[hemisphere]
    with h5py.File(input_path, "r") as source:
        if group_name not in source:
            raise KeyError(f"HDF5 group not found: {group_name}")
        group = source[group_name]

        required = ("cell_lat", "cell_lon", "cell_grid_surface_status", *TB_FIELDS, *QC_FIELDS)
        missing = [name for name in required if name not in group]
        if missing:
            raise KeyError(f"Missing required fields in {group_name}: {', '.join(missing)}")

        lat = group["cell_lat"][...]
        lon = group["cell_lon"][...]
        status = group["cell_grid_surface_status"][...]
        n = len(lat)
        coordinate_ok = np.isfinite(lat) & np.isfinite(lon) & (np.abs(lat) <= 90) & (np.abs(lon) <= 180)
        latitude_ok = lat >= min_lat if hemisphere == "north" else lat <= -min_lat
        water = status == 1

        tb_values = {name: group[name][...] for name in TB_FIELDS}
        tb_valid = {name: _valid_numeric(group[name]) for name in TB_FIELDS}
        aft_tb_ok = tb_valid["cell_tb_v_aft"] & tb_valid["cell_tb_h_aft"]
        flags = {name: group[name][...].astype(np.uint16, copy=False) for name in QC_FIELDS}
        aft_qc_ok = np.ones(n, dtype=bool)
        for name in ("cell_tb_qual_flag_v_aft", "cell_tb_qual_flag_h_aft"):
            fill = int(group[name].attrs.get("_FillValue", 65534))
            aft_qc_ok &= (flags[name] != fill) & ((flags[name] & REJECT_MASK) == 0)

        candidate = coordinate_ok & latitude_ok & water & aft_tb_ok & aft_qc_ok
        counts = {
            "cells": n,
            "valid_coordinates": int(coordinate_ok.sum()),
            "within_latitude": int((coordinate_ok & latitude_ok).sum()),
            "water_in_latitude": int((coordinate_ok & latitude_ok & water).sum()),
            "valid_aft_hv_tb": int((coordinate_ok & latitude_ok & water & aft_tb_ok).sum()),
            "pass_aft_hv_qc": int((coordinate_ok & latitude_ok & water & aft_tb_ok & aft_qc_ok).sum()),
            "analysis_candidates": int(candidate.sum()),
        }

        columns: dict[str, list[object]] = {
            "cell_lat": lat.tolist(),
            "cell_lon": lon.tolist(),
            "surface_status": status.tolist(),
            "coordinate_ok": coordinate_ok.tolist(),
            "latitude_ok": latitude_ok.tolist(),
            "water_mask": water.tolist(),
            "aft_tb_valid": aft_tb_ok.tolist(),
            "aft_hv_qc_ok": aft_qc_ok.tolist(),
            "analysis_candidate": candidate.tolist(),
        }
        for name in ("cell_row", "cell_column"):
            if name in group:
                columns[name] = group[name][...].tolist()
        for name, values in tb_values.items():
            # Represent fill and out-of-range values as empty fields in the CSV.
            columns[name] = [v.item() if ok else "" for v, ok in zip(values, tb_valid[name])]
        for name, values in flags.items():
            columns[name] = values.tolist()
        for name in ("cell_tb_time_utc_aft", "cell_tb_time_utc_fore"):
            if name in group:
                columns[name] = _text_values(group[name])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    names = list(columns)
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(names)
        writer.writerows(zip(*(columns[name] for name in names)))
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("h5_file", type=Path, help="Path to a SMAP L1C .h5 granule")
    parser.add_argument("--output", type=Path, help="CSV output (default: <input-stem>_prepared.csv)")
    parser.add_argument("--hemisphere", choices=("north", "south"), default="north")
    parser.add_argument("--min-lat", type=float, default=60.0, help="Absolute latitude cutoff in degrees (default: 60)")
    args = parser.parse_args()
    if not args.h5_file.is_file():
        parser.error(f"file not found: {args.h5_file}")
    if not 0 <= args.min_lat <= 90:
        parser.error("--min-lat must be between 0 and 90 degrees")
    output = args.output or args.h5_file.with_name(f"{args.h5_file.stem}_prepared.csv")
    counts = prepare(args.h5_file, output, args.min_lat, args.hemisphere)
    print(f"Wrote {output} ({output.stat().st_size:,} bytes)")
    for label, count in counts.items():
        print(f"{label}: {count}")
    print(f"QC: aft H/V flags pass when bits in mask {REJECT_MASK} are all zero")


if __name__ == "__main__":
    main()
