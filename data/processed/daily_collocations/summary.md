# Daily SMAP–AMSR2–CDR comparison inventory

Native SMAP L1C aft H/V observations are quality screened over Arctic water,
matched to the common 25 km AMSR2/CDR grid, and reduced to the closest
SMAP observation per target cell per UTC day. Cells acquired after
midnight on the following UTC date are excluded. This matching does not
increase SMAP's native spatial resolution. AMSR2 descending fields and
G02202 daily concentration are composites, not instantaneous overpasses.

Grid-center match limit: 18 km; latitude: 60–90°N.
CDR concentration is stored as integer percent (0–100) with a 0.01
scale factor to fraction. This table reports percent. `cdr_usable`
excludes QA land-spillover, missing, invalid-ice-mask, and
spatial/temporal interpolation bits (4–64), while retaining weather
filters (bits 1–2). `cdr_strict` additionally excludes weather
filters. Melt-start (bit 128) and original QA codes are retained.

| UTC day | SMAP granules | Screened cells | Within 18 km | Unique grid cells | Valid CDR | Usable with X/Ka | Open water | Edge 1–79% | Ice 80–100% | Strict with X/Ka | Strict open water | Median km |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 20160131 | 1 | 1321 | 1321 | 1321 | 1297 | 1297 | 0 | 0 | 1297 | 1297 | 0 | 11.68 |
| 20160215 | 14 | 21906 | 21906 | 12763 | 12065 | 10235 | 1629 | 548 | 8058 | 8606 | 0 | 11.53 |
| 20160315 | 14 | 21850 | 21850 | 12805 | 12120 | 10380 | 1689 | 586 | 8105 | 8691 | 0 | 11.50 |
| 20160415 | 15 | 23195 | 23195 | 12883 | 12227 | 7530 | 1544 | 495 | 5491 | 5986 | 0 | 11.50 |
| 20160515 | 14 | 20952 | 20952 | 12676 | 12042 | 9986 | 2121 | 837 | 7028 | 7865 | 0 | 11.51 |
| 20160615 | 15 | 20868 | 20868 | 12294 | 11749 | 9245 | 2419 | 1669 | 5157 | 6826 | 0 | 11.54 |
| 20160715 | 15 | 21619 | 21619 | 12632 | 11999 | 9032 | 3534 | 1417 | 4081 | 5498 | 0 | 11.52 |
| 20160815 | 15 | 21120 | 21120 | 12162 | 11478 | 7853 | 4000 | 1588 | 2265 | 3853 | 0 | 11.58 |
| 20160915 | 14 | 20893 | 20893 | 12767 | 12084 | 7341 | 4422 | 842 | 2077 | 2919 | 0 | 11.49 |
| 20161015 | 15 | 22970 | 22970 | 12859 | 12157 | 8045 | 4015 | 540 | 3490 | 4030 | 0 | 11.53 |
| 20161115 | 14 | 21997 | 21997 | 12885 | 12205 | 9249 | 3039 | 587 | 5623 | 6210 | 0 | 11.50 |
| 20161215 | 14 | 21955 | 21955 | 12748 | 12070 | 9837 | 2048 | 616 | 7173 | 7789 | 0 | 11.54 |

The G02202 field is a separate passive-microwave retrieval and is
suitable here for a cross-product baseline. It is not independent
ground truth for final model accuracy claims or for one-year/multiyear
ice-type abundances. Obtain independent ice charts/SAR/field reference
and a validated downscaled SMAP L-band product for the final study.
