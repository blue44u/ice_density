# ice_density

Research code for passive-microwave sea-ice concentration retrieval, with the
planned L/X/Ka-band inputs and constrained endmember analysis.

## Current sample

The original single-granule example is now stored with the other SMAP inputs:

`data/raw/smap_l1c/SMAP_L1C_TB_05344_D_20160131T232727_R19240_001.h5`

It includes north and south polar projection groups, per-cell latitude,
longitude, EASE-grid row/column, fore/aft H/V brightness temperatures, surface
corrected temperatures, acquisition times, and quality flags. The north group
has 8,389 cells in this granule, of which 3,215 are marked as water. The
brightness-temperature and quality-flag fields have not yet been filtered for
retrieval; the quality flags must be interpreted from the product guide before
use.

The repository also includes the AMSR2 `AU_SI3_04` 25 km daily sea-ice product
for 2016-01-31. Its northern polar grid has 448 rows by 304 columns. Brightness
temperatures are stored as packed integers with a 0.1 K scale factor and a zero
fill value. It contains H/V channels at 6.9, 10.7, 18.7, 23.8, 36.5, and
89.0 GHz, with descending-pass (`DSC`) and daily (`DAY`) composites. This gives
the sample both the 10.7 GHz X-band and 36.5 GHz Ka-band measurements alongside
SMAP L-band observations.

## Profile a granule

With the project Python environment installed from `requirements.lock`, run:

```bash
python scripts/profile_smap_l1c.py \
  data/raw/smap_l1c/SMAP_L1C_TB_05344_D_20160131T232727_R19240_001.h5 \
  --hemisphere north
```

Use `--hemisphere south` or `--hemisphere both` to summarize other projection
groups. The profile reports valid coordinates, brightness-temperature ranges,
raw quality-flag codes, surface classes, and acquisition-time coverage. It does
not apply quality filtering or estimate sea-ice concentration.

## Prepare a SMAP granule

The preparation script exports the North (or South) polar cells to CSV. It
keeps the raw H/V fore/aft brightness temperatures and quality codes, marks
fill/out-of-range temperatures as empty fields, and adds explicit coordinate,
latitude, ocean, and analysis-candidate masks. The default Arctic cutoff is
60°N; change it with `--min-lat` when the study area requires another boundary.

```bash
python scripts/prepare_smap_l1c.py \
  data/raw/smap_l1c/SMAP_L1C_TB_05344_D_20160131T232727_R19240_001.h5 \
  --output data/processed/smap_20160131_prepared.csv
```

The aft H/V quality mask follows the bit definitions in the [NSIDC SPL1CTB
Version 6 User Guide](https://nsidc.org/sites/default/files/documents/user-guide/spl1ctb-v006-userguide.pdf).
It accepts a sample only when bits 0 (unacceptable quality), 1 (out of range),
3 (RFI not correctable), 4 (unacceptable NEDT), 12 (null TB), 13 (outside
half-orbit), and 15 (not declared RFI-clean) are all zero. Bit 2 alone (RFI
detected) is retained when the product still declares the pixel RFI-clean.
This is a conservative analysis mask; raw flags remain in the output so the
policy can be compared or changed later. The product guide also states that
L1C is a gridded half-orbit remapping of L1B and that any set input quality
flag is propagated to the grid-cell average.

For the sample granule, at the default 60°N cutoff, the script found 1,701
water cells with valid aft H/V brightness temperatures and 1,321 that also
pass the quality mask. These counts describe one descending half-orbit, not a
daily or complete Arctic map.

## Collocate the 2016-01-31 SMAP and AMSR2 samples

Prepare the SMAP CSV first, then match its quality-screened Arctic cells to
the nearest AMSR2 25 km grid center:

```bash
python scripts/prepare_smap_l1c.py \
  data/raw/smap_l1c/SMAP_L1C_TB_05344_D_20160131T232727_R19240_001.h5 \
  --output data/processed/smap_20160131_prepared.csv

python scripts/collocate_smap_amsr2.py \
  data/processed/smap_20160131_prepared.csv \
  data/raw/amsr2/AMSR_U2_L3_SeaIce25km_B04_20160131.he5 \
  --output data/processed/smap_amsr2_20160131_collocated.csv
```

The match uses latitude/longitude and great-circle distance between cell
centers; the default acceptance radius is 18 km. The output retains SMAP
coordinates, temperatures, flags, and time, and adds AMSR2 grid indices,
center distance, and scaled H/V brightness temperatures for every available
frequency in the descending-pass and daily composites. On this sample, all
1,321 SMAP candidates match, with median center distance 11.68 km and maximum
17.71 km.

This is a date-matched sample, not an instantaneous overpass match: the SMAP
granule is one descending half-orbit around 23:27 UTC, while the AMSR2 fields
are daily composites. `amsr2_product_sic_dsc_percent` is the AMSR2 product's own
retrieval (0 is open water; 110 and 120 encode missing and land in the source),
so treat it as a comparison field rather than independent truth for training or
validation. The 1,321 matched cells are a small regional sample, not a complete
Arctic dataset.

## Exploratory quality summary

Generate a descriptive QA report from the collocated CSV:

```bash
python scripts/summarize_smap_amsr2.py \
  data/processed/smap_amsr2_20160131_collocated.csv \
  --output data/processed/smap_amsr2_20160131_summary.md
```

For this sample, 1,297 of 1,321 descending-pass AMSR2 concentration values are
valid. They range from 96% to 100%, with a mean of 99.06% and standard
deviation of 0.51 percentage points. SMAP aft-V brightness temperature has
descriptive Pearson correlations of 0.556/0.548 with AMSR2 10.7 GHz H/V, and
-0.025/-0.041 with AMSR2 36.5 GHz H/V. These are exploratory relationships
within one orbit and one date; they do not measure retrieval accuracy or show
that one band causes the observed variation. The narrow AMSR2 concentration
range is not enough to train a reliable concentration retrieval.

## Next processing steps

The repository now includes descending SMAP L1C granules, AMSR2 AU_SI25, and
NOAA/NSIDC G02202 Version 6 for 2016-01-31 and the 15th of each month from
February through December. January contains one SMAP half-orbit; the other
dates contain 14–15 half-orbits each. Build one comparison table per date:

```bash
python scripts/build_daily_collocations.py
```

The script writes `data/processed/daily_collocations/*.csv` and `summary.md`.
It applies the same SMAP aft-H/V quality screen as the single-granule example,
keeps only observations acquired on the selected UTC date, and selects the
nearest SMAP observation for each common AMSR2/G02202 25 km grid cell within
18 km. The AMSR2 and G02202 grid centers agree to within 2 m in this product
pair. SMAP L1C is a coarser observation: joining it to 25 km target cells does
not create a 25 km L-band measurement. The output retains observation time,
source file, quality flags, and center distance.

G02202 concentration is stored as 0–100 integers with a scale factor of 0.01
to fraction. The CSV reports percent. The `cdr_usable` flag excludes missing,
invalid-ice-mask, land-spillover, and interpolated pixels; it retains the
product's weather-filtered values with their QA flags. `cdr_strict` also
excludes weather-filtered values. The latter leaves no open-water observations
on these dates, so it cannot by itself support a water endmember. G02202 is a
separate passive-microwave retrieval, suitable for an exploratory comparison
or weak training target, not independent ground truth.

Compare the first two channel baselines on complete SMAP days:

```bash
python scripts/evaluate_channel_baselines.py
```

The date-held-out report is written to
`data/processed/daily_collocations/channel_baselines.md`. On the 11 complete
days, pooled MAE against G02202 is 4.48 percentage points for X/Ka and 4.42
for native L/X/Ka. The improvement is small and reverses on some summer dates;
these are cross-product agreement scores, not independent accuracy estimates.
See [methodology review](docs/methodology_review.md) for the research decisions.

For the final research claim, obtain a validated
downscaled L-band product and independent ice charts, SAR, optical, or field
reference. One-year and multiyear-ice abundances additionally require ice-type
information; total concentration alone does not identify those endmembers.
