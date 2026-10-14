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

## Next processing steps

1. Decode SMAP quality flags and make an Arctic ocean/ice analysis mask.
2. Add the selected AMSR2 X/Ka brightness-temperature product and document its
   channels, grid, calibration, and flags.
3. Compare temporal and spatial sampling, then collocate the inputs on a
   documented common grid.
4. Implement and evaluate a single-sensor baseline before the constrained
   multi-band endmember model.
