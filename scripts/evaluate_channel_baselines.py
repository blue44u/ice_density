#!/usr/bin/env python3
"""Compare X/Ka and native-L/X/Ka ridge baselines against G02202 weak labels.

Each complete UTC day is held out once. Scores describe cross-product
agreement, not independent sea-ice-concentration retrieval accuracy.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import numpy as np


FEATURES = (
    "amsr2_10h_dsc_tb_k", "amsr2_10v_dsc_tb_k",
    "amsr2_36h_dsc_tb_k", "amsr2_36v_dsc_tb_k",
    "smap_tb_h_aft_k", "smap_tb_v_aft_k",
)
MODELS = {"X/Ka": slice(0, 4), "native L/X/Ka": slice(0, 6)}


def _read_day(path: Path) -> dict[str, object]:
    features: list[list[float]] = []
    target: list[float] = []
    product: list[float] = []
    granules: set[str] = set()
    total = 0
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            total += 1
            granules.add(row["smap_file"])
            if row["cdr_usable"] != "True" or row["features_complete"] != "True":
                continue
            values = [float(row[name]) for name in FEATURES]
            label = float(row["cdr_sic_percent"])
            features.append(values)
            target.append(label)
            product.append(float(row["amsr2_product_sic_dsc_percent"]) if row["amsr2_product_sic_dsc_percent"] else math.nan)
    return {
        "date": path.stem.rsplit("_", 1)[-1], "granules": len(granules),
        "total": total, "x": np.asarray(features, dtype=float).reshape(-1, 6),
        "y": np.asarray(target, dtype=float), "product": np.asarray(product, dtype=float),
    }


def _ridge_predict(train_x: np.ndarray, train_y: np.ndarray, test_x: np.ndarray) -> np.ndarray:
    center = train_x.mean(axis=0)
    scale = train_x.std(axis=0)
    scale[scale == 0] = 1
    x = (train_x - center) / scale
    test = (test_x - center) / scale
    y_center = train_y.mean()
    # Fixed weak regularization after training-fold standardization; no test
    # dates are used to select coefficients, centering, or scale.
    penalty = len(train_x) * 0.001
    coef = np.linalg.solve(x.T @ x + penalty * np.eye(x.shape[1]), x.T @ (train_y - y_center))
    return np.clip(test @ coef + y_center, 0, 100)


def _metrics(observed: np.ndarray, predicted: np.ndarray) -> tuple[int, float, float, float]:
    valid = np.isfinite(predicted)
    error = predicted[valid] - observed[valid]
    if not len(error):
        return 0, math.nan, math.nan, math.nan
    return len(error), float(np.mean(np.abs(error))), float(np.sqrt(np.mean(error**2))), float(np.mean(error))


def _render(numbers: tuple[int, float, float, float]) -> str:
    n, mae, rmse, bias = numbers
    if not n:
        return "0 | — | — | —"
    return f"{n:,} | {mae:.2f} | {rmse:.2f} | {bias:+.2f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("data/processed/daily_collocations"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/daily_collocations/channel_baselines.md"))
    parser.add_argument("--min-granules", type=int, default=10, help="Exclude partial daily SMAP coverage (default: 10)")
    args = parser.parse_args()
    days = [_read_day(path) for path in sorted(args.input_dir.glob("smap_amsr2_cdr_*.csv"))]
    included = [day for day in days if day["granules"] >= args.min_granules and len(day["y"]) > 0]
    included_dates = {str(day["date"]) for day in included}
    excluded = [str(day["date"]) for day in days if str(day["date"]) not in included_dates]
    if len(included) < 3:
        parser.error("Need at least three complete dates with usable labels")

    lines = [
        "# Date-held-out channel baselines against G02202", "",
        "This is an exploratory cross-product comparison using G02202 Version 6",
        "as a weak target. G02202 is a passive-microwave retrieval, so these",
        "numbers are **not independent retrieval accuracy**. SMAP L1C is used",
        "at its native resolution; grid matching does not downscale it.", "",
        "Every included date is held out once. A fixed ridge penalty of 0.001",
        "times the number of training samples is applied after training-fold",
        "standardization. Predictions are clipped to 0–100%. No target-date",
        "labels are used for fitting or scaling. The AMSR2 product row is an",
        "existing-product comparison where that product has a valid value;",
        "its sample count can differ from the two fitted models.", "",
        f"Included days: {', '.join(str(day['date']) for day in included)}.",
        f"Excluded for incomplete daily SMAP coverage: {', '.join(excluded) if excluded else 'none'}.",
        "`cdr_usable` retains weather-filtered open-water values but excludes",
        "the invalid-ice mask, land spillover and interpolation flags. Inspect",
        "the original QA field before using this target for training.", "",
        "## Held-out date results", "",
        "| Date | Model | N | MAE pp | RMSE pp | Bias pp | Edge N | Edge MAE pp |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    pooled: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {name: [] for name in (*MODELS, "AMSR2 product")}
    for held in included:
        train_x = np.concatenate([day["x"] for day in included if day is not held])
        train_y = np.concatenate([day["y"] for day in included if day is not held])
        test_x = held["x"]
        test_y = held["y"]
        edge = (test_y > 0) & (test_y < 80)
        predictions = {
            name: _ridge_predict(train_x[:, columns], train_y, test_x[:, columns])
            for name, columns in MODELS.items()
        }
        predictions["AMSR2 product"] = held["product"]
        for name, predicted in predictions.items():
            pooled[name].append((test_y, predicted))
            n, mae, rmse, bias = _metrics(test_y, predicted)
            edge_n, edge_mae, _, _ = _metrics(test_y[edge], predicted[edge])
            edge_display = f"{edge_mae:.2f}" if edge_n else "—"
            lines.append(
                f"| {held['date']} | {name} | {n:,} | {mae:.2f} | {rmse:.2f} | "
                f"{bias:+.2f} | {edge_n:,} | {edge_display} |"
            )

    lines += [
        "", "## Pooled held-out observations by G02202 concentration", "",
        "| Model | Stratum | N | MAE pp | RMSE pp | Bias pp |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for name, pairs in pooled.items():
        observed = np.concatenate([pair[0] for pair in pairs])
        predicted = np.concatenate([pair[1] for pair in pairs])
        strata = (
            ("all", np.ones(len(observed), dtype=bool)),
            ("open water 0%", observed == 0),
            ("edge 1–79%", (observed > 0) & (observed < 80)),
            ("ice 80–100%", observed >= 80),
        )
        for label, mask in strata:
            lines.append(f"| {name} | {label} | {_render(_metrics(observed[mask], predicted[mask]))} |")
    lines += [
        "", "The sample is one day per month in one year. Neighboring grid",
        "cells share information, so pooled row counts are not independent",
        "replicates. Assess each held-out date and concentration stratum, then",
        "repeat with more dates and independent reference before drawing model",
        "performance conclusions. The three-endmember FYI/MYI model requires",
        "ice-type labels or defensible dynamic tie points that are not supplied",
        "by total-concentration G02202 alone.", "",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.output}")
    for name, pairs in pooled.items():
        observed = np.concatenate([pair[0] for pair in pairs])
        predicted = np.concatenate([pair[1] for pair in pairs])
        print(name, "all", _metrics(observed, predicted))
        edge = (observed > 0) & (observed < 80)
        print(name, "edge", _metrics(observed[edge], predicted[edge]))


if __name__ == "__main__":
    main()
