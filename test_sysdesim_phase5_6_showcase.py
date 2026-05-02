"""
用真实 SysDeSim 样例展示当前 Phase5 / Phase6 的抽取结果。

这个脚本放在仓库根目录，目的是给人直接运行、直接阅读，不是 pytest。

运行方式::

    python test_sysdesim_phase5_6_showcase.py
    python test_sysdesim_phase5_6_showcase.py /path/to/model1.xml

这个脚本会展示 5 类内容::

    1. 真实样例里 interaction / lifeline / observation 的总体规模。
    2. 消息方向抽取：哪些是外向内、内向外、self message。
    3. `StateInvariant`、`DurationConstraint`、`TimeConstraint` 的观测抽取结果。
    4. 状态机 transition 的统一 trigger 视图：signal / condition / none。
    5. 名字归一化提示：顺序图里的名字如何与状态机条件里的名字对齐。

期望输出重点::

    - interaction 数量为 1，lifeline 数量为 2。
    - “控制”会被识别为 machine-internal lifeline。
    - 消息方向分布为 inbound 6 / outbound 11 / self 2。
    - `Rmt=4999` 这类观测会被抽成输入提示，并与 `rmt < 5000` 对齐。
    - `Idle -> Control` 是 signal trigger。
    - `Control.S -> Control.X` 是 none trigger。
    - 真实样例里没有被状态机 transition 实际引用的 `TimeEvent`。
    - 真实样例里没有 cross-level transition，也没有 cross-region transition。
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Iterable, Optional

from pyfcstm.convert.sysdesim import (
    SysDeSimDurationConstraintObservation,
    SysDeSimMessageObservation,
    SysDeSimStateInvariantObservation,
    SysDeSimTimeConstraintObservation,
    SysDeSimTriggerCondition,
    SysDeSimTriggerNone,
    SysDeSimTriggerSignal,
    build_sysdesim_phase56_report,
    load_sysdesim_machine,
    load_sysdesim_raw_xmi,
    summarize_sysdesim_raw_xmi,
)

DEFAULT_SAMPLE_XML = Path(
    "/drive/f/电脑管家迁移文件/xwechat_files/"
    "wxid_8td20f9kf3do21_dfa7/msg/file/2026-03/测试用例图/model/model1.xml"
)


def _resolve_xml_path(argv: list[str]) -> Path:
    """Resolve the XML path from CLI args, falling back to the real sample."""
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


def _print_kv(label: str, value: object) -> None:
    """Print one labeled value line."""
    print(f"{label}：{value}")


def _pick_message_examples(
    messages: Iterable[SysDeSimMessageObservation], direction: str, limit: int = 3
) -> list[SysDeSimMessageObservation]:
    """Pick a few message examples of one direction in order."""
    return [item for item in messages if item.direction == direction][:limit]


def _find_transition_summary(
    report, source_path: tuple[str, ...], target_path: tuple[str, ...]
) -> Optional[str]:
    """Return one short human-readable trigger summary for a specific edge."""
    for item in report.transitions:
        if item.source_path != source_path or item.target_path != target_path:
            continue
        trigger = item.trigger
        if isinstance(trigger, SysDeSimTriggerSignal):
            return f"signal:{trigger.signal_name}"
        if isinstance(trigger, SysDeSimTriggerCondition):
            return f"condition:{trigger.raw_text}"
        if isinstance(trigger, SysDeSimTriggerNone):
            return "none"
    return None


def main(argv: list[str] | None = None) -> int:
    """Run the real-sample Phase5/6 showcase."""
    argv = list(sys.argv if argv is None else argv)
    xml_path = _resolve_xml_path(argv)

    if not xml_path.exists():
        print("未找到默认真实样例；如需运行，请显式传入 XML 路径。", file=sys.stderr)
        return 2

    report = build_sysdesim_phase56_report(str(xml_path))
    machine = load_sysdesim_machine(str(xml_path))
    raw_document = load_sysdesim_raw_xmi(str(xml_path))
    raw_summary = summarize_sysdesim_raw_xmi(raw_document)

    messages = [
        item
        for item in report.interaction.observation_stream
        if isinstance(item, SysDeSimMessageObservation)
    ]
    invariants = [
        item
        for item in report.interaction.observation_stream
        if isinstance(item, SysDeSimStateInvariantObservation)
    ]
    durations = [
        item
        for item in report.interaction.observation_stream
        if isinstance(item, SysDeSimDurationConstraintObservation)
    ]
    times = [
        item
        for item in report.interaction.observation_stream
        if isinstance(item, SysDeSimTimeConstraintObservation)
    ]

    message_direction_counts = Counter(item.direction for item in messages)
    observation_kind_counts = Counter(
        type(item).__name__ for item in report.interaction.observation_stream
    )
    internal_lifelines = [
        item.raw_name
        for item in report.interaction.lifelines
        if item.is_machine_internal
    ]
    cross_level_count = sum(
        1 for item in machine.walk_transitions() if item.is_cross_level
    )
    cross_region_count = sum(
        1 for item in machine.walk_transitions() if item.is_cross_region
    )
    used_time_event_count = sum(
        1 for item in machine.walk_transitions() if item.trigger_kind == "time"
    )

    _require(report.selected_machine_name == "StateMachine", "状态机名称不符合预期。")
    _require(
        report.selected_interaction_name == "测试用例", "interaction 名称不符合预期。"
    )
    _require(
        [item.raw_name for item in report.interaction.lifelines] == ["控制", "模块"],
        "lifeline 抽取结果不符合预期。",
    )
    _require(
        internal_lifelines == ["控制"], "machine-internal lifeline 推断结果不符合预期。"
    )
    _require(
        len(report.interaction.observation_stream) == 35, "observation 总数不符合预期。"
    )
    _require(
        message_direction_counts == Counter({"outbound": 11, "inbound": 6, "self": 2}),
        "消息方向统计不符合预期。",
    )
    _require(
        raw_summary.xmi_type_counts.get("uml:TimeEvent") == 22,
        "原始 TimeEvent 总数不符合预期。",
    )
    _require(used_time_event_count == 0, "状态机 transition 不应实际引用 TimeEvent。")
    _require(cross_level_count == 0, "真实样例不应存在 cross-level transition。")
    _require(cross_region_count == 0, "真实样例不应存在 cross-region transition。")
    _require(
        _find_transition_summary(report, ("Idle",), ("Control",)) == "signal:SIG1",
        "Idle -> Control 的 trigger 识别不符合预期。",
    )
    _require(
        _find_transition_summary(report, ("Control", "S"), ("Control", "X")) == "none",
        "Control.S -> Control.X 应被识别为 none trigger。",
    )

    _print_rule()
    print("Phase5 / Phase6 真实样例展示")
    print()
    print(
        "这个脚本关注的是“已经从真实样例里稳定抽出了什么”，而不是去恢复完整顺序图执行语义。"
    )
    print("如果断言通过，说明当前 phase5/6 的中间结果与这份真实样例是一致的。")

    _print_rule()
    print("一、样例总体规模")
    _print_kv("状态机", report.selected_machine_name)
    _print_kv("顺序图", report.selected_interaction_name)
    _print_kv("lifeline", [item.raw_name for item in report.interaction.lifelines])
    _print_kv("内部 lifeline", internal_lifelines)
    _print_kv("observation 总数", len(report.interaction.observation_stream))
    _print_kv("observation 分类统计", dict(observation_kind_counts))
    _print_kv(
        "原始 XMI 里的关键类型计数",
        {
            key: raw_summary.xmi_type_counts[key]
            for key in [
                "uml:Interaction",
                "uml:Lifeline",
                "uml:Message",
                "uml:StateInvariant",
                "uml:DurationConstraint",
                "uml:TimeConstraint",
                "uml:TimeEvent",
            ]
        },
    )

    _print_rule()
    print("二、消息方向抽取")
    print(
        "只看真实样例本身，可以看到 machine-facing 的消息并不多，绝大多数是向外发出的。"
    )
    _print_kv("方向统计", dict(message_direction_counts))
    for direction in ["inbound", "outbound", "self"]:
        examples = _pick_message_examples(messages, direction)
        print(f"{direction} 示例：")
        for item in examples:
            label = item.display_name or "<空名称>"
            print(
                "  - {src} -> {dst} | {name} | signature={sig}".format(
                    src=item.source_lifeline_name,
                    dst=item.target_lifeline_name,
                    name=label,
                    sig=item.signal_name,
                )
            )

    _print_rule()
    print("三、状态观测与时间约束")
    print("`StateInvariant` 会被保守地抽成 `name=value` 形式的输入观测提示。")
    for item in invariants:
        print(
            "  - invariant: {text} | 归一化名字={name} | lifeline={lifeline}".format(
                text=item.raw_text,
                name=item.normalized_name,
                lifeline=item.lifeline_name,
            )
        )
    print(
        "`DurationConstraint` 和 `TimeConstraint` 目前先保留为时间窗口观测，不急着解释成最终 step。"
    )
    for item in durations[:3]:
        print(
            "  - duration: 约束对象={ids} | min={min_text} | max={max_text}".format(
                ids=list(item.constrained_element_ids),
                min_text=item.min_text,
                max_text=item.max_text,
            )
        )
    for item in times:
        print(
            "  - time: 约束对象={ids} | min={min_text} | max={max_text}".format(
                ids=list(item.constrained_element_ids),
                min_text=item.min_text,
                max_text=item.max_text,
            )
        )

    _print_rule()
    print("四、状态机 trigger 统一抽象")
    print(
        "现在 transition 不再分散看 signal / change event / guard，而是统一落到 signal / condition / none 三类。"
    )
    for item in report.transitions:
        trigger = item.trigger
        if isinstance(trigger, SysDeSimTriggerSignal):
            trigger_text = f"signal:{trigger.signal_name}"
        elif isinstance(trigger, SysDeSimTriggerCondition):
            trigger_text = f"condition:{trigger.raw_text}"
        else:
            trigger_text = "none"
        print(
            "  - {src} -> {dst} | {trigger_text} | transition_ids={ids}".format(
                src=".".join(item.source_path) or "[*]",
                dst=".".join(item.target_path) or "[*]",
                trigger_text=trigger_text,
                ids=list(item.transition_ids),
            )
        )

    _print_rule()
    print("五、名字归一化提示")
    print(
        "这一层的目标是把顺序图观测名与状态机条件名收敛到同一命名空间，为后续 binding 做准备。"
    )
    for item in report.name_hints:
        print(
            "  - {name} | observation={obs} | trigger={trg}".format(
                name=item.normalized_name,
                obs=list(item.observation_names),
                trg=list(item.trigger_variable_names),
            )
        )

    _print_rule()
    print("六、真实样例里明确不存在的东西")
    print("这些信息很重要，因为它们决定后续 phase7/8 不需要为这份样例额外兜底。")
    _print_kv("transition 实际引用的 TimeEvent 数", used_time_event_count)
    _print_kv("cross-level transition 数", cross_level_count)
    _print_kv("cross-region transition 数", cross_region_count)

    _print_rule()
    print("结论")
    print(
        "当前 phase5/6 已经能把真实样例中的顺序图观测和状态机 trigger 主干稳定抽出来。"
    )
    print(
        "后续 phase7/8 的重点就不再是‘能不能读出来’，而是‘如何把这些观测绑定成 timeline step / SetInput / emit 候选’。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
