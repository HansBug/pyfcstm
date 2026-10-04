"""Rebuild the diagnostic summary from immutable raw samples, without solving."""

import collections
import json
from pathlib import Path
import statistics


def summarize(root):
    summary = {}
    for name in ("macro_cache", "corpus", "scaling", "sat_probes"):
        directory = root / name
        manifest = json.loads((directory / "manifest.json").read_text())
        rows = [
            json.loads(line)
            for line in (directory / "raw.jsonl").read_text().splitlines()
        ]
        assert len(rows) == len(manifest["specs"]), name
        references, groups = {}, collections.defaultdict(list)
        for spec, row in zip(manifest["specs"], rows):
            assert all(row[key] == value for key, value in spec.items())
            key = (
                row["case"],
                row["query"],
                row.get("bound"),
                row.get("cone_slicing", False),
            )
            contract = {
                field: row[field]
                for field in (
                    "input_sha256",
                    "status",
                    "outcome",
                    "property_satisfied",
                    "replay_ok",
                    "partition_count",
                    "partition_assignments",
                )
            }
            contract["fingerprints"] = {
                key: value
                for key, value in row["fingerprints"].items()
                if key != "witness"
            }
            if key not in references:
                assert row["arm"] == "baseline"
                references[key] = contract
            assert contract == references[key], (name, key, row["arm"])
            assert row["replay_ok"] is not False
            assert row["status"] != "sat" or row["replay_ok"] is True
            if not row.get("profile"):
                groups[key + (row["arm"],)].append(row)
        measurements = []
        for key, samples in groups.items():
            ordered = sorted(samples, key=lambda row: row["call_ms"])
            representative = ordered[len(ordered) // 2]
            times = [row["call_ms"] for row in samples]
            memories = [
                row["peak_rss_bytes"]
                for row in samples
                if row["peak_rss_bytes"] is not None
            ]
            measurements.append(
                dict(
                    case=key[0],
                    query=key[1],
                    bound=key[2],
                    cone_slicing=key[3],
                    arm=key[4],
                    n=len(samples),
                    p50_ms=statistics.median(times),
                    min_ms=min(times),
                    max_ms=max(times),
                    rss_p50_bytes=statistics.median(memories) if memories else None,
                    representative_phases_ms=representative["phases_ms"],
                    representative_cache=representative["cache"],
                    representative_sat_cache=representative.get("sat_cache"),
                    partition_count=representative["partition_count"],
                    partition_assignments=representative["partition_assignments"],
                )
            )
        summary[name] = dict(
            records=len(rows),
            ordinary_records=sum(not row.get("profile") for row in rows),
            sat_records=sum(row["status"] == "sat" for row in rows),
            witness_differences=sum(
                row.get("witness_matches_baseline") is False for row in rows
            ),
            measurements=measurements,
        )
        if name == "corpus":
            baseline = [row for row in rows if row["arm"] == "baseline"]
            phases = collections.Counter()
            for row in baseline:
                phases.update(row["phases_ms"])
            summary[name]["baseline_phase_totals_ms"] = dict(phases)
            summary[name]["baseline_call_total_ms"] = sum(
                row["call_ms"] for row in baseline
            )
            summary[name]["baseline_dominant_phases"] = dict(
                collections.Counter(
                    max(row["phases_ms"], key=row["phases_ms"].get) for row in baseline
                )
            )
    return summary


if __name__ == "__main__":
    print(json.dumps(summarize(Path(__file__).parent), indent=2, sort_keys=True))
