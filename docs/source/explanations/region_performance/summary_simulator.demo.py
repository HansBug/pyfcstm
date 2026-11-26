from perf_summary_common import fits, provenance, rows, series

data = rows("e2.jsonl")
print("measured on:", provenance(data))
print("each point: median of %d timed batches after a warm-up; first cycle: minimum of fresh runs" % data[0]["repeats"])
print("base model: R=4 S=8 T=2 D=1 V=1; one parameter changes per sweep")
print()
fit = fits()
for sweep, axis in (("R", "R"), ("S", "S"), ("T", "T"), ("V", "V"), ("D_chain", "D"), ("D_branch", "D")):
    pts = series(data, sweep, axis, lambda r: r["seconds_per_cycle"] * 1e6)
    first = series(data, sweep, axis, lambda r: r["first_cycle"]["min"] * 1e6)
    print("%s sweep (%s): us per cycle / first cycle us" % (sweep, axis))
    print("  " + "  ".join("%s=%d: %.0f/%.0f" % (axis, x, y, f) for (x, y), (_, f) in zip(pts, first)))
    f = fit["e2/" + sweep]
    quad = f["quadratic"]["coefficients"]
    print("  linear R2 %.4f, slope %.3f us per unit | quadratic R2 %.4f, x^2 term %.4f us | power exponent %.2f (R2 %.3f)" % (
        f["linear"]["r2"], f["linear"]["slope"] * 1e6, f["quadratic"]["r2"], quad[2] * 1e6,
        f["power"]["exponent"], f["power"]["r2"]))
    print()
