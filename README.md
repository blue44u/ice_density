# ice_density

Research code for passive-microwave sea-ice concentration retrieval, with the
planned L/X/Ka-band inputs and constrained endmember analysis.

## Current sample

The repository contains one SMAP L1C brightness-temperature HDF5 granule:

`SMAP_L1C_TB_05344_D_20160131T232727_R19240_001.h5`

It includes north and south polar projection groups, per-cell latitude,
longitude, EASE-grid row/column, fore/aft H/V brightness temperatures, surface
corrected temperatures, acquisition times, and quality flags. The north group
has 8,389 cells in this granule, of which 3,215 are marked as water. The
brightness-temperature and quality-flag fields have not yet been filtered for
retrieval; the quality flags must be interpreted from the product guide before
use.

## Profile a granule

With the project Python environment installed from `requirements.lock`, run:

```bash
python scripts/profile_smap_l1c.py \
  SMAP_L1C_TB_05344_D_20160131T232727_R19240_001.h5 \
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
  SMAP_L1C_TB_05344_D_20160131T232727_R19240_001.h5 \
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

## Next processing steps

1. Add the selected AMSR2 X/Ka brightness-temperature product and document its
   channels, grid, calibration, and flags.
2. Compare temporal and spatial sampling, then collocate the inputs on a
   documented common grid.
3. Implement and evaluate a single-sensor baseline before the constrained
   multi-band endmember model.
