from perf_summary_common import rows

data = rows("e1.jsonl")
products = [r for r in data if r["kind"] == "product"]
print("measured on:", data[0]["commit"], "|", data[0]["machine"]["cpu"], "| Python", data[0]["machine"]["python"])
print("each pair was run for %d cycles on %d random input sequences; timing is the median of %d batches"
      % (products[0]["cycles"], products[0]["seeds"], products[0]["repeats"]))
print()
print(" R  S  T | leaf states        | transitions            | formula | same vars | ms per cycle")
print("         |  regions    flat   |  regions        flat   | matches |           |  regions   flat")
for r in sorted(products, key=lambda r: (r["model"]["T"], r["model"]["S"], r["model"]["R"])):
    m = r["model"]
    formula = (
        r["formula_region_states"] == r["region_leaf_states"]
        and r["formula_flat_states"] == r["flat_leaf_states"]
        and r["formula_region_transitions"] == r["region_transitions"]
        and r["formula_flat_transitions"] == r["flat_transitions"]
    )
    print("%2d %2d %2d | %8d %7d   | %8d %11d   | %-7s | %-9s | %7.2f %7.2f" % (
        m["R"], m["S"], m["T"], r["region_leaf_states"], r["flat_leaf_states"],
        r["region_transitions"], r["flat_transitions"], formula, r["equivalent"],
        r["region_seconds_per_cycle"] * 1e3, r["flat_seconds_per_cycle"] * 1e3))
print()
print("coupled models (leaf states, transitions):")
for r in data:
    if r["kind"] == "coupled":
        print("  %-30s %d, %d" % (r["label"], r["counts"]["leaf_states"], r["counts"]["transitions"]))
print()
print("cycles with different variables, out of %d compared:" % next(r for r in data if r["kind"] == "coupled_compare")["compared_cycles"])
for r in data:
    if r["kind"] == "coupled_compare":
        print("  %-30s vs %-30s %4d (first at cycle: %s)" % (
            r["label"], r["reference"], r["cycles_with_different_variables"], "none" if r["first_difference_cycle"] is None else r["first_difference_cycle"]))
