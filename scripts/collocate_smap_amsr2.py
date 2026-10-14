#!/usr/bin/env python3
"""Match quality-screened SMAP cells to nearest AMSR2 25 km grid cells."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import h5py
import numpy as np
from scipy.spatial import cKDTree


AMSR_GRID = "HDFEOS/GRIDS/NpPolarGrid25km"
AMSR_DATA_FIELDS = f"{AMSR_GRID}/Data Fields"
FREQUENCIES = ("06", "10", "18", "23", "36", "89")
POLARIZATIONS = ("H", "V")
PASSES = ("DSC", "DAY")
EARTH_RADIUS_KM = 6371.0088


def _unit_sphere(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    lat_radians = np.deg2rad(lat)
    lon_radians = np.deg2rad(lon)
    cos_lat = np.cos(lat_radians)
    return np.column_stack((cos_lat * np.cos(lon_radians), cos_lat * np.sin(lon_radians), np.sin(lat_radians)))


def _distance_km(chord_distance: np.ndarray) -> np.ndarray:
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.clip(chord_distance / 2, 0, 1))


def _read_smap_candidates(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        rows = [row for row in csv.DictReader(stream) if row.get("analysis_candidate", "").lower() == "true"]
    if not rows:
        raise ValueError(f"No analysis candidates found in {path}")
    return rows


def _unpack(dataset: h5py.Dataset, flat_indices: np.ndarray) -> list[float | str]:
    raw = dataset[...].reshape(-1)[flat_indices]
    fill = dataset.attrs.get("_FillValue")
    scale = float(dataset.attrs.get("scale_factor", 1.0))
    offset = float(dataset.attrs.get("add_offset", 0.0))
    result: list[float | str] = []
    for value in raw:
        if (fill is not None and value == fill) or not np.isfinite(value):
            result.append("")
        else:
            result.append(float(value) * scale + offset)
    return result


def collocate(
    smap_csv: Path,
    amsr2_file: Path,
    output_csv: Path,
    max_distance_km: float,
) -> dict[str, float | int]:
    smap_rows = _read_smap_candidates(smap_csv)
    smap_lat = np.asarray([float(row["cell_lat"]) for row in smap_rows])
    smap_lon = np.asarray([float(row["cell_lon"]) for row in smap_rows])

    with h5py.File(amsr2_file, "r") as source:
        grid = source[AMSR_GRID]
        fields = source[AMSR_DATA_FIELDS]
        grid_lat = grid["lat"][...]
        grid_lon = grid["lon"][...]
        nrows, ncols = grid_lat.shape
        valid_grid = (
            np.isfinite(grid_lat.ravel())
            & np.isfinite(grid_lon.ravel())
            & (np.abs(grid_lat.ravel()) <= 90)
            & (np.abs(grid_lon.ravel()) <= 180)
        )
        valid_flat_indices = np.flatnonzero(valid_grid)
        flat_lat = grid_lat.ravel()[valid_grid]
        flat_lon = grid_lon.ravel()[valid_grid]
        tree = cKDTree(_unit_sphere(flat_lat, flat_lon))
        chord, nearest_valid = tree.query(_unit_sphere(smap_lat, smap_lon), k=1)
        distances = _distance_km(chord)
        nearest_flat = valid_flat_indices[nearest_valid]
        nearest_rows = nearest_flat // ncols
        nearest_cols = nearest_flat % ncols
        nearest_lat = grid_lat.ravel()[nearest_flat]
        nearest_lon = grid_lon.ravel()[nearest_flat]
        matched = distances <= max_distance_km

        output_fields: list[tuple[str, list[float | str]]] = [
            ("amsr2_grid_row", nearest_rows.tolist()),
            ("amsr2_grid_column", nearest_cols.tolist()),
            ("amsr2_lat", nearest_lat.tolist()),
            ("amsr2_lon", nearest_lon.tolist()),
            ("amsr2_center_distance_km", distances.tolist()),
            ("amsr2_within_distance", matched.tolist()),
        ]

        for frequency in FREQUENCIES:
            for polarization in POLARIZATIONS:
                for overpass in PASSES:
                    name = f"SI_25km_NH_{frequency}{polarization}_{overpass}"
                    if name in fields:
                        output_fields.append((f"amsr2_{frequency}{polarization}_{overpass.lower()}_tb_k", _unpack(fields[name], nearest_flat)))

        # This is the product's own sea-ice-concentration retrieval, included
        # only as a comparison field, not as independent training truth.
        sic_name = "SI_25km_NH_ICECON_DSC"
        if sic_name in fields:
            raw_sic = fields[sic_name][...].reshape(-1)[nearest_flat]
            sic_values: list[float | str] = []
            for value in raw_sic:
                sic_values.append(float(value) if 0 <= value <= 100 else "")
            output_fields.append(("amsr2_product_sic_dsc_percent", sic_values))

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    original_fields = list(smap_rows[0])
    all_fields = original_fields + [name for name, _ in output_fields]
    with output_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=all_fields)
        writer.writeheader()
        for i, smap_row in enumerate(smap_rows):
            result = dict(smap_row)
            for name, values in output_fields:
                value = values[i]
                if not matched[i] and name.startswith("amsr2_") and name not in {
                    "amsr2_grid_row", "amsr2_grid_column", "amsr2_lat", "amsr2_lon",
                    "amsr2_center_distance_km", "amsr2_within_distance",
                }:
                    value = ""
                result[name] = value
            writer.writerow(result)

    return {
        "smap_candidates": len(smap_rows),
        "within_distance": int(matched.sum()),
        "median_center_distance_km": float(np.median(distances)),
        "max_center_distance_km": float(np.max(distances)),
        "output_bytes": output_csv.stat().st_size,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("smap_csv", type=Path, help="Output CSV from prepare_smap_l1c.py")
    parser.add_argument("amsr2_file", type=Path, help="AMSR2 AU_SI3_04 25 km daily .he5 file")
    parser.add_argument("--output", type=Path, default=Path("data/processed/smap_amsr2_20160131_collocated.csv"))
    parser.add_argument(
        "--max-distance-km",
        type=float,
        default=18.0,
        help="Maximum SMAP-to-AMSR2 grid-center distance for a match (default: 18 km)",
    )
    args = parser.parse_args()
    if not args.smap_csv.is_file():
        parser.error(f"SMAP CSV not found: {args.smap_csv}")
    if not args.amsr2_file.is_file():
        parser.error(f"AMSR2 file not found: {args.amsr2_file}")
    if args.max_distance_km <= 0:
        parser.error("--max-distance-km must be positive")
    counts = collocate(args.smap_csv, args.amsr2_file, args.output, args.max_distance_km)
    print(f"Wrote {args.output} ({counts['output_bytes']:,} bytes)")
    for label, value in counts.items():
        if label != "output_bytes":
            print(f"{label}: {value}")


if __name__ == "__main__":
    main()
