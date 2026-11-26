"""Shared drawing code for the BMC scaling figures.

Every ``*.plot.py`` next to this file reads the committed JSON Lines files in
``data/`` and calls :func:`render` with a figure name and a language.  Latin
text is laid out with DejaVu Sans (bundled with matplotlib) and Chinese text with
the SimHei file the repository ships in ``docs/source/_libs``, so layout never
depends on the fonts installed on the machine.  Text stays text in the SVG, which
names a browser-friendly font stack, carries no date and uses a fixed hash salt.
"""

import argparse
import io
import json
import math
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as font_manager  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

DATA = Path(__file__).resolve().parent / "data"
BLUE, ORANGE, GREEN, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#52514e"
STACKS = {
    "en": "'DejaVu Sans', sans-serif",
    "zh": "'DejaVu Sans', 'Noto Sans CJK SC', 'Microsoft YaHei', 'PingFang SC', 'Droid Sans Fallback', sans-serif",
}
SIMHEI = Path(__file__).resolve().parents[2] / "_libs" / "SimHei.ttf"

TEXT = {
    "en": {
        "n_states": "leaf states N (T=2, k=5)",
        "seconds": "seconds",
        "compile": "build formula",
        "solve": "solve",
        "total": "total (dashed)",
        "regions_r": "regions R (S=4, k=3)",
        "regions_s": "states per region S (R=4, k=3)",
        "bound_k": "bound k (N=400)",
        "phase_title": "Share of time spent building the formula",
        "phase_flat": "region-free machines",
        "phase_regions": "machines with regions",
        "total_s": "build + solve (seconds, log axis)",
        "compile_pct": "build share of total (%)",
        "nodes_meas": "measured nodes",
        "nodes_pred": "closed form",
        "nodes_title": "Formula size: closed form vs measurement",
        "flat_title": "Region-free machines",
        "region_title": "Machines with regions",
        "fit_x": "propagations reported by z3",
        "fit_y": "solver seconds of the main check",
        "fit_title": "Solve time follows propagations",
        "fit_line": "dashed: %.0f ns per propagation",
        "php_x": "mutually exclusive regions",
        "php_unsat": "exclusive (unsat)",
        "php_sat": "same shape, satisfiable",
        "php_to": "x: not decided in 280 s",
        "php_title": "Worst case: exclusive regions",
        "loglog": "log-log axes",
        "logy": "log y axis",
        "formula_nodes": "formula nodes",
        "constructed_s": "measured build seconds",
    },
    "zh": {
        "n_states": "叶子状态数 N（T=2，k=5）",
        "seconds": "秒",
        "compile": "构造公式",
        "solve": "求解",
        "total": "总计（虚线）",
        "regions_r": "区域数 R（S=4，k=3）",
        "regions_s": "每个区域的状态数 S（R=4，k=3）",
        "bound_k": "步数上界 k（N=400）",
        "phase_title": "构造公式占总耗时的比例",
        "phase_flat": "不含区域的状态机",
        "phase_regions": "含区域的状态机",
        "total_s": "构造加求解（秒，对数坐标）",
        "compile_pct": "构造占总耗时的比例（%）",
        "nodes_meas": "实测节点数",
        "nodes_pred": "闭式",
        "nodes_title": "公式规模：闭式与实测",
        "flat_title": "不含区域的状态机",
        "region_title": "含区域的状态机",
        "fit_x": "z3 报告的传播次数",
        "fit_y": "主检查的求解秒数",
        "fit_title": "求解耗时跟随传播次数",
        "fit_line": "虚线：每次传播 %.0f 纳秒",
        "php_x": "互斥的区域个数",
        "php_unsat": "互斥（不可满足）",
        "php_sat": "同样结构，可满足",
        "php_to": "x：280 秒内未判定",
        "php_title": "最坏情形：互斥区域",
        "loglog": "双对数坐标",
        "logy": "纵轴对数坐标",
        "formula_nodes": "公式节点数",
        "constructed_s": "实测构造秒数",
    },
}


def rows(name):
    """Read one JSON Lines file of ``data/`` without the failed records."""
    with (DATA / name).open(encoding="utf-8") as handle:
        return [
            r for r in map(json.loads, filter(str.strip, handle)) if "error" not in r
        ]


def sweep(records, family, key, **fixed):
    """Return ``(x, compile_s, solve_s)`` of one sweep of finished unsat points.

    Duplicate configurations are collapsed to their median.  Records of other
    sweeps are excluded: calls, written variables and explicit ``T`` are only
    kept when they are the swept parameter or a fixed one.
    """
    grouped = {}
    for r in records:
        cfg = r["cfg"]
        params = cfg["params"]
        if cfg["family"] != family or cfg["kind"] != "unsat" or "error" in r:
            continue
        if r.get("status") != "unsat" or "t_solve" not in r:
            continue
        if params.get("calls") or params.get("eff") is False:
            continue
        for extra in ("V", "T"):
            if extra in params and extra != key and extra not in fixed:
                if extra == "V" or params[extra] != 2:
                    break
        else:
            ok = True
            for name, value in fixed.items():
                have = (
                    cfg["k"]
                    if name == "k"
                    else params.get(name, 2 if name == "T" else None)
                )
                ok = ok and have == value
            if ok:
                x = cfg["k"] if key == "k" else params[key]
                grouped.setdefault(x, []).append((r["t_compile"], r["t_solve"]))
    out = []
    for x, vals in grouped.items():
        vals.sort(key=sum)
        mid = vals[len(vals) // 2]
        out.append((x, mid[0], mid[1]))
    return sorted(out)


def retest(key, family, **fixed):
    """Return ``(x, total_s)`` of the retest points of one sweep."""
    return [
        (x, c + s_) for x, c, s_ in sweep(rows("timing.jsonl"), family, key, **fixed)
    ]


def _style(ax, xlabel, ylabel, title, logx=True, logy=True):
    if logx:
        ax.set_xscale("log")
    if logy:
        ax.set_yscale("log")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=11)
    ax.grid(True, color="#e4e3df", linewidth=0.6)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def _curves(ax, pts, t, show_labels, extra=()):
    xs = [p[0] for p in pts]
    total = [p[1] + p[2] for p in pts]
    ax.plot(xs, [p[1] for p in pts], "-o", color=BLUE, ms=4, lw=1.5)
    ax.plot(xs, [p[2] for p in pts], "-s", color=ORANGE, ms=4, lw=1.5)
    ax.plot(xs, total, "--", color=GREY, lw=1)
    if extra:
        ax.plot(
            [e[0] for e in extra],
            [e[1] for e in extra],
            "x",
            color="black",
            ms=6,
            mew=1.5,
        )
    if show_labels:
        for row, (text, color) in enumerate(
            ((t["compile"], BLUE), (t["solve"], ORANGE), (t["total"], GREY))
        ):
            ax.text(
                0.04,
                0.93 - 0.075 * row,
                text,
                transform=ax.transAxes,
                color=color,
                fontsize=8,
                ha="left",
            )


def fig_time_flat(t):
    timing = rows("original_measurements.jsonl")
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    specs = (
        ("N", {"k": 5, "T": 2}, t["n_states"]),
        ("k", {"N": 400, "T": 2}, t["bound_k"]),
        ("T", {"N": 100, "k": 5}, "T (N=100, k=5)"),
    )
    for ax, (key, fixed, label) in zip(axes, specs):
        pts = sweep(timing, "flat", key, **fixed)
        _curves(ax, pts, t, True, retest(key, "flat", **fixed))
        _style(ax, label, t["seconds"], t["flat_title"])
    return fig


def fig_time_regions(t):
    timing = rows("original_measurements.jsonl")
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    specs = (
        ("R", {"S": 4, "k": 3}, t["regions_r"]),
        ("S", {"R": 4, "k": 3}, t["regions_s"]),
        ("k", {"R": 4, "S": 40}, "k (R=4, S=40)"),
    )
    for ax, (key, fixed, label) in zip(axes, specs):
        pts = sweep(timing, "regions", key, **fixed)
        _curves(ax, pts, t, True, retest(key, "regions", **fixed))
        _style(ax, label, t["seconds"], t["region_title"])
    return fig


def fig_phases(t):
    timing = rows("original_measurements.jsonl")
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for family, color, label, row in (
        ("flat", BLUE, t["phase_flat"], 0),
        ("regions", ORANGE, t["phase_regions"], 1),
    ):
        pts = []
        for r in timing:
            if r["cfg"]["family"] == family and r.get("status") in ("sat", "unsat"):
                total = r["t_compile"] + r["t_solve"]
                if total > 1.0:
                    pts.append((total, r["t_compile"] / total * 100))
        ax.scatter(
            [p[0] for p in pts], [p[1] for p in pts], s=14, color=color, alpha=0.7
        )
        ax.text(
            0.04,
            0.12 - 0.07 * row,
            label,
            transform=ax.transAxes,
            color=color,
            fontsize=8.5,
            ha="left",
        )
    ax.set_xscale("log")
    ax.set_ylim(0, 100)
    _style(ax, t["total_s"], t["compile_pct"], t["phase_title"], True, False)
    return fig


def fig_nodes(t):
    grid = (
        rows("formula_grid.jsonl")
        + rows("timing.jsonl")
        + rows("original_measurements.jsonl")
    )
    fig, ax = plt.subplots(figsize=(6, 4.6))
    xs, ys = [], []
    for r in grid:
        cfg, p = r["cfg"], r["cfg"]["params"]
        if (
            cfg["mode"] != "time"
            or cfg["family"] != "flat"
            or "V" in p
            or p.get("T", 2) != 2
        ):
            continue
        if cfg["kind"] != "unsat" or r.get("nodes") is None or cfg["k"] < 2:
            continue
        xs.append(r["nodes"])
        ys.append(21 * p["N"] * cfg["k"] - 18 * p["N"] + 33 * cfg["k"] + 6)
    ax.scatter(xs, ys, s=12, color=BLUE, alpha=0.7)
    lim = [min(xs), max(xs)]
    ax.plot(lim, lim, "--", color=GREY, lw=1)
    _style(ax, t["nodes_meas"], t["nodes_pred"], t["nodes_title"])
    return fig


def _regions_nodes(r, s, k):
    return 23 * r * s * k - 18 * r * s + 22.29 * r * k + 2.904 * r + 46.17 * k + 17.61


def fig_fit(t):
    law = rows("solve_law.jsonl")
    xs, ys = [], []
    for r in law:
        if r["cfg"]["mode"] != "time":
            continue
        check = r["checks"][0]
        prop = check["stats"].get("propagations", 0)
        if prop > 2e4:
            xs.append(prop)
            ys.append(check["t"])
    xs, ys = np.array(xs, float), np.array(ys)
    ns = float(np.median(ys / xs) * 1e9)
    fig, ax = plt.subplots(figsize=(6, 4.6))
    ax.scatter(xs, ys, s=14, color=GREEN, alpha=0.7)
    line = np.array([xs.min(), xs.max()])
    ax.plot(line, line * ns * 1e-9, "--", color=GREY, lw=1)
    ax.text(
        0.04,
        0.92,
        t["fit_line"] % ns,
        transform=ax.transAxes,
        color=GREY,
        fontsize=9,
        ha="left",
    )
    _style(ax, t["fit_x"], t["fit_y"], t["fit_title"])
    return fig


def fig_pigeonhole(t):
    php = rows("pigeonhole.jsonl")
    unsat = sorted(
        (r["cfg"]["params"]["pigeons"], r["t_solve"], r["status"])
        for r in php
        if r["cfg"]["kind"] == "unsat"
    )
    sat = sorted(
        (r["cfg"]["params"]["pigeons"], r["t_solve"])
        for r in php
        if r["cfg"]["kind"] == "sat"
    )
    fig, ax = plt.subplots(figsize=(6, 4.6))
    done = [u for u in unsat if u[2] == "unsat"]
    ax.plot(
        [u[0] for u in done], [u[1] for u in done], "-o", color=ORANGE, ms=4, lw=1.6
    )
    open_ = [u for u in unsat if u[2] != "unsat"]
    ax.plot(
        [u[0] for u in open_], [u[1] for u in open_], "x", color=ORANGE, ms=8, mew=2
    )
    ax.plot([s[0] for s in sat], [s[1] for s in sat], "-o", color=BLUE, ms=4, lw=1.6)
    for row, (text, color) in enumerate(
        ((t["php_unsat"], ORANGE), (t["php_sat"], BLUE), (t["php_to"], ORANGE))
    ):
        ax.text(
            0.04,
            0.93 - 0.075 * row,
            text,
            transform=ax.transAxes,
            color=color,
            fontsize=8.5,
            ha="left",
        )
    _style(ax, t["php_x"], t["seconds"], t["php_title"], False, True)
    return fig


FIGURES = {
    "time_flat": fig_time_flat,
    "time_regions": fig_time_regions,
    "phases": fig_phases,
    "nodes": fig_nodes,
    "fit": fig_fit,
    "pigeonhole": fig_pigeonhole,
}


def render(name, language, argv=None):
    """Draw figure ``name`` in ``language`` and write the SVG given by ``-o``."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args(argv)
    families = ["DejaVu Sans"]
    if language == "zh":
        font_manager.fontManager.addfont(str(SIMHEI))
        families.append("SimHei")
    plt.rcParams.update(
        {
            "svg.fonttype": "none",
            "svg.hashsalt": "pyfcstm-bmc-scaling",
            "font.family": families,
            "axes.unicode_minus": False,
            "font.size": 9,
        }
    )
    fig = FIGURES[name](TEXT[language])
    fig.subplots_adjust(left=0.1, right=0.97, bottom=0.17, top=0.9, wspace=0.28)
    buffer = io.BytesIO()
    fig.savefig(buffer, format="svg", metadata={"Date": None, "Creator": None})
    svg = buffer.getvalue().decode("utf-8")
    svg = re.sub(
        r"font: ([\d.]+px) '[^;\"]*'",
        lambda m: "font: %s %s" % (m.group(1), STACKS[language]),
        svg,
    )
    Path(args.output).write_text(svg, encoding="utf-8")
    return math.nan
