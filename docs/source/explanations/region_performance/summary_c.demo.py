from perf_summary_common import fits, median, provenance, rows, series

all_rows = rows("e4.jsonl")
speed = [r for r in all_rows if r["part"] == "speed"]
cap = [r for r in all_rows if r["part"] == "capacity"]
base = rows("e4_baseline.jsonl")
py = rows("e3.jsonl")
print("measured on:", provenance(speed, extra="gcc"), "(-O2 -std=c99, pinned to one core)")
print("each point: minimum of %d runs of %d+ cycles" % (speed[0]["repeats"], 2000))
print()
for sweep, axis in (("R", "R"), ("S", "S"), ("T", "T"), ("V", "V"), ("D_chain", "D")):
    ns = series(speed, sweep, axis, "ns_per_cycle")
    text = dict(series(speed, sweep, axis, "text"))
    size = dict(series(speed, sweep, axis, "sizeof_machine"))
    first = dict(series(speed, sweep, axis, "first_cycle_ns"))
    print("%s sweep (%s): ns per cycle | .text bytes | sizeof bytes | first cycle us" % (sweep, axis))
    for x, y in ns:
        print("  %s=%-3d %8.1f | %7d | %9d | %9.1f" % (axis, x, y, text[x], size[x], first[x] / 1e3))
    f = fits()["e4/" + sweep]
    print("  power exponent of ns per cycle %.2f (R2 %.3f); quadratic R2 %.4f; linear R2 %.3f" % (
        f["power"]["exponent"], f["power"]["r2"], f["quadratic"]["r2"], f["linear"]["r2"]))
    print()
print("the base model R=4 S=8 T=2 D=1 V=1 appears in several sweeps; its ns per cycle:")
same = [r["ns_per_cycle"] for r in speed if r["model"] == {"R": 4, "S": 8, "T": 2, "D": 1, "V": 1}]
print("  " + " ".join("%.1f" % v for v in same) + "  (spread %.0f%%)" % (100 * (max(same) / min(same) - 1)))
print()
print("generated Python / generated C time per cycle, same model:")
for sweep, axis in (("R", "R"), ("S", "S"), ("T", "T"), ("V", "V")):
    c = dict(series(speed, sweep, axis, "ns_per_cycle"))
    p = dict(series(py, sweep, axis, lambda r: r["seconds_per_cycle"] * 1e9))
    ratios = [p[x] / c[x] for x in c]
    print("  %s sweep: median %.0fx, min %.0fx, max %.0fx" % (sweep, median(ratios), min(ratios), max(ratios)))
print()
print("default capacity macros against the model size (scopes = all states + regions):")
ok_arena = ok_trail = 0
for r in cap:
    scopes = r["counts"]["all_states"] + r["counts"]["regions"]
    ok_arena += r["arena_capacity"] == max(24, 12 * scopes)
    ok_trail += r["trail_capacity"] == 16 + 4 * scopes
print("  %d models: ARENA_CAPACITY == max(24, 12*scopes) in %d, TRAIL_CAPACITY == 16 + 4*scopes in %d" % (len(cap), ok_arena, ok_trail))
for r in sorted(cap, key=lambda r: r["counts"]["regions"]):
    m = r["model"]
    if m["S"] == 8 and m["D"] in (1, 4) and m["R"] in (1, 8, 64):
        scopes = r["counts"]["all_states"] + r["counts"]["regions"]
        print("  D=%d S=%d R=%-2d scopes=%-4d ARENA_CAPACITY=%-6d TRAIL_CAPACITY=%d" % (
            m["D"], m["S"], m["R"], scopes, r["arena_capacity"], r["trail_capacity"]))
print()
print("region-free ring, earlier template vs current template:")
for n in sorted({r["n"] for r in base}):
    old = next(r for r in base if r["n"] == n and r["template"] == "old")
    new = next(r for r in base if r["n"] == n and r["template"] == "new")
    print("  n=%-3d ns/cycle %6.1f -> %6.1f | .text %6d -> %6d | sizeof %5d -> %5d" % (
        n, old["ns_per_cycle"], new["ns_per_cycle"], old["text"], new["text"],
        old["sizeof_machine"], new["sizeof_machine"]))
