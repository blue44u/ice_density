# Date-held-out channel baselines against G02202

This is an exploratory cross-product comparison using G02202 Version 6
as a weak target. G02202 is a passive-microwave retrieval, so these
numbers are **not independent retrieval accuracy**. SMAP L1C is used
at its native resolution; grid matching does not downscale it.

Every included date is held out once. A fixed ridge penalty of 0.001
times the number of training samples is applied after training-fold
standardization. Predictions are clipped to 0–100%. No target-date
labels are used for fitting or scaling. The AMSR2 product row is an
existing-product comparison where that product has a valid value;
its sample count can differ from the two fitted models.

Included days: 20160215, 20160315, 20160415, 20160515, 20160615, 20160715, 20160815, 20160915, 20161015, 20161115, 20161215.
Excluded for incomplete daily SMAP coverage: 20160131.
`cdr_usable` retains weather-filtered open-water values but excludes
the invalid-ice mask, land spillover and interpolation flags. Inspect
the original QA field before using this target for training.

## Held-out date results

| Date | Model | N | MAE pp | RMSE pp | Bias pp | Edge N | Edge MAE pp |
|---|---|---:|---:|---:|---:|---:|---:|
| 20160215 | X/Ka | 10,235 | 3.87 | 6.02 | -1.95 | 548 | 10.31 |
| 20160215 | native L/X/Ka | 10,235 | 3.58 | 5.71 | -1.74 | 548 | 9.82 |
| 20160215 | AMSR2 product | 10,064 | 2.37 | 6.46 | +0.15 | 539 | 19.70 |
| 20160315 | X/Ka | 10,380 | 4.00 | 6.03 | -1.48 | 586 | 10.43 |
| 20160315 | native L/X/Ka | 10,380 | 3.79 | 5.80 | -1.38 | 586 | 9.91 |
| 20160315 | AMSR2 product | 10,215 | 2.49 | 6.33 | -0.09 | 571 | 19.51 |
| 20160415 | X/Ka | 7,530 | 2.34 | 4.57 | -0.52 | 495 | 8.58 |
| 20160415 | native L/X/Ka | 7,530 | 2.17 | 4.33 | -0.37 | 495 | 8.12 |
| 20160415 | AMSR2 product | 7,381 | 2.83 | 7.06 | +0.35 | 482 | 19.95 |
| 20160515 | X/Ka | 9,986 | 2.25 | 5.09 | +0.56 | 837 | 9.27 |
| 20160515 | native L/X/Ka | 9,986 | 2.21 | 4.98 | +0.52 | 837 | 8.79 |
| 20160515 | AMSR2 product | 9,836 | 3.83 | 9.20 | +0.54 | 821 | 22.11 |
| 20160615 | X/Ka | 9,245 | 3.78 | 7.39 | +0.12 | 1,669 | 10.14 |
| 20160615 | native L/X/Ka | 9,245 | 3.76 | 7.35 | +0.08 | 1,669 | 10.03 |
| 20160615 | AMSR2 product | 9,116 | 5.78 | 11.93 | +2.36 | 1,617 | 22.65 |
| 20160715 | X/Ka | 9,032 | 9.91 | 13.27 | -5.75 | 1,417 | 15.73 |
| 20160715 | native L/X/Ka | 9,032 | 10.32 | 13.51 | -6.11 | 1,417 | 15.58 |
| 20160715 | AMSR2 product | 8,926 | 5.40 | 12.50 | -1.11 | 1,397 | 19.84 |
| 20160815 | X/Ka | 7,853 | 7.79 | 11.88 | -3.24 | 1,588 | 11.63 |
| 20160815 | native L/X/Ka | 7,853 | 8.43 | 12.51 | -3.89 | 1,588 | 11.89 |
| 20160815 | AMSR2 product | 7,792 | 6.59 | 13.99 | +0.21 | 1,557 | 22.05 |
| 20160915 | X/Ka | 7,341 | 5.66 | 9.11 | -1.39 | 842 | 12.98 |
| 20160915 | native L/X/Ka | 7,341 | 5.76 | 9.20 | -1.48 | 842 | 13.18 |
| 20160915 | AMSR2 product | 7,297 | 3.74 | 9.46 | -0.10 | 833 | 18.15 |
| 20161015 | X/Ka | 8,045 | 3.28 | 6.40 | +1.29 | 540 | 7.71 |
| 20161015 | native L/X/Ka | 8,045 | 3.15 | 6.23 | +1.57 | 540 | 7.20 |
| 20161015 | AMSR2 product | 7,985 | 3.81 | 9.02 | -0.49 | 526 | 18.62 |
| 20161115 | X/Ka | 9,249 | 3.47 | 5.94 | +0.19 | 587 | 10.42 |
| 20161115 | native L/X/Ka | 9,249 | 3.10 | 5.53 | +0.44 | 587 | 9.70 |
| 20161115 | AMSR2 product | 9,131 | 2.94 | 7.58 | -0.36 | 567 | 18.72 |
| 20161215 | X/Ka | 9,837 | 3.61 | 6.38 | -1.41 | 616 | 10.85 |
| 20161215 | native L/X/Ka | 9,837 | 3.22 | 5.92 | -1.03 | 616 | 10.28 |
| 20161215 | AMSR2 product | 9,672 | 2.75 | 6.74 | +0.09 | 610 | 17.22 |

## Pooled held-out observations by G02202 concentration

| Model | Stratum | N | MAE pp | RMSE pp | Bias pp |
|---|---|---:|---:|---:|---:|
| X/Ka | all | 98,733 | 4.48 | 7.82 | -1.24 |
| X/Ka | open water 0% | 30,460 | 3.74 | 6.89 | +3.74 |
| X/Ka | edge 1–79% | 9,725 | 11.24 | 14.07 | -7.92 |
| X/Ka | ice 80–100% | 58,548 | 3.74 | 6.75 | -2.71 |
| native L/X/Ka | all | 98,733 | 4.42 | 7.80 | -1.21 |
| native L/X/Ka | open water 0% | 30,460 | 3.69 | 6.82 | +3.69 |
| native L/X/Ka | edge 1–79% | 9,725 | 11.03 | 13.74 | -7.87 |
| native L/X/Ka | ice 80–100% | 58,548 | 3.70 | 6.87 | -2.65 |
| AMSR2 product | all | 97,415 | 3.81 | 9.35 | +0.15 |
| AMSR2 product | open water 0% | 30,358 | 0.78 | 5.25 | +0.78 |
| AMSR2 product | edge 1–79% | 9,520 | 20.40 | 24.82 | +2.10 |
| AMSR2 product | ice 80–100% | 57,537 | 2.67 | 5.61 | -0.50 |

The sample is one day per month in one year. Neighboring grid
cells share information, so pooled row counts are not independent
replicates. Assess each held-out date and concentration stratum, then
repeat with more dates and independent reference before drawing model
performance conclusions. The three-endmember FYI/MYI model requires
ice-type labels or defensible dynamic tie points that are not supplied
by total-concentration G02202 alone.
