# Benchmark validation report

Acceptance: |deviation| <= 5 % on every published quantity at every point, with the study equation of state (Peng-Robinson). No parameter is tuned to force agreement. The computed MITA at the published design is a diagnostic only.

## khan2015_n2_single: INCOMPLETE
BENCHMARK_INPUTS_INCOMPLETE. Missing inputs (null in benchmarks.yaml, not substituted):
- `feed_composition`
- `feed_flow_kg_s`
- `product_basis`
- `lng_storage_pressure_bar`
- `T_lng_C`
- `P_high_bar`
- `P_low_bar`
- `n2_flow_kg_s`
- `T_exp_in_C`
- `T_cool_C`
- `compressor_pr_max_per_stage`
- `dp_mshe_hp_bar`
- `dp_mshe_lp_bar`
- `dp_cooler_bar`
- `dp_intercooler_bar`

## khan2015_n2_dual: INCOMPLETE
BENCHMARK_INPUTS_INCOMPLETE. Missing inputs (null in benchmarks.yaml, not substituted):
- `feed_composition`
- `feed_flow_kg_s`
- `product_basis`
- `lng_storage_pressure_bar`
- `T_lng_C`
- `P_high_bar`
- `P_low_bar`
- `n2_flow_kg_s`
- `T_exp_in_warm_C`
- `T_exp_in_cold_C`
- `split`
- `T_cool_C`
- `compressor_pr_max_per_stage`
- `dp_mshe_hp_bar`
- `dp_mshe_lp_bar`
- `dp_cooler_bar`
- `dp_intercooler_bar`

## jensen_skogestad2009_prico: PASS
Source: Jensen, J.B., Skogestad, S., 2009. Single-cycle mixed-fluid LNG process. Part I: Optimal design. 1st Annual Gas Processing Symposium, Doha. Case 1 (Table 2)
- Part I, Table 2 (p. 4), Case 1: feed 52.2 kg/s, LNG 44.6 kg/s, refrigerant 478 kg/s, Tout -144 C, superheat 10 C, dTmin 1.96 C, eta 82.8 %, Ws 77.5 MW, Ph 22 bar, Pl 4.0 bar, refrigerant composition. SRK equation of state stated on p. 2.
- Part II (Jensen and Skogestad 2009, o11.pdf), Fig. 1 and p. 2: feed 30 C and 40 bar, 35 bar after the main exchanger, refrigerant 30 C after the sea-water cooler. These are stated for Case 8 of Part I; their use for Case 1 is an inference.
- Feed composition, pressure drops: NOT in Part I. Taken from Jacobsen and Skogestad (2013), Table 1 ('copied from Jensen and Skogestad [7]', the nominal optimum of a different case) and Perez (2009, NTNU MSc thesis, p. 16: pressure drops, atmospheric flash). Secondary sources; applicability to Case 1 NOT confirmed.
- **Input provenance: secondary_for_feed_composition_and_pressure_drops**

PR (primary): 2 of 2 points within 5 %, mean deviation -0.60 %, mean absolute 0.60 %, maximum absolute 0.66 %, flowsheet failures 0.
SRK with PR kij (cross-check): 2 of 2 points within 5 %, mean deviation -0.24 %, mean absolute 0.56 %, maximum absolute 0.80 %, flowsheet failures 0.

| Point | EOS | Published | Computed | Deviation (%) | Computed MITA (K) | Codes |
|---|---|---|---|---|---|---|
| Compressor power (MW) | PR (primary) | 77.5 | 76.986 | -0.66 | 1.82 | MITA_VIOLATION |
| LNG flow (kg/s) | PR (primary) | 44.6 | 44.363 | -0.53 | 1.82 | MITA_VIOLATION |
| Compressor power (MW) | SRK with PR kij (cross-check) | 77.5 | 77.746 | +0.32 | 1.95 | MITA_VIOLATION |
| LNG flow (kg/s) | SRK with PR kij (cross-check) | 44.6 | 44.243 | -0.80 | 1.95 | MITA_VIOLATION |

Note: the source used SRK. The PR deviation includes the equation-of-state difference; the SRK run reuses the PR binary interaction parameters, so it is a cross-check and not a reproduction of the source's SRK parameters.

## austbo2015_n2_single_PR: FAIL
Source: Austbo, B. (2015) PhD thesis NTNU, Tables 5.1 and 5.4 (Peng-Robinson columns); same content as Austbo and Gundersen (2015), Energy Procedia 64, 63-72 (paper not opened)
- skoge.folk.ntnu.no/publications/thesis/more/Austboe_NTNU_2015/phd-thesis-austboe-revised.pdf, printed p. 111 (Table 5.1 feed) and p. 124 (Table 5.4), PDF pp. 143 and 156. Opened 2026-11-19.

PR (primary): 14 of 15 points within 5 %, mean deviation +1.10 %, mean absolute 1.95 %, maximum absolute 21.95 %, flowsheet failures 0.

| Point | EOS | Published | Computed | Deviation (%) | Computed MITA (K) | Codes |
|---|---|---|---|---|---|---|
| dTmin 1.0 K, eta 0.7 | PR (primary) | 3717.0 | 3712.4 | -0.12 | -0.204 | TEMP_CROSS |
| dTmin 1.0 K, eta 0.8 | PR (primary) | 2604.0 | 2511.3 | -3.56 | -0.197 | TEMP_CROSS |
| dTmin 1.0 K, eta 0.9 | PR (primary) | 1813.0 | 2211 | +21.95 | 5.28 |  |
| dTmin 2.0 K, eta 0.7 | PR (primary) | 3810.0 | 3813.1 | +0.08 | 0.762 | MITA_VIOLATION |
| dTmin 2.0 K, eta 0.8 | PR (primary) | 2714.0 | 2718 | +0.15 | 0.646 | MITA_VIOLATION |
| dTmin 2.0 K, eta 0.9 | PR (primary) | 1849.0 | 1827.2 | -1.18 | -0.661 | TEMP_CROSS |
| dTmin 3.0 K, eta 0.7 | PR (primary) | 3906.0 | 3895 | -0.28 | 1.77 | MITA_VIOLATION |
| dTmin 3.0 K, eta 0.8 | PR (primary) | 2772.0 | 2758.1 | -0.50 | 1.48 | MITA_VIOLATION |
| dTmin 3.0 K, eta 0.9 | PR (primary) | 1882.0 | 1884.7 | +0.14 | 1.48 | MITA_VIOLATION |
| dTmin 4.0 K, eta 0.7 | PR (primary) | 4003.0 | 4009.8 | +0.17 | 2.91 | MITA_VIOLATION |
| dTmin 4.0 K, eta 0.8 | PR (primary) | 2831.0 | 2823.2 | -0.28 | 2.42 | MITA_VIOLATION |
| dTmin 4.0 K, eta 0.9 | PR (primary) | 1915.0 | 1916.6 | +0.08 | 2.22 | MITA_VIOLATION |
| dTmin 5.0 K, eta 0.7 | PR (primary) | 4102.0 | 4111.9 | +0.24 | 3.79 | MITA_VIOLATION |
| dTmin 5.0 K, eta 0.8 | PR (primary) | 2891.0 | 2892.3 | +0.05 | 3.41 | MITA_VIOLATION |
| dTmin 5.0 K, eta 0.9 | PR (primary) | 1948.0 | 1938.8 | -0.47 | 3.12 | MITA_VIOLATION |

## austbo2015_n2_single_SRK: FAIL
Source: Austbo (2015) thesis Table 5.4, SRK columns; run with SRK that reuses the PR kij (labelled cross-check)
- Same document and pages as austbo2015_n2_single_PR.

PR (primary): 12 of 15 points within 5 %, mean deviation +1.50 %, mean absolute 3.85 %, maximum absolute 22.15 %, flowsheet failures 0.
SRK with PR kij (cross-check): 12 of 15 points within 5 %, mean deviation +2.59 %, mean absolute 3.12 %, maximum absolute 22.51 %, flowsheet failures 0.

| Point | EOS | Published | Computed | Deviation (%) | Computed MITA (K) | Codes |
|---|---|---|---|---|---|---|
| dTmin 1.0 K, eta 0.7 | PR (primary) | 3846.0 | 4125.3 | +7.26 | 1.59 |  |
| dTmin 1.0 K, eta 0.7 | SRK with PR kij (cross-check) | 3846.0 | 4131.7 | +7.43 | 1.58 |  |
| dTmin 1.0 K, eta 0.8 | PR (primary) | 2655.0 | 2564.4 | -3.41 | -0.111 | TEMP_CROSS |
| dTmin 1.0 K, eta 0.8 | SRK with PR kij (cross-check) | 2655.0 | 2569.3 | -3.23 | -0.125 | TEMP_CROSS |
| dTmin 1.0 K, eta 0.9 | PR (primary) | 1848.0 | 2257.3 | +22.15 | 5.43 |  |
| dTmin 1.0 K, eta 0.9 | SRK with PR kij (cross-check) | 1848.0 | 2264 | +22.51 | 5.41 |  |
| dTmin 2.0 K, eta 0.7 | PR (primary) | 4026.0 | 3959.5 | -1.65 | 1.26 | MITA_VIOLATION |
| dTmin 2.0 K, eta 0.7 | SRK with PR kij (cross-check) | 4026.0 | 4021.9 | -0.10 | 0.684 | MITA_VIOLATION |
| dTmin 2.0 K, eta 0.8 | PR (primary) | 2797.0 | 3096.6 | +10.71 | 3.72 |  |
| dTmin 2.0 K, eta 0.8 | SRK with PR kij (cross-check) | 2797.0 | 3104.8 | +11.01 | 3.69 |  |
| dTmin 2.0 K, eta 0.9 | PR (primary) | 1904.0 | 1889.1 | -0.78 | 0.886 | MITA_VIOLATION |
| dTmin 2.0 K, eta 0.9 | SRK with PR kij (cross-check) | 1904.0 | 1913.6 | +0.50 | 0.304 | MITA_VIOLATION |
| dTmin 3.0 K, eta 0.7 | PR (primary) | 4128.0 | 4047.9 | -1.94 | 2.31 | MITA_VIOLATION |
| dTmin 3.0 K, eta 0.7 | SRK with PR kij (cross-check) | 4128.0 | 4111.2 | -0.41 | 1.7 | MITA_VIOLATION |
| dTmin 3.0 K, eta 0.8 | PR (primary) | 2890.0 | 2849.8 | -1.39 | 2.14 | MITA_VIOLATION |
| dTmin 3.0 K, eta 0.8 | SRK with PR kij (cross-check) | 2890.0 | 2888.3 | -0.06 | 1.53 | MITA_VIOLATION |
| dTmin 3.0 K, eta 0.9 | PR (primary) | 1938.0 | 1921.8 | -0.84 | 2.09 | MITA_VIOLATION |
| dTmin 3.0 K, eta 0.9 | SRK with PR kij (cross-check) | 1938.0 | 1946.8 | +0.45 | 1.51 | MITA_VIOLATION |
| dTmin 4.0 K, eta 0.7 | PR (primary) | 4232.0 | 4168.8 | -1.49 | 3.4 | MITA_VIOLATION |
| dTmin 4.0 K, eta 0.7 | SRK with PR kij (cross-check) | 4232.0 | 4233.6 | +0.04 | 2.76 | MITA_VIOLATION |
| dTmin 4.0 K, eta 0.8 | PR (primary) | 2952.0 | 2917.7 | -1.16 | 3.06 | MITA_VIOLATION |
| dTmin 4.0 K, eta 0.8 | SRK with PR kij (cross-check) | 2952.0 | 2957 | +0.17 | 2.42 | MITA_VIOLATION |
| dTmin 4.0 K, eta 0.9 | PR (primary) | 1972.0 | 1956.3 | -0.80 | 2.92 | MITA_VIOLATION |
| dTmin 4.0 K, eta 0.9 | SRK with PR kij (cross-check) | 1972.0 | 1981.9 | +0.50 | 2.33 | MITA_VIOLATION |
| dTmin 5.0 K, eta 0.7 | PR (primary) | 4337.0 | 4279.6 | -1.32 | 4.39 | MITA_VIOLATION |
| dTmin 5.0 K, eta 0.7 | SRK with PR kij (cross-check) | 4337.0 | 4345.7 | +0.20 | 3.73 | MITA_VIOLATION |
| dTmin 5.0 K, eta 0.8 | PR (primary) | 3015.0 | 2971.1 | -1.46 | 4.16 | MITA_VIOLATION |
| dTmin 5.0 K, eta 0.8 | SRK with PR kij (cross-check) | 3015.0 | 3011 | -0.13 | 3.51 | MITA_VIOLATION |
| dTmin 5.0 K, eta 0.9 | PR (primary) | 2006.0 | 1979.2 | -1.34 | 3.81 | MITA_VIOLATION |
| dTmin 5.0 K, eta 0.9 | SRK with PR kij (cross-check) | 2006.0 | 2005.2 | -0.04 | 3.21 | MITA_VIOLATION |

Note: the source used SRK. The PR deviation includes the equation-of-state difference; the SRK run reuses the PR binary interaction parameters, so it is a cross-check and not a reproduction of the source's SRK parameters.

## austbo2015_n2_dual_SRK: PASS
Source: Austbo (2015) thesis Table 5.9 (dual nitrogen expander, rigorous HYSYS, SRK) and flowsheet Fig. 5.16 (printed p. 137)
- Same PDF; Table 5.9 printed p. 142 (PDF p. 174); Fig. 5.16 printed p. 137 (PDF p. 169). Feed data as Table 5.1 (p. 111).

PR (primary): 15 of 15 points within 5 %, mean deviation -1.14 %, mean absolute 1.14 %, maximum absolute 1.63 %, flowsheet failures 0.
SRK with PR kij (cross-check): 15 of 15 points within 5 %, mean deviation +0.13 %, mean absolute 0.19 %, maximum absolute 0.45 %, flowsheet failures 0.

| Point | EOS | Published | Computed | Deviation (%) | Computed MITA (K) | Codes |
|---|---|---|---|---|---|---|
| dTmin 1.0 K, eta 0.7 | PR (primary) | 2387.0 | 2348 | -1.63 | 0.399 | MITA_VIOLATION |
| dTmin 1.0 K, eta 0.7 | SRK with PR kij (cross-check) | 2387.0 | 2386.1 | -0.04 | 0.16 | MITA_VIOLATION |
| dTmin 1.0 K, eta 0.8 | PR (primary) | 1643.0 | 1620.9 | -1.35 | 0.241 | MITA_VIOLATION |
| dTmin 1.0 K, eta 0.8 | SRK with PR kij (cross-check) | 1643.0 | 1642.8 | -0.01 | 0.0739 | MITA_VIOLATION |
| dTmin 1.0 K, eta 0.9 | PR (primary) | 1123.0 | 1114.1 | -0.80 | 0.416 | MITA_VIOLATION |
| dTmin 1.0 K, eta 0.9 | SRK with PR kij (cross-check) | 1123.0 | 1125.4 | +0.21 | 0.278 | MITA_VIOLATION |
| dTmin 2.0 K, eta 0.7 | PR (primary) | 2448.0 | 2408.3 | -1.62 | 1.45 | MITA_VIOLATION |
| dTmin 2.0 K, eta 0.7 | SRK with PR kij (cross-check) | 2448.0 | 2446.5 | -0.06 | 1 | MITA_VIOLATION |
| dTmin 2.0 K, eta 0.8 | PR (primary) | 1682.0 | 1660 | -1.31 | 1.26 | MITA_VIOLATION |
| dTmin 2.0 K, eta 0.8 | SRK with PR kij (cross-check) | 1682.0 | 1681.9 | -0.00 | 1.07 | MITA_VIOLATION |
| dTmin 2.0 K, eta 0.9 | PR (primary) | 1148.0 | 1134.2 | -1.21 | 1.26 | MITA_VIOLATION |
| dTmin 2.0 K, eta 0.9 | SRK with PR kij (cross-check) | 1148.0 | 1145.8 | -0.19 | 1.12 | MITA_VIOLATION |
| dTmin 3.0 K, eta 0.7 | PR (primary) | 2512.0 | 2477.4 | -1.38 | 2.58 | MITA_VIOLATION |
| dTmin 3.0 K, eta 0.7 | SRK with PR kij (cross-check) | 2512.0 | 2515.9 | +0.16 | 1.77 | MITA_VIOLATION |
| dTmin 3.0 K, eta 0.8 | PR (primary) | 1723.0 | 1708.3 | -0.85 | 2.3 | MITA_VIOLATION |
| dTmin 3.0 K, eta 0.8 | SRK with PR kij (cross-check) | 1723.0 | 1730.4 | +0.43 | 2.08 | MITA_VIOLATION |
| dTmin 3.0 K, eta 0.9 | PR (primary) | 1173.0 | 1160.4 | -1.08 | 2.32 | MITA_VIOLATION |
| dTmin 3.0 K, eta 0.9 | SRK with PR kij (cross-check) | 1173.0 | 1172.2 | -0.07 | 2.05 | MITA_VIOLATION |
| dTmin 4.0 K, eta 0.7 | PR (primary) | 2577.0 | 2543.5 | -1.30 | 3.5 | MITA_VIOLATION |
| dTmin 4.0 K, eta 0.7 | SRK with PR kij (cross-check) | 2577.0 | 2581.9 | +0.19 | 3.17 | MITA_VIOLATION |
| dTmin 4.0 K, eta 0.8 | PR (primary) | 1764.0 | 1746.4 | -1.00 | 3.24 | MITA_VIOLATION |
| dTmin 4.0 K, eta 0.8 | SRK with PR kij (cross-check) | 1764.0 | 1768.4 | +0.25 | 2.99 | MITA_VIOLATION |
| dTmin 4.0 K, eta 0.9 | PR (primary) | 1199.0 | 1190.9 | -0.68 | 3.22 | MITA_VIOLATION |
| dTmin 4.0 K, eta 0.9 | SRK with PR kij (cross-check) | 1199.0 | 1202.7 | +0.31 | 3.05 | MITA_VIOLATION |
| dTmin 5.0 K, eta 0.7 | PR (primary) | 2646.0 | 2619 | -1.02 | 4.44 | MITA_VIOLATION |
| dTmin 5.0 K, eta 0.7 | SRK with PR kij (cross-check) | 2646.0 | 2657.8 | +0.45 | 4.07 | MITA_VIOLATION |
| dTmin 5.0 K, eta 0.8 | PR (primary) | 1807.0 | 1784 | -1.27 | 4.24 | MITA_VIOLATION |
| dTmin 5.0 K, eta 0.8 | SRK with PR kij (cross-check) | 1807.0 | 1806.1 | -0.05 | 3.94 | MITA_VIOLATION |
| dTmin 5.0 K, eta 0.9 | PR (primary) | 1226.0 | 1219.1 | -0.56 | 4.19 | MITA_VIOLATION |
| dTmin 5.0 K, eta 0.9 | SRK with PR kij (cross-check) | 1226.0 | 1231 | +0.41 | 4.01 | MITA_VIOLATION |

Note: the source used SRK. The PR deviation includes the equation-of-state difference; the SRK run reuses the PR binary interaction parameters, so it is a cross-check and not a reproduction of the source's SRK parameters.
