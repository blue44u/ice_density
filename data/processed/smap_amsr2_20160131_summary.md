# SMAP-AMSR2 collocation: exploratory QA

Input: `data/processed/smap_amsr2_20160131_collocated.csv`

## Sample and spatial match

- SMAP quality-screened candidate rows: 1,321
- AMSR2 matches within the configured radius: 1,321
- Latitude span: 62.58°N to 86.61°N
- SMAP-to-AMSR2 center distance: median 11.68 km; 95th percentile 15.44 km; maximum 17.70 km

## Brightness-temperature coverage

All temperatures are in kelvin. Missing percentage is measured against the collocated candidate rows.

| Channel | Valid | Missing | Mean | Std. dev. | P05 | Median | P95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| amsr2_06H_dsc_tb_k | 1321 | 0.00% | 232.294 | 3.924 | 225.400 | 232.200 | 238.800 |
| amsr2_06V_dsc_tb_k | 1321 | 0.00% | 252.894 | 2.594 | 248.400 | 253.000 | 256.700 |
| amsr2_10H_dsc_tb_k | 1321 | 0.00% | 235.308 | 3.796 | 229.000 | 235.100 | 241.700 |
| amsr2_10V_dsc_tb_k | 1321 | 0.00% | 254.427 | 2.548 | 250.100 | 254.600 | 258.300 |
| amsr2_18H_dsc_tb_k | 1321 | 0.00% | 235.292 | 3.833 | 229.400 | 235.300 | 241.300 |
| amsr2_18V_dsc_tb_k | 1321 | 0.00% | 253.488 | 2.581 | 249.400 | 253.700 | 257.300 |
| amsr2_23H_dsc_tb_k | 1321 | 0.00% | 235.905 | 4.119 | 229.400 | 236.000 | 242.500 |
| amsr2_23V_dsc_tb_k | 1321 | 0.00% | 251.889 | 3.085 | 246.600 | 252.300 | 256.200 |
| amsr2_36H_dsc_tb_k | 1321 | 0.00% | 230.485 | 5.698 | 221.000 | 231.000 | 237.900 |
| amsr2_36V_dsc_tb_k | 1321 | 0.00% | 244.488 | 5.477 | 235.000 | 245.500 | 250.900 |
| amsr2_89H_dsc_tb_k | 1321 | 0.00% | 208.113 | 9.746 | 192.200 | 207.700 | 225.000 |
| amsr2_89V_dsc_tb_k | 1321 | 0.00% | 218.853 | 9.799 | 202.800 | 218.800 | 235.400 |

## AMSR2 product concentration field

- Valid descending-pass product values: 1,297 / 1,321
- Range: 96.0%–100.0%; mean 99.06%; standard deviation 0.51 percentage points.
- The source product codes 0 as open water, 110 as missing/not calculated, and 120 as land. The collocation CSV leaves 110 and 120 blank.

## Descriptive cross-sensor correlations

Pearson r uses valid row pairs. SMAP aft H/V brightness temperatures are compared with descending-pass AMSR2 10.7 GHz and 36.5 GHz H/V channels.

| SMAP channel | AMSR2 channel | Pairs | Pearson r |
|---|---|---:|---:|
| cell_tb_v_aft | amsr2_10H_dsc_tb_k | 1,321 | 0.556 |
| cell_tb_v_aft | amsr2_10V_dsc_tb_k | 1,321 | 0.548 |
| cell_tb_v_aft | amsr2_36H_dsc_tb_k | 1,321 | -0.025 |
| cell_tb_v_aft | amsr2_36V_dsc_tb_k | 1,321 | -0.041 |
| cell_tb_h_aft | amsr2_10H_dsc_tb_k | 1,321 | 0.282 |
| cell_tb_h_aft | amsr2_10V_dsc_tb_k | 1,321 | 0.192 |
| cell_tb_h_aft | amsr2_36H_dsc_tb_k | 1,321 | 0.013 |
| cell_tb_h_aft | amsr2_36V_dsc_tb_k | 1,321 | -0.014 |

## Interpretation and limits

This is a single-date, one-half-orbit exploratory sample. Spatial nearest-neighbor coverage is good for this sample, but the AMSR2 data are daily composites and are not instantaneous matches to the SMAP measurements. The AMSR2 concentration field is an existing sensor-product retrieval, not independent validation truth. Its narrow value range on this date also provides little target variation for training. These summaries do not estimate retrieval accuracy or establish physical causation between channels.
