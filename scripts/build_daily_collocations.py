#!/usr/bin/env python3
"""Build one SMAP/AMSR2/CDR comparison table per selected UTC day.

These tables describe native SMAP L1C observations matched to the common
AMSR2/CDR 25 km grid. They are not downscaled SMAP products or validation truth.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import h5py
import numpy as np
from pyproj import CRS, Transformer
from scipy.spatial import cKDTree

from prepare_smap_l1c import REJECT_MASK, _valid_numeric


GRID = "HDFEOS/GRIDS/NpPolarGrid25km"
RADIUS_KM = 6371.0088
CDR_UNUSABLE_BITS = 4 | 8 | 16 | 32 | 64
CDR_STRICT_EXCLUDE_BITS = 1 | 2 | CDR_UNUSABLE_BITS
CHANNELS = ("10H", "10V", "36H", "36V")
FIELDS = (
    "date", "amsr2_row", "amsr2_column", "amsr2_lat", "amsr2_lon",
    "smap_file", "smap_time_utc_aft", "smap_lat", "smap_lon",
    "smap_center_distance_km", "smap_tb_h_aft_k", "smap_tb_v_aft_k",
    "smap_qc_h_aft", "smap_qc_v_aft", "amsr2_10h_dsc_tb_k",
    "amsr2_10v_dsc_tb_k", "amsr2_36h_dsc_tb_k", "amsr2_36v_dsc_tb_k",
    "amsr2_product_sic_dsc_percent", "cdr_sic_percent", "cdr_sic_qa_flag",
    "cdr_sic_stdev_fraction", "cdr_usable", "cdr_strict", "features_complete",
)


def _unit_sphere(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    lat_radians = np.deg2rad(lat)
    lon_radians = np.deg2rad(lon)
    cos_lat = np.cos(lat_radians)
    return np.column_stack((
        cos_lat * np.cos(lon_radians),
        cos_lat * np.sin(lon_radians),
        np.sin(lat_radians),
    ))


def _smap_candidates(path: Path, date: str, min_lat: float) -> dict[str, np.ndarray]:
    with h5py.File(path) as source:
        group = source["North_Polar_Projection"]
        lat = group["cell_lat"][...]
        lon = group["cell_lon"][...]
        status = group["cell_grid_surface_status"][...]
        h_tb = group["cell_tb_h_aft"]
        v_tb = group["cell_tb_v_aft"]
        h_flag = group["cell_tb_qual_flag_h_aft"]
        v_flag = group["cell_tb_qual_flag_v_aft"]
        h_quality = h_flag[...].astype(np.uint16)
        v_quality = v_flag[...].astype(np.uint16)
        good = (
            np.isfinite(lat) & np.isfinite(lon)
            & (lat >= min_lat) & (lat <= 90)
            & (np.abs(lon) <= 180) & (status == 1)
            & _valid_numeric(h_tb) & _valid_numeric(v_tb)
            & (h_quality != int(h_flag.attrs.get("_FillValue", 65534)))
            & (v_quality != int(v_flag.attrs.get("_FillValue", 65534)))
            & ((h_quality & REJECT_MASK) == 0)
            & ((v_quality & REJECT_MASK) == 0)
        )
        indices = np.flatnonzero(good)
        times = group["cell_tb_time_utc_aft"][indices]
        # A filename's first UTC date can include cells acquired after midnight.
        # Pair only measurements acquired on the CDR/AMSR2 date.
        utc_day = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
        same_day = np.fromiter((_text(value).startswith(utc_day) for value in times), bool)
        indices = indices[same_day]
        return {
            "lat": lat[indices], "lon": lon[indices],
            "h_tb": h_tb[indices], "v_tb": v_tb[indices],
            "h_flag": h_quality[indices], "v_flag": v_quality[indices],
            "time": times[same_day],
            "file": np.full(len(indices), path.name, dtype=object),
        }


def _packed_values(dataset: h5py.Dataset, rows: np.ndarray, cols: np.ndarray) -> np.ndarray:
    # h5py does not support two index arrays as paired point coordinates.
    raw = dataset[...][rows, cols]
    result = raw.astype(float)
    fill = dataset.attrs.get("_FillValue")
    if fill is not None:
        result[raw == fill] = np.nan
    result *= float(dataset.attrs.get("scale_factor", 1.0))
    result += float(dataset.attrs.get("add_offset", 0.0))
    return result


def _text(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").rstrip("\x00 ")
    return str(value).rstrip("\x00 ")


def _cell(value: float) -> float | str:
    return float(value) if np.isfinite(value) else ""


def _verify_common_grid(amsr_grid: h5py.Group, cdr: h5py.File) -> None:
    lat = amsr_grid["lat"][...]
    lon = amsr_grid["lon"][...]
    x = cdr["x"][...]
    y = cdr["y"][...]
    if lat.shape != (len(y), len(x)) or lon.shape != lat.shape:
        raise ValueError("AMSR2 and CDR grids have different dimensions")
    wkt = _text(cdr["crs"].attrs["crs_wkt"])
    project = Transformer.from_crs(4326, CRS.from_wkt(wkt), always_xy=True)
    projected_x, projected_y = project.transform(lon, lat)
    error_m = np.hypot(projected_x - x[None, :], projected_y - y[:, None])
    if not np.all(np.isfinite(error_m)) or float(np.max(error_m)) > 2:
        raise ValueError(f"AMSR2/CDR grid centers differ by up to {np.nanmax(error_m):.1f} m")


def build_date(
    date: str, smap_files: list[Path], amsr_file: Path, cdr_file: Path,
    output: Path, min_lat: float, max_distance_km: float,
) -> dict[str, int | float]:
    parts = [_smap_candidates(path, date, min_lat) for path in smap_files]
    candidates = sum(len(part["lat"]) for part in parts)
    if not candidates:
        raise ValueError(f"No quality-screened Arctic water observations on {date}")
    smap = {name: np.concatenate([part[name] for part in parts]) for name in parts[0]}

    with h5py.File(amsr_file) as amsr, h5py.File(cdr_file) as cdr:
        grid = amsr[GRID]
        _verify_common_grid(grid, cdr)
        grid_lat = grid["lat"][...]
        grid_lon = grid["lon"][...]
        tree = cKDTree(_unit_sphere(grid_lat.ravel(), grid_lon.ravel()))
        chord, flat_index = tree.query(_unit_sphere(smap["lat"], smap["lon"]))
        distance = 2 * RADIUS_KM * np.arcsin(np.clip(chord / 2, 0, 1))
        within = np.flatnonzero(distance <= max_distance_km)
        if not len(within):
            raise ValueError(f"No SMAP cells within {max_distance_km} km on {date}")
        # At most one observation per CDR/AMSR2 target cell per UTC date.
        # Equal distances fall back to source file/order for determinism.
        order = within[np.lexsort((within, distance[within], flat_index[within]))]
        _, first = np.unique(flat_index[order], return_index=True)
        chosen = order[first]
        target = flat_index[chosen]
        rows, cols = np.unravel_index(target, grid_lat.shape)

        fields = grid["Data Fields"]
        tb = {
            channel: _packed_values(fields[f"SI_25km_NH_{channel}_DSC"], rows, cols)
            for channel in CHANNELS
        }
        amsr_sic = fields["SI_25km_NH_ICECON_DSC"][...][rows, cols].astype(float)
        amsr_sic[(amsr_sic < 0) | (amsr_sic > 100)] = np.nan
        cdr_raw = cdr["cdr_seaice_conc"][0][rows, cols].astype(float)
        cdr_valid = (cdr_raw >= 0) & (cdr_raw <= 100)
        cdr_sic = np.where(cdr_valid, cdr_raw, np.nan)
        qa = cdr["cdr_seaice_conc_qa_flag"][0][rows, cols]
        cdr_usable = cdr_valid & ((qa & CDR_UNUSABLE_BITS) == 0)
        cdr_strict = cdr_valid & ((qa & CDR_STRICT_EXCLUDE_BITS) == 0)
        stdev = cdr["cdr_seaice_conc_stdev"][0][rows, cols].astype(float)
        stdev[stdev < 0] = np.nan
        features_complete = np.logical_and.reduce([np.isfinite(v) for v in tb.values()])

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(FIELDS)
        for i, source_index in enumerate(chosen):
            writer.writerow((
                date, int(rows[i]), int(cols[i]), float(grid_lat[rows[i], cols[i]]),
                float(grid_lon[rows[i], cols[i]]), smap["file"][source_index],
                _text(smap["time"][source_index]), float(smap["lat"][source_index]),
                float(smap["lon"][source_index]), float(distance[source_index]),
                float(smap["h_tb"][source_index]), float(smap["v_tb"][source_index]),
                int(smap["h_flag"][source_index]), int(smap["v_flag"][source_index]),
                *(_cell(tb[channel][i]) for channel in CHANNELS),
                _cell(amsr_sic[i]), _cell(cdr_sic[i]), int(qa[i]),
                _cell(stdev[i]), bool(cdr_usable[i]), bool(cdr_strict[i]),
                bool(features_complete[i]),
            ))

    usable = cdr_usable & features_complete
    strict = cdr_strict & features_complete
    return {
        "granules": len(smap_files), "smap_candidates": candidates,
        "within_distance": len(within), "unique_grid_cells": len(chosen),
        "cdr_valid": int(cdr_valid.sum()), "cdr_usable": int(cdr_usable.sum()),
        "cdr_strict": int(cdr_strict.sum()),
        "features_complete": int(features_complete.sum()),
        "usable_complete": int(usable.sum()),
        "usable_open_water": int(np.sum(usable & (cdr_sic == 0))),
        "usable_edge_1_79": int(np.sum(usable & (cdr_sic >= 1) & (cdr_sic < 80))),
        "usable_ice_80_100": int(np.sum(usable & (cdr_sic >= 80))),
        "strict_complete": int(strict.sum()),
        "strict_open_water": int(np.sum(strict & (cdr_sic == 0))),
        "median_distance_km": float(np.median(distance[chosen])),
        "max_distance_km": float(np.max(distance[chosen])),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/daily_collocations"))
    parser.add_argument("--date", action="append", help="UTC YYYYMMDD; repeat to select dates")
    parser.add_argument("--min-lat", type=float, default=60)
    parser.add_argument("--max-distance-km", type=float, default=18)
    args = parser.parse_args()
    if not 0 <= args.min_lat <= 90 or args.max_distance_km <= 0:
        parser.error("Require 0 <= --min-lat <= 90 and --max-distance-km > 0")

    smap_by_date: dict[str, list[Path]] = defaultdict(list)
    for path in sorted((args.raw_root / "smap_l1c").glob("SMAP_L1C_TB_*_D_*.h5")):
        date = path.name.split("_D_", 1)[1][:8]
        smap_by_date[date].append(path)
    dates = args.date or sorted(smap_by_date)
    if not dates:
        parser.error(f"No SMAP L1C descending files under {args.raw_root / 'smap_l1c'}")
    results = {}
    for date in dates:
        if len(date) != 8 or not date.isdigit() or date not in smap_by_date:
            parser.error(f"No descending SMAP files for date {date}")
        amsr = args.raw_root / "amsr2" / f"AMSR_U2_L3_SeaIce25km_B04_{date}.he5"
        cdr = args.raw_root / "reference_sic/g02202_v6_north" / f"sic_psn25_{date}_F17_v06r00.nc"
        for path in (amsr, cdr):
            if not path.is_file():
                parser.error(f"Missing same-date input: {path}")
        output = args.output_dir / f"smap_amsr2_cdr_{date}.csv"
        results[date] = build_date(
            date, smap_by_date[date], amsr, cdr, output,
            args.min_lat, args.max_distance_km,
        )
        print(date, results[date], output)

    summary = args.output_dir / "summary.md"
    lines = [
        "# Daily SMAP–AMSR2–CDR comparison inventory", "",
        "Native SMAP L1C aft H/V observations are quality screened over Arctic water,",
        "matched to the common 25 km AMSR2/CDR grid, and reduced to the closest",
        "SMAP observation per target cell per UTC day. Cells acquired after",
        "midnight on the following UTC date are excluded. This matching does not",
        "increase SMAP's native spatial resolution. AMSR2 descending fields and",
        "G02202 daily concentration are composites, not instantaneous overpasses.", "",
        f"Grid-center match limit: {args.max_distance_km:g} km; latitude: {args.min_lat:g}–90°N.",
        "CDR concentration is stored as integer percent (0–100) with a 0.01",
        "scale factor to fraction. This table reports percent. `cdr_usable`",
        "excludes QA land-spillover, missing, invalid-ice-mask, and",
        "spatial/temporal interpolation bits (4–64), while retaining weather",
        "filters (bits 1–2). `cdr_strict` additionally excludes weather",
        "filters. Melt-start (bit 128) and original QA codes are retained.", "",
        f"| UTC day | SMAP granules | Screened cells | Within {args.max_distance_km:g} km | Unique grid cells | Valid CDR | Usable with X/Ka | Open water | Edge 1–79% | Ice 80–100% | Strict with X/Ka | Strict open water | Median km |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for date, stats in results.items():
        lines.append(
            f"| {date} | {stats['granules']} | {stats['smap_candidates']} | "
            f"{stats['within_distance']} | {stats['unique_grid_cells']} | "
            f"{stats['cdr_valid']} | {stats['usable_complete']} | "
            f"{stats['usable_open_water']} | {stats['usable_edge_1_79']} | "
            f"{stats['usable_ice_80_100']} | {stats['strict_complete']} | "
            f"{stats['strict_open_water']} | "
            f"{stats['median_distance_km']:.2f} |"
        )
    lines += [
        "", "The G02202 field is a separate passive-microwave retrieval and is",
        "suitable here for a cross-product baseline. It is not independent",
        "ground truth for final model accuracy claims or for one-year/multiyear",
        "ice-type abundances. Obtain independent ice charts/SAR/field reference",
        "and a validated downscaled SMAP L-band product for the final study.", "",
    ]
    summary.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {summary}")


if __name__ == "__main__":
    main()
