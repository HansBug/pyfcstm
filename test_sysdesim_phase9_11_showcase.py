"""
用真实 SysDeSim 样例展示当前 Phase9 / Phase10 / Phase11 的落地结果。

这个脚本放在仓库根目录，目的是给人直接运行、直接阅读，不是 pytest。

运行方式::

    python test_sysdesim_phase9_11_showcase.py
    python test_sysdesim_phase9_11_showcase.py /path/to/model1_fixed.xml

这个脚本只展示你真正关心的东西::

    1. 时间变量的语义是什么。
    2. 若两个状态可共存，给出一条完整时间轴。
    3. 若两个状态不可共存，只给出精确 `unsat` 原因。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional, Tuple

from pyfcstm.convert.sysdesim import (
    build_sysdesim_state_coexistence_timeline_report,
)

DEFAULT_SAMPLE_XML = Path("/home/hansbug/文档/damnx_sysdesim_sample/model1_fixed.xml")


def _resolve_xml_path(argv: List[str]) -> Path:
    """Resolve the XML path from CLI args, falling back to the fixed real sample."""
    if len(argv) >= 2:
        return Path(argv[1]).expanduser()
    return DEFAULT_SAMPLE_XML


def _require(condition: bool, message: str) -> None:
    """Raise a readable assertion error when one expected fact is missing."""
    if not condition:
        raise AssertionError(message)


def _print_rule() -> None:
    """Print a visual separator."""
    print("=" * 80)


def _format_actions(actions: Tuple[str, ...]) -> str:
    """Format one action tuple for one timeline row."""
    if not actions:
        return "-"
    rendered = []
    for item in actions:
        if item.startswith("hidden_auto(") and ": " in item and " -> " in item:
            prefix = item[len("hidden_auto(") : -1]
            machine_alias, arc = prefix.split(": ", 1)
            src, dst = arc.split(" -> ", 1)
            rendered.append(
                "tau:{alias} {src}->{dst}".format(
                    alias=_short_machine_alias(machine_alias),
                    src=_short_state_text(src),
                    dst=_short_state_text(dst),
                )
            )
        elif item.startswith("SetInput("):
            rendered.append(item[len("SetInput(") : -1])
        else:
            rendered.append(item)
    return ",".join(rendered)


def _short_machine_alias(machine_alias: str) -> str:
    """Convert one long machine alias into a short table header token."""
    if machine_alias == "StateMachine":
        return "Main"
    if "_region" in machine_alias:
        return "R{}".format(machine_alias.rsplit("_region", 1)[-1])
    return machine_alias


def _short_state_text(state_path: str) -> str:
    """Render one state path as a short relative state name."""
    if ".Control." in state_path:
        return state_path.split(".Control.", 1)[1]
    if state_path.endswith(".Control"):
        return "Control"
    return state_path.rsplit(".", 1)[-1]


def _fit(text: str, width: int) -> str:
    """Fit one cell into a fixed-width column."""
    if len(text) <= width:
        return text.ljust(width)
    if width <= 3:
        return text[:width]
    return text[: width - 3] + "..."


def _print_timeline_table(
    timeline_points,
    first_symbol: Optional[str],
) -> None:
    """Print one compact timeline table with controlled line width."""
    headers = ["t", "pt", "act", "Main", "R1", "R2", "R3", "R4", "co"]
    widths = [6, 8, 16, 8, 8, 8, 8, 8, 8]

    def _row(values: List[str]) -> str:
        return "| " + " | ".join(
            _fit(item, width) for item, width in zip(values, widths)
        ) + " |"

    print("列说明：")
    print("  - `t` 是求解得到的连续时间实数值。")
    print("  - `pt` 是时间点类型，`sXX` 表示 step，`tau@...` 表示隐藏 auto。")
    print("  - `Main/R1/R2/R3/R4` 分别对应主状态机和 4 个 region 输出。")
    print("  - 状态值只保留 `Control` 之后的相对状态名。")
    print("  - `co` 为 `start` 表示从该行开始首次共存，`yes` 表示该行时仍在共存。")
    print()
    print(_row(headers))
    print(_row(["-" * width for width in widths]))
    for item in timeline_points:
        state_map = {
            _short_machine_alias(alias): _short_state_text(state)
            for alias, state in item.machine_states
        }
        point_label = item.point_label
        if item.point_kind == "auto":
            point_label = "tau@{}".format(point_label)
        co_text = ""
        if item.is_coexistent:
            co_text = "start" if item.symbol == first_symbol else "yes"
        print(
            _row(
                [
                    item.time_value_text,
                    point_label,
                    _format_actions(item.actions),
                    state_map.get("Main", "-"),
                    state_map.get("R1", "-"),
                    state_map.get("R2", "-"),
                    state_map.get("R3", "-"),
                    state_map.get("R4", "-"),
                    co_text,
                ]
            )
        )


def main(argv: Optional[List[str]] = None) -> int:
    """Run the real-sample Phase9/10/11 showcase."""
    argv = list(sys.argv if argv is None else argv)
    xml_path = _resolve_xml_path(argv)

    if not xml_path.exists():
        print("未找到默认真实样例；如需运行，请显式传入 XML 路径。", file=sys.stderr)
        return 2

    unsat_timeline = build_sysdesim_state_coexistence_timeline_report(
        str(xml_path),
        "StateMachine__Control_region2",
        "M",
        "StateMachine__Control_region3",
        "X",
    )
    sat_timeline = build_sysdesim_state_coexistence_timeline_report(
        str(xml_path),
        "StateMachine__Control_region2",
        "L",
        "StateMachine__Control_region3",
        "X",
    )
    _require(unsat_timeline.status == "unsat", "M/X 查询应为 unsat。")
    _require(
        unsat_timeline.reason
        == "The left queried state never appears in the imported trajectory.",
        "M/X 查询原因说明不符合预期。",
    )
    _require(sat_timeline.status == "sat", "L/X 查询应为 sat。")
    _require(
        sat_timeline.first_coexistence_symbol
        == "tau__StateMachine__Control_region3__s24__1",
        "L/X 的首次共存点应从 `tau__StateMachine__Control_region3__s24__1` 开始。",
    )

    _print_rule()
    print("Phase11 共存时间轴展示")
    print()
    print(
        "时间变量在求解器里使用的是 Z3 Real，也就是连续时间上的实数。"
    )
    print(
        "它不是 IEEE 754 的浮点位模式；展示时会把求解结果打印成普通十进制文本，所以你可以把它理解为连续时间上的 float 值。"
    )

    _print_rule()
    print("一、可共存示例：StateMachine__Control_region2.L 与 StateMachine__Control_region3.X")
    print("求解结果：", sat_timeline.status)
    print("时间域类型：", sat_timeline.time_domain)
    print(
        "首次共存时刻：{symbol} = {time}".format(
            symbol=sat_timeline.first_coexistence_symbol,
            time=sat_timeline.first_coexistence_time_text,
        )
    )
    print("说明：", sat_timeline.first_coexistence_note)
    print()
    print("完整时间轴表：")
    _print_timeline_table(
        sat_timeline.timeline_points,
        sat_timeline.first_coexistence_symbol,
    )

    print()
    _print_rule()
    print("二、不可共存示例：StateMachine__Control_region2.M 与 StateMachine__Control_region3.X")
    print("求解结果：", unsat_timeline.status)
    print("原因：", unsat_timeline.reason)

    _print_rule()
    print("结论")
    print(
        "当前输出已经收敛成一条 witness 时间轴：你可以直接看到每个 step 的时间、每个隐藏 auto 的时间、各状态机在这些时刻的当前状态，以及首次共存究竟从哪个时刻开始。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
