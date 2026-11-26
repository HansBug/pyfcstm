from perf_summary_common import fits, median, provenance, rows, series

sim, gen = rows("e2.jsonl"), rows("e3.jsonl")
print("measured on:", provenance(gen))
print("each point: median of %d timed batches; same models and same input sequence as the simulator" % gen[0]["repeats"])
print()
allratios = []
for sweep, axis in (("R", "R"), ("S", "S"), ("T", "T"), ("V", "V"), ("D_chain", "D"), ("D_branch", "D")):
    a = series(sim, sweep, axis, lambda r: r["seconds_per_cycle"] * 1e6)
    b = series(gen, sweep, axis, lambda r: r["seconds_per_cycle"] * 1e6)
    ratios = [x[1] / y[1] for x, y in zip(a, b)]
    allratios += ratios
    print("%s sweep (%s): generated Python us per cycle, and simulator/generated ratio" % (sweep, axis))
    print("  " + "  ".join("%s=%d: %.0f (%.1fx)" % (axis, x[0], y[1], q) for x, y, q in zip(a, b, ratios)))
    f = fits()["e3/" + sweep]
    print("  linear R2 %.4f | quadratic R2 %.4f, x^2 term %.4f us" % (
        f["linear"]["r2"], f["quadratic"]["r2"], f["quadratic"]["coefficients"][2] * 1e6))
print()
print("ratio over all %d points: median %.1f, min %.1f, max %.1f" % (
    len(allratios), median(allratios), min(allratios), max(allratios)))
print("final variables equal to the simulator's after 1024 cycles: %d of %d points" % (
    sum(1 for r in gen if r["simulator_final_vars_equal"]), len(gen)))
print()
print("generated machine.py bytes and import ms, by R:")
for x, size in series(gen, "R", "R", lambda r: r["machine_bytes"]):
    imp = dict(series(gen, "R", "R", lambda r: r["import_seconds"] * 1e3))[x]
    print("  R=%d: %d bytes, %.1f ms" % (x, size, imp))
