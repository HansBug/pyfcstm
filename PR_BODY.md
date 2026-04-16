## 摘要

- 把 timeline 验证 / report 能力放到 `pyfcstm sysdesim validate` 子命令下，不再和原有 `pyfcstm sysdesim` 转换入口混在一起。
- 保持原有转换路径兼容：`pyfcstm sysdesim -i ... -o ...` 仍然输出 FCSTM 文件族和 conversion report。
- 修复 Phase11 的初始状态缺口：引入初始观测符号 `t00` 和初始状态窗口，使“只在场景开始前成立的共存”不再被误判成 `unsat`。
- 补齐 Phase13 方向的 CLI / 单测覆盖：包括嵌套的 `sysdesim validate` 流程和初始状态共存的回归测试。

## 验证

- `pytest test/convert/sysdesim/test_phase9_11.py test/entry/test_sysdesim.py -q`

## 真实样例 CLI 复现

下面这组命令已于 `2026-04-16` 在真实样例 `model1_fixed_v2.xml` 上实跑通过。
运行时只需要把 `XML` 改成你手头那份 `model1_fixed_v2.xml` 的路径即可。

```bash
cd path/to/pyfcstm

export XML='path/to/model1_fixed_v2.xml'
export OUT='./.tmp/model1_fixed_v2_cli_20260416'

mkdir -p "$OUT/convert" "$OUT/reports"

venv/bin/python -m pyfcstm sysdesim \
  -i "$XML" \
  -o "$OUT/convert" \
  --clear

venv/bin/python -m pyfcstm sysdesim validate \
  -i "$XML" \
  --report-file "$OUT/reports/timeline_import_report.json"

venv/bin/python -m pyfcstm sysdesim validate \
  -i "$XML" \
  --left-machine-alias StateMachine__Control_region2 \
  --left-state H.L \
  --right-machine-alias StateMachine__Control_region3 \
  --right-state X \
  --report-file "$OUT/reports/phase11_sat_report.json"
```

期望检查点：

- 转换步骤会导出 `5` 个 FCSTM 输出：
  - `StateMachine`
  - `StateMachine__Control_region1`
  - `StateMachine__Control_region2`
  - `StateMachine__Control_region3`
  - `StateMachine__Control_region4`
- 转换 CLI 会打印 `Tick: not required`
- `timeline_import_report.json` 中应看到：
  - `len(phase78.steps) == 28`
  - `len(phase78.duration_constraints) == 9`
  - `len(phase10.bindings) == 5`
  - `len(phase10.traces) == 5`
- `phase11_sat_report.json` 中应看到：
  - `phase11.solve_result.status == "sat"`
  - `phase11.timeline_report.first_coexistence_symbol == "tau__StateMachine__Control_region3__s20__1"`
  - `phase11.timeline_report.first_coexistence_time_text == "67"`
