# Complete BMC witness-path measurements

Before: `2db089114bb5137aaf5a94d18af9949066f4bb6c`; after: `9e68e7458e79095ef5ee5267bdb65da41bb41761`. Both checkouts were clean. The same profiling tool and input digests were used; see [before.json](before.json) and [after.json](after.json).

The experiment contains 352 records: for each revision, 80 file-API calls, 80 actual Click CLI calls, and 16 separate cProfile calls. Every timed call ran in a fresh interpreter; five repetitions determine each uninstrumented p50. The three positive slicing models and the traffic model with the largest initial solve regression are all included, with reach and invariant queries and the option both off and on. No local tests or other agent benchmark workers ran concurrently.

`call_ms` covers the complete `build_bmc_output` file API or Click CLI invocation, including model/query loading, solving, witness completion, replay and JSON report serialization. It starts after the helper imports; lazy imports reached inside the public call are included. Interpreter startup and the helper transport are excluded. Raw `process_ms` includes that transport and must not be called bare CLI startup latency. Separate cProfile numbers are diagnostic, affected by instrumentation, and are not mixed into wall-time distributions.

All recorded verdicts match the corpus expectations and every available witness passes ordinary replay. SAT/UNSAT describe solver results, not universal success/failure; `property_satisfied` and `outcome` in the raw data preserve property polarity.

## Complete API and CLI calls

Positive change means slower. These are before/after comparisons of the requested option setting, not comparisons of slicing against default. The off rows are unchanged-path controls. Min/max values show the observed spread of the five calls; this small experiment does not establish a universal speedup or statistical significance. The full six-arm benchmark additionally compares both slicing implementations with the same-round default.

| Case/query | Status | Option enabled | Entry | Before p50 ms | Before range ms | After p50 ms | After range ms | Change |
|---|---|---|---|---|---|---|---|---|
| codex_traffic_emergency_priority/invariant | sat | false | api | 1352.501 | 1332.622–1420.585 | 1340.260 | 1326.763–1350.706 | -0.91% |
| codex_traffic_emergency_priority/invariant | sat | false | cli | 1373.088 | 1360.070–1412.317 | 1336.313 | 1317.373–1418.098 | -2.68% |
| codex_traffic_emergency_priority/invariant | sat | true | api | 1256.443 | 1238.794–1308.779 | 1278.863 | 1217.777–1305.733 | 1.78% |
| codex_traffic_emergency_priority/invariant | sat | true | cli | 1268.700 | 1255.714–1321.459 | 1285.344 | 1229.167–1325.064 | 1.31% |
| codex_traffic_emergency_priority/reach | sat | false | api | 1402.827 | 1371.661–1435.619 | 1354.371 | 1343.027–1361.520 | -3.45% |
| codex_traffic_emergency_priority/reach | sat | false | cli | 1412.381 | 1390.613–1430.134 | 1357.049 | 1329.341–1379.200 | -3.92% |
| codex_traffic_emergency_priority/reach | sat | true | api | 1378.472 | 1344.694–1421.118 | 1359.061 | 1337.735–1370.547 | -1.41% |
| codex_traffic_emergency_priority/reach | sat | true | cli | 1372.583 | 1358.154–1392.808 | 1389.333 | 1371.139–1422.600 | 1.22% |
| conveyor_counters/invariant | unsat | false | api | 339.791 | 337.057–343.001 | 348.006 | 346.827–350.591 | 2.42% |
| conveyor_counters/invariant | unsat | false | cli | 341.615 | 340.083–348.565 | 343.826 | 335.398–348.692 | 0.65% |
| conveyor_counters/invariant | unsat | true | api | 305.289 | 301.938–312.302 | 310.356 | 308.161–312.602 | 1.66% |
| conveyor_counters/invariant | unsat | true | cli | 309.505 | 305.919–335.034 | 315.347 | 308.813–327.548 | 1.89% |
| conveyor_counters/reach | sat | false | api | 379.061 | 378.748–387.521 | 385.398 | 378.124–501.113 | 1.67% |
| conveyor_counters/reach | sat | false | cli | 382.439 | 377.146–401.934 | 385.815 | 382.792–390.215 | 0.88% |
| conveyor_counters/reach | sat | true | api | 358.409 | 355.132–364.703 | 354.650 | 348.826–357.362 | -1.05% |
| conveyor_counters/reach | sat | true | cli | 357.284 | 355.992–367.987 | 357.889 | 352.890–365.474 | 0.17% |
| heater_logging/invariant | unsat | false | api | 271.799 | 269.365–281.338 | 278.968 | 270.466–313.305 | 2.64% |
| heater_logging/invariant | unsat | false | cli | 273.392 | 269.536–278.412 | 269.133 | 267.890–273.894 | -1.56% |
| heater_logging/invariant | unsat | true | api | 229.658 | 229.033–233.253 | 225.462 | 223.585–235.441 | -1.83% |
| heater_logging/invariant | unsat | true | cli | 234.946 | 229.402–242.136 | 234.144 | 223.962–238.792 | -0.34% |
| heater_logging/reach | sat | false | api | 279.131 | 275.824–309.950 | 274.170 | 272.987–280.131 | -1.78% |
| heater_logging/reach | sat | false | cli | 283.359 | 276.949–290.728 | 280.351 | 273.075–282.769 | -1.06% |
| heater_logging/reach | sat | true | api | 243.379 | 241.274–245.982 | 236.733 | 234.114–237.609 | -2.73% |
| heater_logging/reach | sat | true | cli | 250.122 | 244.381–257.068 | 240.189 | 238.357–241.493 | -3.97% |
| telemetry_outputs/invariant | unsat | false | api | 395.854 | 387.783–404.347 | 387.401 | 377.542–391.744 | -2.14% |
| telemetry_outputs/invariant | unsat | false | cli | 388.519 | 384.429–402.407 | 386.185 | 379.081–399.743 | -0.60% |
| telemetry_outputs/invariant | unsat | true | api | 330.913 | 322.434–338.365 | 315.389 | 313.501–320.612 | -4.69% |
| telemetry_outputs/invariant | unsat | true | cli | 324.743 | 318.900–330.324 | 318.029 | 314.965–323.808 | -2.07% |
| telemetry_outputs/reach | sat | false | api | 409.359 | 400.146–421.392 | 400.164 | 395.339–408.438 | -2.25% |
| telemetry_outputs/reach | sat | false | cli | 403.874 | 401.101–409.440 | 405.987 | 403.166–416.283 | 0.52% |
| telemetry_outputs/reach | sat | true | api | 368.560 | 356.022–377.739 | 345.006 | 342.321–348.025 | -6.39% |
| telemetry_outputs/reach | sat | true | cli | 359.987 | 359.050–367.375 | 352.058 | 350.897–360.260 | -2.20% |

## Witness work counts

Counts come from separate cProfile calls through the public file API. Actual sliced SAT paths now decode once and replay twice: one internal completion/validation plus the independent public replay. No public replay is cached. `codex_traffic_emergency_priority/reach` retains every variable and is an unsliced control even with the option requested; it already decoded and replayed once. UNSAT queries without a witness do neither.

| Case/query | Option enabled | Before decodes | Before replays | After decodes | After replays |
|---|---|---|---|---|---|
| codex_traffic_emergency_priority/invariant | false | 1 | 1 | 1 | 1 |
| codex_traffic_emergency_priority/invariant | true | 2 | 3 | 1 | 2 |
| codex_traffic_emergency_priority/reach | false | 1 | 1 | 1 | 1 |
| codex_traffic_emergency_priority/reach | true | 1 | 1 | 1 | 1 |
| conveyor_counters/invariant | false | 0 | 0 | 0 | 0 |
| conveyor_counters/invariant | true | 0 | 0 | 0 | 0 |
| conveyor_counters/reach | false | 1 | 1 | 1 | 1 |
| conveyor_counters/reach | true | 2 | 3 | 1 | 2 |
| heater_logging/invariant | false | 0 | 0 | 0 | 0 |
| heater_logging/invariant | true | 0 | 0 | 0 | 0 |
| heater_logging/reach | false | 1 | 1 | 1 | 1 |
| heater_logging/reach | true | 2 | 3 | 1 | 2 |
| telemetry_outputs/invariant | false | 0 | 0 | 0 | 0 |
| telemetry_outputs/invariant | true | 0 | 0 | 0 | 0 |
| telemetry_outputs/reach | false | 1 | 1 | 1 | 1 |
| telemetry_outputs/reach | true | 2 | 3 | 1 | 2 |

## Disjoint profiling phases

Each row is one instrumented call. The phase columns partition that call; do not add the overlapping inclusive function diagnostics from the JSON. Build includes encoding-time solver probes. Z3 check isolates checks invoked through the solve budget; solve bookkeeping covers the remaining core solve work. Internal decode includes completion and verification. Other includes loading, report formatting/serialization and wrapper work. Default and unsliced paths have no internal completion phase.

| Case/query | Option enabled | Revision | build ms | z3_check ms | solve_bookkeeping ms | internal_decode ms | external_decode ms | external_replay ms | other ms |
|---|---|---|---|---|---|---|---|---|---|
| codex_traffic_emergency_priority/invariant | false | before | 1710.847 | 1.077 | 9.670 | 0.000 | 20.611 | 10.918 | 286.968 |
| codex_traffic_emergency_priority/invariant | false | after | 1756.952 | 1.168 | 9.114 | 0.000 | 20.577 | 10.849 | 292.881 |
| codex_traffic_emergency_priority/invariant | true | before | 1564.740 | 1.031 | 8.087 | 32.175 | 32.283 | 10.640 | 302.027 |
| codex_traffic_emergency_priority/invariant | true | after | 1576.931 | 1.027 | 8.388 | 32.646 | 1.292 | 10.765 | 285.544 |
| codex_traffic_emergency_priority/reach | false | before | 1808.367 | 11.605 | 8.848 | 0.000 | 21.176 | 11.828 | 293.334 |
| codex_traffic_emergency_priority/reach | false | after | 1750.805 | 16.175 | 10.406 | 0.000 | 23.968 | 11.688 | 280.133 |
| codex_traffic_emergency_priority/reach | true | before | 1790.486 | 12.028 | 9.903 | 0.000 | 22.381 | 12.444 | 291.795 |
| codex_traffic_emergency_priority/reach | true | after | 1829.522 | 11.152 | 8.556 | 0.000 | 21.019 | 11.427 | 290.769 |
| conveyor_counters/invariant | false | before | 348.742 | 8.604 | 6.829 | 0.000 | 0.000 | 0.000 | 199.035 |
| conveyor_counters/invariant | false | after | 352.765 | 8.437 | 6.776 | 0.000 | 0.000 | 0.000 | 199.061 |
| conveyor_counters/invariant | true | before | 302.494 | 5.687 | 5.499 | 0.000 | 0.000 | 0.000 | 204.578 |
| conveyor_counters/invariant | true | after | 299.544 | 5.539 | 5.522 | 0.000 | 0.000 | 0.000 | 200.948 |
| conveyor_counters/reach | false | before | 410.097 | 7.382 | 7.313 | 0.000 | 15.740 | 10.547 | 206.085 |
| conveyor_counters/reach | false | after | 393.393 | 7.450 | 7.353 | 0.000 | 16.308 | 11.451 | 203.905 |
| conveyor_counters/reach | true | before | 330.214 | 7.161 | 5.698 | 25.812 | 25.755 | 10.167 | 200.994 |
| conveyor_counters/reach | true | after | 344.027 | 7.198 | 5.840 | 26.831 | 1.532 | 10.231 | 208.042 |
| heater_logging/invariant | false | before | 254.220 | 0.355 | 6.494 | 0.000 | 0.000 | 0.000 | 192.476 |
| heater_logging/invariant | false | after | 240.104 | 0.324 | 6.247 | 0.000 | 0.000 | 0.000 | 195.202 |
| heater_logging/invariant | true | before | 183.720 | 0.567 | 4.835 | 0.000 | 0.000 | 0.000 | 195.611 |
| heater_logging/invariant | true | after | 175.004 | 0.589 | 4.321 | 0.000 | 0.000 | 0.000 | 193.503 |
| heater_logging/reach | false | before | 239.185 | 0.188 | 6.383 | 0.000 | 11.144 | 7.664 | 193.810 |
| heater_logging/reach | false | after | 238.110 | 0.189 | 6.124 | 0.000 | 10.777 | 7.365 | 196.919 |
| heater_logging/reach | true | before | 174.160 | 0.224 | 4.255 | 18.412 | 18.788 | 7.021 | 192.859 |
| heater_logging/reach | true | after | 172.517 | 0.319 | 4.689 | 18.682 | 1.135 | 7.755 | 199.410 |
| telemetry_outputs/invariant | false | before | 445.096 | 0.755 | 11.536 | 0.000 | 0.000 | 0.000 | 203.141 |
| telemetry_outputs/invariant | false | after | 432.198 | 0.610 | 10.538 | 0.000 | 0.000 | 0.000 | 194.255 |
| telemetry_outputs/invariant | true | before | 340.515 | 0.648 | 7.111 | 0.000 | 0.000 | 0.000 | 200.627 |
| telemetry_outputs/invariant | true | after | 335.061 | 0.470 | 6.699 | 0.000 | 0.000 | 0.000 | 191.467 |
| telemetry_outputs/reach | false | before | 441.813 | 0.230 | 10.578 | 0.000 | 18.406 | 16.465 | 205.023 |
| telemetry_outputs/reach | false | after | 443.138 | 0.232 | 10.629 | 0.000 | 18.605 | 16.120 | 199.674 |
| telemetry_outputs/reach | true | before | 352.792 | 0.207 | 7.507 | 35.589 | 35.692 | 15.692 | 200.447 |
| telemetry_outputs/reach | true | after | 355.328 | 0.175 | 6.680 | 36.614 | 1.929 | 16.277 | 207.360 |

## Interpretation and limits

The verified-trace reuse removes one complete decode/completion pass on the default-policy result path. It does not remove the first internal validation, nor does it skip independent output replay. Explicit event policies and raw-model decoding still reconstruct their requested trace. Each reused result is copied so one caller cannot mutate a later caller's witness.

Enabled SAT file-API changes range from a 6.39% reduction on telemetry reach to a 1.78% increase on traffic invariant in this experiment; enabled SAT CLI changes range from a 3.97% reduction on heater reach to a 1.31% increase on traffic invariant. These ranges include the unsliced traffic reach control. Most complete-call cost remains outside repeated witness decoding, so the structural reduction in work must not be described as a comparable percentage reduction in whole-call time. Small changes also appear on the off controls. The [completed six-arm run](../../runs/9e68e7458e79/report.md) finds a 3.78% reduction in full API p50 within the six actually sliced SAT queries against the same-round initial slicing implementation, but only 0.64% across all 51 queries. T3 remains unmet: DAG reduction is 6.09%, and unsliced build + solve grows 6.87%. A [bounded diagnostic rerun](../../runs/9e68e7458e79-unsliced-control/report.md) did not reproduce the larger unsliced regression; it does not replace the formal result. See the [benchmark interpretation](../../../README.md#verified-witness-reuse-measurements) for group definitions, worst regressions and remaining costs.

## Reproduction

Use the same interpreter/dependency environment and this revision's profiling tool against separate clean checkouts, writing to new output paths:

```bash
python tools/profile_bmc_witness.py --checkout /path/to/2db08911 --output /tmp/witness-before.json
python tools/profile_bmc_witness.py --checkout /path/to/9e68e745 --output /tmp/witness-after.json
```

Each p50 above is the median of the five matching `call_ms` records. Changes are `(after_p50 / before_p50 - 1) * 100`; phase timings and work counts are recorded directly in the matching `mode=profile` record. Input and tool SHA-256 digests, exact source commits, Python and Z3 versions, invocation exit codes and verdicts accompany the raw records.
