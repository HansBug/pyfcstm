"""
用真实 SysDeSim 样例展示当前 Phase7 / Phase8 的 timeline-first 导入结果。

这个脚本放在仓库根目录，目的是给人直接运行、直接阅读，不是 pytest。

运行方式::

    python test_sysdesim_phase7_8_showcase.py
    python test_sysdesim_phase7_8_showcase.py /path/to/model1.xml

这个脚本会展示 6 类内容::

    1. timeline-first machine graph：signal / condition / initial / auto 分类。
    2. `input_map` 候选：哪些名字更像外部输入，哪些只是观测，哪些更像内部写变量。
    3. `event_map` 候选：哪些消息能绑定到机器事件，哪些只是 outbound mismatch。
    4. step 候选：哪些会变成 `emit`，哪些会变成 `SetInput`，哪些只是空 anchor。
    5. time window 与 duration constraint：如何落到具体 step 上。
    6. diagnostics：当前真实样例里仍需要人工关注的点。
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from pyfcstm.convert.sysdesim import (
    SysDeSimTimelineEmitAction,
    SysDeSimTimelineSetInputAction,
    build_sysdesim_phase78_report,
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


def main(argv: list[str] | None = None) -> int:
    """Run the real-sample Phase7/8 showcase."""
    argv = list(sys.argv if argv is None else argv)
    xml_path = _resolve_xml_path(argv)

    if not xml_path.exists():
        print("未找到默认真实样例；如需运行，请显式传入 XML 路径。", file=sys.stderr)
        return 2

    report = build_sysdesim_phase78_report(str(xml_path))

    graph_kind_counts = Counter(item.semantic_kind for item in report.machine_graph)
    force_edges = [
        (".".join(item.source_path), ".".join(item.target_path))
        for item in report.machine_graph
        if item.force_transition
    ]
    emitted_steps = [
        step.step_id
        for step in report.steps
        if any(
            isinstance(action, SysDeSimTimelineEmitAction) for action in step.actions
        )
    ]
    set_input_steps = [
        step.step_id
        for step in report.steps
        if any(
            isinstance(action, SysDeSimTimelineSetInputAction)
            for action in step.actions
        )
    ]
    mismatch_steps = [
        step.step_id
        for step in report.steps
        if "machine_relevant_direction_mismatch" in step.notes
    ]
    input_by_name = {item.normalized_name: item for item in report.input_candidates}
    event_by_name = {item.scenario_event_name: item for item in report.event_candidates}

    _require(report.selected_machine_name == "StateMachine", "状态机名称不符合预期。")
    _require(
        report.selected_interaction_name == "测试用例", "interaction 名称不符合预期。"
    )
    _require(
        graph_kind_counts
        == Counter(
            {
                "signal_transition": 11,
                "initial_transition": 6,
                "condition_transition": 3,
                "auto_transition": 1,
            }
        ),
        "machine graph 分类统计不符合预期。",
    )
    _require(
        force_edges == [("Control.H", "Control.G")], "force transition 不符合预期。"
    )
    _require(
        [item.normalized_name for item in report.input_candidates]
        == ["a", "b", "c", "d", "mode", "rmt", "y"],
        "input candidates 不符合预期。",
    )
    _require(input_by_name["mode"].role == "internal_state", "mode 的分类不符合预期。")
    _require(input_by_name["rmt"].role == "external_input", "rmt 的分类不符合预期。")
    _require(input_by_name["y"].role == "observation_only", "y 的分类不符合预期。")
    _require(
        event_by_name["Sig1"].machine_event_path == "/SIG1", "Sig1 绑定不符合预期。"
    )
    _require(
        event_by_name["Sig2"].machine_event_path == "/SIG2", "Sig2 绑定不符合预期。"
    )
    _require(
        event_by_name["Sig4"].machine_event_path == "/SIG4", "Sig4 绑定不符合预期。"
    )
    _require(
        event_by_name["Sig5"].machine_event_path == "/SIG5", "Sig5 绑定不符合预期。"
    )
    _require(
        event_by_name["Sig6"].machine_event_path == "/SIG6", "Sig6 绑定不符合预期。"
    )
    _require(event_by_name["Sig7"].emit_allowed is False, "Sig7 不应成为 emit 候选。")
    _require(event_by_name["Sig8"].emit_allowed is False, "Sig8 不应成为 emit 候选。")
    _require(event_by_name["Sig9"].emit_allowed is False, "Sig9 不应成为 emit 候选。")
    _require(len(report.steps) == 24, "step 数量不符合预期。")
    _require(
        emitted_steps == ["s01", "s10", "s14", "s16", "s19", "s22"],
        "emit step 列表不符合预期。",
    )
    _require(
        set_input_steps == ["s02", "s04", "s06", "s08", "s20"],
        "SetInput step 列表不符合预期。",
    )
    _require(
        mismatch_steps == ["s13", "s23", "s24"],
        "outbound machine-relevant mismatch step 列表不符合预期。",
    )
    _require(
        [(item.step_id, item.value_text) for item in report.time_windows]
        == [("s03", "0s-1s"), ("s07", "0s-1s")],
        "time window 结果不符合预期。",
    )
    _require(
        [
            (item.left_step_id, item.right_step_id, item.value_text)
            for item in report.duration_constraints
        ]
        == [
            ("s05", "s10", "20s-30s"),
            ("s11", "s12", "10s"),
            ("s12", "s13", "15s"),
            ("s13", "s14", "10s"),
            ("s15", "s16", "10s"),
            ("s17", "s18", "10s"),
            ("s18", "s19", "5s"),
            ("s19", "s21", "30s"),
            ("s21", "s22", "5s"),
        ],
        "duration constraint 结果不符合预期。",
    )

    _print_rule()
    print("Phase7 / Phase8 真实样例展示")
    print()
    print(
        "这个脚本关注的不是 FCSTM 兼容导出，而是 timeline-first importer 现在已经能给出哪些可审查候选。"
    )
    print(
        "如果下面断言全部通过，说明真实样例上的 machine graph / input_map / event_map / step 候选已经落稳。"
    )

    _print_rule()
    print("一、Machine Graph")
    print(
        "现在状态机主干不再只是 phase6 的 trigger 视图，而是显式分成 initial / signal / condition / auto 四类。"
    )
    print("分类统计：", dict(graph_kind_counts))
    print("force transition：", force_edges)
    print("auto transition：")
    for item in report.machine_graph:
        if item.semantic_kind != "auto_transition":
            continue
        print(
            "  - {src} -> {dst} | notes={notes}".format(
                src=".".join(item.source_path) or "[*]",
                dst=".".join(item.target_path) or "[*]",
                notes=list(item.notes),
            )
        )

    _print_rule()
    print("二、Input Map 候选")
    print(
        "这里的目标不是把所有 property 都认成内部变量，而是先按‘外部输入优先’给出可讨论绑定。"
    )
    for item in report.input_candidates:
        print(
            "  - {name} | role={role} | scenario={scenario} | machine={machine}".format(
                name=item.normalized_name,
                role=item.role,
                scenario=list(item.scenario_names),
                machine=list(item.machine_local_names),
            )
        )
        if item.trigger_expressions:
            print(f"    trigger_expressions={list(item.trigger_expressions)}")
        if item.write_texts:
            print(f"    write_texts={list(item.write_texts)}")
        if item.observation_values:
            print(f"    observation_values={list(item.observation_values)}")

    _print_rule()
    print("三、Event Map 候选")
    print(
        "只有 inbound + machine-relevant 的消息，才会在下一步变成真正的 `emit` 候选。"
    )
    for item in report.event_candidates:
        print(
            "  - {name} | machine_event={event} | directions={dirs} | emit_allowed={emit_allowed} | machine_relevant={relevant}".format(
                name=item.scenario_event_name,
                event=item.machine_event_path,
                dirs=list(item.message_directions),
                emit_allowed=item.emit_allowed,
                relevant=item.is_machine_relevant,
            )
        )
        if item.note:
            print(f"    note={item.note}")

    _print_rule()
    print("四、Step 候选")
    print(
        "当前真实样例最后落成 24 个 step，其中 6 个是 emit，5 个是 SetInput，其余是空 anchor。"
    )
    for step in report.steps:
        action_texts = []
        for action in step.actions:
            if isinstance(action, SysDeSimTimelineEmitAction):
                action_texts.append(f"emit({action.machine_event_path})")
            elif isinstance(action, SysDeSimTimelineSetInputAction):
                action_texts.append(
                    f"SetInput({action.input_name}={action.value_text})"
                )
        print(
            "  - {step_id} | kind={kind} | direction={direction} | actions={actions} | notes={notes}".format(
                step_id=step.step_id,
                kind=step.anchor_kind,
                direction=step.direction,
                actions=action_texts,
                notes=list(step.notes),
            )
        )

    _print_rule()
    print("五、时间约束绑定")
    print("time window 会绑定到具体 step；duration constraint 会绑定到两个 step 之间。")
    print("time windows：")
    for item in report.time_windows:
        print(f"  - {item.step_id}: {item.value_text}")
    print("duration constraints：")
    for item in report.duration_constraints:
        print(f"  - [{item.left_step_id}, {item.right_step_id}] = {item.value_text}")

    _print_rule()
    print("六、Diagnostics")
    print(
        "当前最需要关注的是 3 个 outbound machine-relevant signal mismatch：Sig9 / Sig8 / Sig7。"
    )
    print("diagnostic 统计：", dict(Counter(item.code for item in report.diagnostics)))

    _print_rule()
    print("结论")
    print("当前 phase7/8 已经把真实样例稳定收敛成 timeline-first IR。")
    print(
        "也就是说，后续 phase9/10 的重点将不再是‘怎么抽出来’，而是‘如何把这些候选继续绑定到 runtime / SMT 语义上’。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
