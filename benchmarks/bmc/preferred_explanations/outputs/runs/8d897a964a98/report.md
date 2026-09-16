# Preferred explanation measurements

Synthetic fixtures only; no claim about a production model distribution. API excludes imports; CLI includes startup. RSS is whole-process peak. Timed samples have no check observer. Reported explanation time is the existing production metric, not a hard wall-clock bound or a complete accounting of late narrative/proof work. API samples also retain full solve_ms in raw data. A 5 ms budget can overrun during Python setup; inspect raw status and elapsed time rather than claiming hard realtime behavior.

| Case | Surface | Arm | Time median [min, max] ms | RSS median KiB | Reported explanation median ms |
|---|---|---|---:|---:|---:|
| multiple_short | api | baseline_default | 48.828 [48.520, 49.689] | 88744 | 11.706 |
| multiple_short | api | current_default | 48.832 [48.409, 52.237] | 88848 | 11.612 |
| multiple_short | api | current_preferred | 62.795 [62.322, 63.355] | 88920 | 25.486 |
| multiple_short | cli | baseline_default | 938.639 [935.539, 947.341] | 113904 | 11.863 |
| multiple_short | cli | current_default | 939.610 [935.096, 941.825] | 114084 | 11.716 |
| multiple_short | cli | current_preferred | 957.213 [950.081, 960.263] | 113980 | 25.429 |
| multiple_long | api | baseline_default | 613.436 [604.923, 630.007] | 95688 | 250.624 |
| multiple_long | api | current_default | 606.446 [602.859, 613.711] | 95644 | 245.754 |
| multiple_long | api | current_preferred | 1787.071 [1774.738, 1825.793] | 95904 | 1424.614 |
| multiple_long | cli | baseline_default | 1521.553 [1520.064, 1536.153] | 121536 | 244.360 |
| multiple_long | cli | current_default | 1532.164 [1515.081, 1545.074] | 121324 | 248.937 |
| multiple_long | cli | current_preferred | 2717.793 [2715.532, 2729.786] | 121268 | 1435.430 |
| single_conflict | api | baseline_default | 197.737 [196.683, 198.968] | 89992 | 71.078 |
| single_conflict | api | current_default | 196.049 [194.929, 199.195] | 89756 | 68.393 |
| single_conflict | api | current_preferred | 230.851 [227.314, 234.361] | 89964 | 102.833 |
| single_conflict | cli | baseline_default | 1092.694 [1080.232, 1105.605] | 114736 | 68.867 |
| single_conflict | cli | current_default | 1094.155 [1087.374, 1098.252] | 114808 | 69.171 |
| single_conflict | cli | current_preferred | 1126.361 [1121.978, 1144.701] | 114892 | 101.206 |
| feasible | api | baseline_default | 117.727 [116.543, 119.262] | 85672 | 0.000 |
| feasible | api | current_default | 116.702 [114.498, 118.069] | 85928 | 0.000 |
| feasible | api | current_preferred | 118.079 [115.261, 119.678] | 85928 | 0.000 |
| feasible | cli | baseline_default | 1019.517 [1012.103, 1035.193] | 111428 | 0.000 |
| feasible | cli | current_default | 1021.508 [1016.127, 1038.170] | 111644 | 0.000 |
| feasible | cli | current_preferred | 1020.356 [1016.474, 1025.197] | 111324 | 0.000 |
| budget_limited | api | baseline_default | 605.985 [603.379, 613.389] | 95380 | 245.263 |
| budget_limited | api | current_default | 604.034 [598.444, 610.421] | 95436 | 245.873 |
| budget_limited | api | current_preferred | 466.002 [463.294, 472.765] | 92344 | 109.681 |
| budget_limited | cli | baseline_default | 1531.219 [1524.875, 1543.782] | 121796 | 245.455 |
| budget_limited | cli | current_default | 1522.497 [1520.923, 1535.615] | 121896 | 244.780 |
| budget_limited | cli | current_preferred | 1385.900 [1378.627, 1391.853] | 117392 | 108.479 |

Separate untimed check-count / quality observations:

| Case | Arm | Checks | Core member IDs | Minimality | Preference status |
|---|---|---:|---|---|---|
| multiple_short | baseline_default | 13 | assumption.0000.frame.0000, initial.variable.y | proven | off |
| multiple_short | current_default | 13 | assumption.0000.frame.0000, initial.variable.y | proven | off |
| multiple_short | current_preferred | 23 | assumption.0000.frame.0000, initial.where | proven | complete |
| multiple_long | baseline_default | 13 | assumption.0000.frame.0000, initial.variable.y | proven | off |
| multiple_long | current_default | 13 | assumption.0000.frame.0000, initial.variable.y | proven | off |
| multiple_long | current_preferred | 219 | assumption.0000.frame.0000, initial.where | proven | complete |
| single_conflict | baseline_default | 10 | assumption.0000.frame.0000, assumption.0001.frame.0000 | proven | off |
| single_conflict | current_default | 10 | assumption.0000.frame.0000, assumption.0001.frame.0000 | proven | off |
| single_conflict | current_preferred | 11 | assumption.0000.frame.0000, assumption.0001.frame.0000 | proven | complete |
| feasible | baseline_default | 1 |  | None | off |
| feasible | current_default | 1 |  | None | off |
| feasible | current_preferred | 1 |  | None | not_applicable |
| budget_limited | baseline_default | 13 | assumption.0000.frame.0000, initial.variable.y | proven | off |
| budget_limited | current_default | 13 | assumption.0000.frame.0000, initial.variable.y | proven | off |
| budget_limited | current_preferred | 3 |  | None | timeout |
