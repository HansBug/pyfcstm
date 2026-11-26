"""Helpers shared by the summary scripts that print tables from the committed data files."""
import json
import os
import statistics

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def rows(name):
    with open(os.path.join(DATA, name)) as handle:
        return [json.loads(line) for line in handle if line.strip()]


def fits():
    with open(os.path.join(DATA, "fits.json")) as handle:
        return json.load(handle)


def provenance(records, extra=""):
    first = records[0]
    machine = first["machine"]
    parts = [
        "commit %s" % first["commit"],
        machine["cpu"],
        "Python %s" % machine["python"],
    ]
    if extra and machine.get("gcc"):
        parts.append(machine["gcc"])
    return "; ".join(parts)


def series(records, sweep, axis, key):
    pts = sorted(
        (r["model"][axis], key(r) if callable(key) else r[key])
        for r in records
        if r["sweep"] == sweep
    )
    return pts


def median(values):
    return statistics.median(values)
