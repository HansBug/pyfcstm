"""
Figures of the region performance page, drawn from the committed data files.

Every ``fig_<name>_<lang>.plot.py`` script calls :func:`main` with one figure name
and one language (``en`` or ``zh``). The data is read from ``data/*.jsonl`` next
to this file; the figure text is the only thing that differs between languages.

The output is reproducible: the hash salt is fixed, text stays text (the SVG names
fonts, it does not embed them) and no date is written. Latin text is laid out with
DejaVu Sans (bundled with matplotlib) and Chinese text with the SimHei font that the
repository ships in ``docs/source/_libs``, so the layout does not depend on the fonts
installed on the machine; the SVG lists CJK fonts that a browser is likely to have.
"""

import argparse
import json
import os
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as font_manager  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
BLUE, ORANGE, GREEN, GRAY, RED = "#1f77b4", "#d95f02", "#2ca02c", "#666666", "#c0392b"
CJK_STACK = "'DejaVu Sans', 'Noto Sans CJK SC', 'Microsoft YaHei', 'PingFang SC', 'Droid Sans Fallback', sans-serif"
LATIN_STACK = "'DejaVu Sans', sans-serif"


def rows(name):
    """
    Read one JSON Lines data file.

    :param name: File name inside ``data/``.
    :type name: str
    :return: Records.
    :rtype: list
    """
    with open(os.path.join(DATA, name)) as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sweep(records, name, axis, key):
    """
    Collect ``(x, y)`` of one sweep sorted by x.

    :param records: Records with ``sweep`` and ``model``.
    :type records: list
    :param name: Sweep name.
    :type name: str
    :param axis: Model parameter on the x axis.
    :type axis: str
    :param key: Function or field name giving y.
    :type key: object
    :return: Two arrays.
    :rtype: tuple
    """
    pts = sorted(
        (r["model"][axis], key(r) if callable(key) else r[key])
        for r in records
        if r["sweep"] == name
    )
    return np.array([p[0] for p in pts], float), np.array([p[1] for p in pts], float)


def poly(ax, xs, ys, degree, **kw):
    """
    Draw a least-squares polynomial of the given degree and return its ``R^2``.

    :param ax: Axes.
    :param xs: Abscissae.
    :param ys: Ordinates.
    :param degree: Polynomial degree.
    :type degree: int
    :return: Coefficient of determination.
    :rtype: float
    """
    coef = np.polyfit(xs, ys, degree)
    grid = np.linspace(xs.min(), xs.max(), 200)
    ax.plot(grid, np.polyval(coef, grid), **kw)
    fit = np.polyval(coef, xs)
    ss_res = float(np.sum((ys - fit) ** 2))
    ss_tot = float(np.sum((ys - ys.mean()) ** 2))
    return 1 - ss_res / ss_tot if ss_tot else 1.0


def setup(lang):
    """
    Apply the style shared by every figure.

    :param lang: ``en`` or ``zh``.
    :type lang: str
    :return: ``None``.
    :rtype: None
    """
    families = ["DejaVu Sans"]
    if lang == "zh":
        # The font file is part of the repository, so every machine lays the
        # Chinese labels out with the same glyph metrics.
        simhei = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "_libs", "SimHei.ttf"
        )
        font_manager.fontManager.addfont(simhei)
        families.append("SimHei")
    plt.rcParams.update(
        {
            "svg.fonttype": "none",
            "svg.hashsalt": "region-performance",
            "font.family": families,
            "font.size": 9,
            "axes.grid": True,
            "grid.alpha": 0.3,
            "axes.unicode_minus": False,
            "figure.dpi": 100,
        }
    )


def save(fig, out, lang):
    """
    Save a figure deterministically and fix the font stack in the SVG text.

    :param fig: Figure.
    :param out: Output path.
    :type out: str
    :param lang: ``en`` or ``zh``.
    :type lang: str
    :return: ``None``.
    :rtype: None
    """
    fig.savefig(out, format="svg", metadata={"Date": None}, bbox_inches="tight")
    with open(out, encoding="utf-8") as handle:
        text = handle.read()
    stack = CJK_STACK if lang == "zh" else LATIN_STACK
    text = re.sub(
        r"font: (\d+px) '[^;\"]*'", lambda m: "font: %s %s" % (m.group(1), stack), text
    )
    with open(out, "w", encoding="utf-8") as handle:
        handle.write(text)


L = {
    "R": {"en": "regions per owner R", "zh": "每个拥有者的区域数 R"},
    "S": {"en": "states per region S", "zh": "每个区域的状态数 S"},
    "T": {"en": "transitions per state T", "zh": "每个状态的转换数 T"},
    "V": {"en": "variables written per transition V", "zh": "每个转换写入的变量数 V"},
    "D": {"en": "owner nesting levels D", "zh": "拥有者嵌套层数 D"},
}


def fig_model_size(lang):
    """
    Region form against flat expansion: states and transitions.

    :param lang: ``en`` or ``zh``.
    :return: Figure.
    """
    data = [
        r for r in rows("e1.jsonl") if r["kind"] == "product" and r["model"]["T"] == 1
    ]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
    colors = {2: BLUE, 3: GREEN, 4: ORANGE}
    rs = np.arange(1, 9)
    for ax, kind in zip(axes, ("states", "transitions")):
        for S, color in colors.items():
            pts = sorted((r["model"]["R"], r) for r in data if r["model"]["S"] == S)
            xs = [p[0] for p in pts]
            reg = [
                p[1][
                    "region_%s" % ("leaf_states" if kind == "states" else "transitions")
                ]
                for p in pts
            ]
            flat = [
                p[1]["flat_%s" % ("leaf_states" if kind == "states" else "transitions")]
                for p in pts
            ]
            ax.plot(xs, reg, "o", color=color)
            ax.plot(xs, flat, "s", color=color)
            ax.plot(rs, rs * S, "-", color=color, lw=1)
            ax.plot(
                rs,
                S**rs if kind == "states" else S**rs * (2**rs - 1),
                "--",
                color=color,
                lw=1,
            )
        ax.set_yscale("log")
        ax.set_xlabel(L["R"][lang])
    axes[0].set_ylabel("leaf states" if lang == "en" else "叶子状态数")
    axes[1].set_ylabel("transitions" if lang == "en" else "转换数")
    axes[0].set_title(
        "(a) " + ("states: sum vs product" if lang == "en" else "状态：和与积")
    )
    axes[1].set_title(
        "(b) " + ("transitions: sum vs product" if lang == "en" else "转换：和与积")
    )
    handles = [
        plt.Line2D(
            [],
            [],
            color=GRAY,
            marker="o",
            ls="-",
            label="regions: R·S (measured, formula)"
            if lang == "en"
            else "区域写法：R·S（实测，公式）",
        ),
        plt.Line2D(
            [],
            [],
            color=GRAY,
            marker="s",
            ls="--",
            label="flat expansion (measured, formula)"
            if lang == "en"
            else "展开成一台状态机（实测，公式）",
        ),
    ] + [plt.Line2D([], [], color=c, lw=3, label="S=%d" % s) for s, c in colors.items()]
    axes[0].legend(handles=handles, fontsize=7, loc="upper left")
    fig.tight_layout()
    return fig


def fig_sim_sweeps(lang):
    """
    Simulator time per cycle against R, S, T and V.

    :param lang: ``en`` or ``zh``.
    :return: Figure.
    """
    data = rows("e2.jsonl")
    fig, axes = plt.subplots(1, 4, figsize=(12, 3.4))
    for ax, (name, degree) in zip(axes, (("R", 2), ("S", 1), ("T", 1), ("V", 1))):
        xs, ys = sweep(data, name, name, lambda r: r["seconds_per_cycle"] * 1e3)
        ax.plot(xs, ys, "o", color=BLUE, label="median" if lang == "en" else "中位数")
        r2 = poly(
            ax,
            xs,
            ys,
            degree,
            color=GRAY,
            ls="--",
            label="fit" if lang == "en" else "拟合",
        )
        kind = {1: ("linear", "线性"), 2: ("quadratic", "二次")}[degree]
        ax.set_xlabel(L[name][lang])
        ax.set_title(
            "%s fit, R² = %.4f" % (kind[0], r2)
            if lang == "en"
            else "%s拟合，R² = %.4f" % (kind[1], r2),
            fontsize=8,
        )
        ax.set_ylim(bottom=0)
    axes[0].set_ylabel("ms per cycle" if lang == "en" else "每周期毫秒数")
    axes[0].legend(fontsize=7)
    fig.tight_layout()
    return fig


def fig_depth(lang):
    """
    Simulator time per cycle and first-cycle time against nesting depth.

    :param lang: ``en`` or ``zh``.
    :return: Figure.
    """
    data = rows("e2.jsonl")
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
    for name, color, label in (
        ("D_chain", BLUE, "R=1 chain" if lang == "en" else "R=1 的链"),
        (
            "D_branch",
            ORANGE,
            "R=2, one nested" if lang == "en" else "R=2，其中一个嵌套",
        ),
    ):
        xs, steady = sweep(data, name, "D", lambda r: r["seconds_per_cycle"] * 1e6)
        _, first = sweep(data, name, "D", lambda r: r["first_cycle"]["min"] * 1e6)
        axes[0].plot(xs, steady, "o-", color=color, label=label)
        axes[1].plot(xs, first, "o-", color=color, label=label)
    for ax in axes:
        ax.set_yscale("log")
        ax.set_xlabel(L["D"][lang])
    axes[0].set_ylabel(
        "µs per cycle (steady)" if lang == "en" else "每周期微秒数（稳态）"
    )
    axes[1].set_ylabel("µs, first cycle" if lang == "en" else "第一个周期的微秒数")
    axes[0].set_title("(a) " + ("steady state" if lang == "en" else "稳态"))
    axes[1].set_title(
        "(b) "
        + (
            "first cycle (enters every owner)"
            if lang == "en"
            else "第一个周期（进入每个拥有者）"
        )
    )
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    return fig


def fig_python_vs_simulator(lang):
    """
    Generated Python runtime against the simulator on the same sweeps.

    :param lang: ``en`` or ``zh``.
    :return: Figure.
    """
    sim, gen = rows("e2.jsonl"), rows("e3.jsonl")
    fig, axes = plt.subplots(1, 4, figsize=(12, 3.4))
    for ax, name in zip(axes, ("R", "S", "T", "V")):
        xs, a = sweep(sim, name, name, lambda r: r["seconds_per_cycle"] * 1e6)
        _, b = sweep(gen, name, name, lambda r: r["seconds_per_cycle"] * 1e6)
        ax.plot(
            xs, a, "o-", color=BLUE, label="simulator" if lang == "en" else "仿真器"
        )
        ax.plot(
            xs,
            b,
            "s-",
            color=ORANGE,
            label="generated Python" if lang == "en" else "生成的 Python",
        )
        ax.set_yscale("log")
        if name != "T":
            ax.set_xscale("log")
        ax.set_xlabel(L[name][lang])
        ax.set_title(
            ("median ratio %.1f×" if lang == "en" else "中位数之比 %.1f 倍")
            % float(np.median(a / b)),
            fontsize=8,
        )
    axes[0].set_ylabel("µs per cycle" if lang == "en" else "每周期微秒数")
    axes[0].legend(fontsize=7)
    fig.tight_layout()
    return fig


def fig_c_speed_size(lang):
    """
    Generated C: time per cycle and code size against R and S.

    :param lang: ``en`` or ``zh``.
    :return: Figure.
    """
    data = [r for r in rows("e4.jsonl") if r.get("part") == "speed"]
    fig, axes = plt.subplots(2, 2, figsize=(9, 6))
    for col, name in enumerate(("R", "S")):
        xs, ns = sweep(data, name, name, "ns_per_cycle")
        _, text = sweep(data, name, name, "text")
        axes[0][col].plot(xs, ns, "o-", color=BLUE)
        axes[1][col].plot(xs, text, "o-", color=ORANGE)
        slope = np.polyfit(np.log(xs), np.log(ns), 1)[0]
        axes[0][col].set_title(
            ("log-log slope %.2f" if lang == "en" else "对数坐标斜率 %.2f") % slope,
            fontsize=8,
        )
        for ax in (axes[0][col], axes[1][col]):
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_xlabel(L[name][lang])
    axes[0][0].set_ylabel(
        "ns per cycle (min of runs)" if lang == "en" else "每周期纳秒数（多次取最小）"
    )
    axes[1][0].set_ylabel(".text bytes" if lang == "en" else ".text 字节数")
    fig.tight_layout()
    return fig


def fig_c_capacity(lang):
    """
    Generated C: capacity macros and ``sizeof`` against model size.

    :param lang: ``en`` or ``zh``.
    :return: Figure.
    """
    cap = [r for r in rows("e4.jsonl") if r.get("part") == "capacity"]
    speed = [r for r in rows("e4.jsonl") if r.get("part") == "speed"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6))
    ax = axes[0]
    for D, marker in ((1, "o"), (2, "s"), (4, "^")):
        pts = sorted(
            (r["counts"]["regions"], r["arena_capacity"])
            for r in cap
            if r["model"]["D"] == D and r["model"]["S"] == 8
        )
        ax.plot(*zip(*pts), marker + "-", color=BLUE, label="D=%d" % D)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("regions in the model" if lang == "en" else "模型中的区域总数")
    ax.set_ylabel("ARENA_CAPACITY")
    ax.legend(fontsize=7)
    ax.set_title(
        "(a) " + ("default arena capacity" if lang == "en" else "默认的 arena 容量"),
        fontsize=9,
    )
    ax = axes[1]
    for S, color in ((3, GREEN), (8, BLUE), (32, ORANGE)):
        pts = sorted(
            (r["model"]["R"], r["trail_capacity"])
            for r in cap
            if r["model"]["D"] == 1 and r["model"]["S"] == S
        )
        ax.plot(*zip(*pts), "o-", color=color, label="S=%d" % S)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(L["R"][lang])
    ax.set_ylabel("TRAIL_CAPACITY")
    ax.legend(fontsize=7)
    ax.set_title(
        "(b) " + ("default trail capacity" if lang == "en" else "默认的 trail 容量"),
        fontsize=9,
    )
    ax = axes[2]
    xs, sz = sweep(speed, "R", "R", "sizeof_machine")
    ax.plot(xs, sz / 1024.0, "o-", color=ORANGE)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(L["R"][lang])
    ax.set_ylabel(
        "sizeof(machine) [KiB]" if lang == "en" else "单个机器的 sizeof [KiB]"
    )
    ax.set_title(
        "(c) " + ("RAM of one machine" if lang == "en" else "单个机器的内存"),
        fontsize=9,
    )
    fig.tight_layout()
    return fig


def fig_first_cycle_engines(lang):
    """
    First-cycle time of nested owners in the simulator, Python and C.

    :param lang: ``en`` or ``zh``.
    :return: Figure.
    """
    fig, ax = plt.subplots(figsize=(5.6, 3.8))
    xs, sim = sweep(
        rows("e2.jsonl"), "D_chain", "D", lambda r: r["first_cycle"]["min"] * 1e9
    )
    ax.plot(xs, sim, "o-", color=BLUE, label="simulator" if lang == "en" else "仿真器")
    xs, py = sweep(
        rows("e3.jsonl"), "D_chain", "D", lambda r: r["first_cycle"]["min"] * 1e9
    )
    ax.plot(
        xs,
        py,
        "s-",
        color=ORANGE,
        label="generated Python" if lang == "en" else "生成的 Python",
    )
    c = [r for r in rows("e4.jsonl") if r.get("part") == "speed"]
    xs, cc = sweep(c, "D_chain", "D", "first_cycle_ns")
    ax.plot(
        xs, cc, "^-", color=GREEN, label="generated C" if lang == "en" else "生成的 C"
    )
    ax.set_yscale("log")
    ax.set_xlabel(L["D"][lang])
    ax.set_ylabel("ns, first cycle" if lang == "en" else "第一个周期的纳秒数")
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig


def fig_c_baseline(lang):
    """
    Generated C: earlier template against the current one on region-free rings.

    :param lang: ``en`` or ``zh``.
    :return: Figure.
    """
    data = rows("e4_baseline.jsonl")
    ns = sorted({r["n"] for r in data})
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4))
    for ax, key, title in (
        (axes[0], "ns_per_cycle", "ns per cycle" if lang == "en" else "每周期纳秒数"),
        (axes[1], "text", ".text bytes" if lang == "en" else ".text 字节数"),
        (
            axes[2],
            "sizeof_machine",
            "sizeof(machine) bytes" if lang == "en" else "单机 sizeof 字节数",
        ),
    ):
        width = 0.38
        for shift, tag, color, label in (
            (-width / 2, "old", GRAY, "earlier template" if lang == "en" else "旧模板"),
            (
                width / 2,
                "new",
                BLUE,
                "current template" if lang == "en" else "当前模板",
            ),
        ):
            vals = [
                next(r[key] for r in data if r["n"] == n and r["template"] == tag)
                for n in ns
            ]
            ax.bar(np.arange(len(ns)) + shift, vals, width, color=color, label=label)
        ax.set_xticks(np.arange(len(ns)))
        ax.set_xticklabels(["%d" % n for n in ns])
        ax.set_xlabel(
            "sibling states in the ring" if lang == "en" else "环中的同级状态数"
        )
        ax.set_title(title, fontsize=9)
        ax.set_ylim(top=ax.get_ylim()[1] * 1.3)
    axes[0].legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    return fig


FIGURES = {
    "model_size": fig_model_size,
    "sim_sweeps": fig_sim_sweeps,
    "depth": fig_depth,
    "python_vs_simulator": fig_python_vs_simulator,
    "c_speed_size": fig_c_speed_size,
    "c_capacity": fig_c_capacity,
    "first_cycle_engines": fig_first_cycle_engines,
    "c_baseline": fig_c_baseline,
}


def main(name, lang):
    """
    Command line entry used by every ``fig_*.plot.py`` script.

    :param name: Figure name, a key of :data:`FIGURES`.
    :type name: str
    :param lang: ``en`` or ``zh``.
    :type lang: str
    :return: ``None``.
    :rtype: None
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args()
    setup(lang)
    fig = FIGURES[name](lang)
    save(fig, args.output, lang)


if __name__ == "__main__":
    sys.exit("run one of the fig_*.plot.py scripts")
