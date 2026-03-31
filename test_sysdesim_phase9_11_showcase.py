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

from dataclasses import dataclass
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from pyfcstm.convert.sysdesim import (
    build_sysdesim_state_coexistence_timeline_report,
)

DEFAULT_SAMPLE_XML = Path("/home/hansbug/文档/damnx_sysdesim_sample/model1_fixed.xml")


@dataclass(frozen=True)
class _ShowcaseExample:
    """One configured coexistence example in the root showcase script."""

    title: str
    left_machine_alias: str
    left_state_ref: str
    right_machine_alias: str
    right_state_ref: str
    expected_status: str
    expected_reason: Optional[str] = None
    expected_first_symbol: Optional[str] = None


@dataclass(frozen=True)
class _ShowcaseExampleResult:
    """Normalized result for one showcase example."""

    example: _ShowcaseExample
    status: str
    reason: Optional[str]
    timeline: Optional[object]


SHOWCASE_EXAMPLES = (
    _ShowcaseExample(
        title="可共存示例：StateMachine__Control_region2.H.L 与 StateMachine__Control_region3.X",
        left_machine_alias="StateMachine__Control_region2",
        left_state_ref="H.L",
        right_machine_alias="StateMachine__Control_region3",
        right_state_ref="X",
        expected_status="sat",
        expected_first_symbol="tau__StateMachine__Control_region3__s24__1",
    ),
    _ShowcaseExample(
        title="不可共存示例：StateMachine__Control_region2.M 与 StateMachine__Control_region3.X",
        left_machine_alias="StateMachine__Control_region2",
        left_state_ref="M",
        right_machine_alias="StateMachine__Control_region3",
        right_state_ref="X",
        expected_status="unsat",
        expected_reason="The left queried state never appears in the imported trajectory.",
    ),
    _ShowcaseExample(
        title="新增检查：StateMachine__Control_region2.H.M 与 StateMachine__Control_region3.S",
        left_machine_alias="StateMachine__Control_region2",
        left_state_ref="H.M",
        right_machine_alias="StateMachine__Control_region3",
        right_state_ref="S",
        expected_status="unsat",
        expected_reason="The left queried state never appears in the imported trajectory.",
    ),
)


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


def _run_showcase_example(
    xml_path: Path,
    example: _ShowcaseExample,
) -> _ShowcaseExampleResult:
    """Execute one configured coexistence example and normalize its result."""
    try:
        timeline = build_sysdesim_state_coexistence_timeline_report(
            str(xml_path),
            example.left_machine_alias,
            example.left_state_ref,
            example.right_machine_alias,
            example.right_state_ref,
        )
    except LookupError as err:
        status = "invalid"
        reason = str(err)
        timeline = None
    else:
        status = timeline.status
        reason = timeline.reason

    _require(
        status == example.expected_status,
        "{title} 的结果应为 {expected}，实际为 {actual}。".format(
            title=example.title,
            expected=example.expected_status,
            actual=status,
        ),
    )
    if example.expected_reason is not None:
        _require(
            reason == example.expected_reason,
            "{title} 的原因说明不符合预期。".format(title=example.title),
        )
    if example.expected_first_symbol is not None:
        _require(timeline is not None, "{title} 应返回 timeline。".format(title=example.title))
        _require(
            timeline.first_coexistence_symbol == example.expected_first_symbol,
            "{title} 的首次共存点不符合预期。".format(title=example.title),
        )

    return _ShowcaseExampleResult(
        example=example,
        status=status,
        reason=reason,
        timeline=timeline,
    )


def _print_showcase_example(index: int, result: _ShowcaseExampleResult) -> None:
    """Print one showcase example through the shared output path."""
    _print_rule()
    print("{index}、{title}".format(index=index, title=result.example.title))
    if result.status != "sat" or result.timeline is None:
        print("结果：不行")
        print("原因：", result.reason or "未找到可构造的共存时间点。")
        return

    print("结果：可以")
    print("求解结果：", result.timeline.status)
    print("时间域类型：", result.timeline.time_domain)
    print(
        "首次共存时刻：{symbol} = {time}".format(
            symbol=result.timeline.first_coexistence_symbol,
            time=result.timeline.first_coexistence_time_text,
        )
    )
    print("说明：", result.timeline.first_coexistence_note)
    print()
    print("完整时间轴表：")
    _print_timeline_table(
        result.timeline.timeline_points,
        result.timeline.first_coexistence_symbol,
    )


def main(argv: Optional[List[str]] = None) -> int:
    """Run the real-sample Phase9/10/11 showcase."""
    argv = list(sys.argv if argv is None else argv)
    xml_path = _resolve_xml_path(argv)

    if not xml_path.exists():
        print("未找到默认真实样例；如需运行，请显式传入 XML 路径。", file=sys.stderr)
        return 2

    results = [_run_showcase_example(xml_path, example) for example in SHOWCASE_EXAMPLES]

    _print_rule()
    print("Phase11 共存时间轴展示")
    print()
    print(
        "时间变量在求解器里使用的是 Z3 Real，也就是连续时间上的实数。"
    )
    print(
        "它不是 IEEE 754 的浮点位模式；展示时会把求解结果打印成普通十进制文本，所以你可以把它理解为连续时间上的 float 值。"
    )

    for index, result in enumerate(results, start=1):
        print()
        _print_showcase_example(index, result)

    _print_rule()
    print("结论")
    print(
        "当前 3 个示例都走同一个输出出口：若可共存，就打印完整 witness 时间轴表；若不可共存，就统一打印 `不行` 和精确原因。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
