"""Guard the public inspect/BMC payloads against version-marker drift."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_FIELDS = frozenset({
    "schema_version",
    "schema_status",
    "product_version",
    "payload_version",
    "schemaVersion",
    "productVersion",
    "payloadVersion",
})
SCHEMA_PATHS = (
    ROOT / "pyfcstm" / "diagnostics" / "schema.json",
    ROOT / "pyfcstm" / "diagnostics" / "inspect_llm_report_schema.json",
    ROOT / "docs" / "source" / "reference" / "bmc_results" / "bmc_cli.schema.json",
)


def _forbidden_paths(value: Any, path: str = "$",) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in FORBIDDEN_FIELDS:
                yield child_path
            yield from _forbidden_paths(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _forbidden_paths(child, f"{path}[{index}]")


def _assert_clean(payload: Any, label: str) -> None:
    paths = list(_forbidden_paths(payload))
    if paths:
        raise SystemExit(
            f"{label} contains forbidden public version markers: {', '.join(paths)}",
        )


def _assert_text_clean(text: str, label: str) -> None:
    """Reject structured version keys in non-JSON inspect renderings."""
    matches = [
        field
        for field in FORBIDDEN_FIELDS
        if any(
            re.search(pattern, text)
            for pattern in (
                rf'"{re.escape(field)}"',
                rf"(?m)^\s*-\s+{re.escape(field)}\s:",
            )
        )
    ]
    if matches:
        raise SystemExit(
            f"{label} contains forbidden public version markers: {', '.join(sorted(matches))}",
        )


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        # OSError identifies an unreadable contract file; JSONDecodeError
        # identifies malformed JSON before any public payload is exercised.
        raise SystemExit(f"cannot read JSON contract {path}: {error}") from error


def main() -> int:
    for path in SCHEMA_PATHS:
        schema = _load_json(path)
        _assert_clean(schema, str(path.relative_to(ROOT)))
        if "$schema" not in schema or "$id" not in schema:
            raise SystemExit(f"{path} must retain standard $schema and $id metadata")

    sys.path.insert(0, str(ROOT))
    from pyfcstm.entry.bmc import build_bmc_output
    from pyfcstm.entry.inspect import build_inspect_json, build_inspect_output

    with TemporaryDirectory(prefix="pyfcstm-public-contract-") as temp_dir:
        temp = Path(temp_dir)
        model_path = temp / "model.fcstm"
        query_path = temp / "query.fbmcq"
        model_path.write_text(
            "state Root { state Idle; [*] -> Idle; }\n",
            encoding="utf-8",
        )
        query_path.write_text(
            'check reach <= 1: active("Root");\n',
            encoding="utf-8",
        )
        inspect_payload = json.loads(build_inspect_json(str(model_path)))
        _assert_clean(inspect_payload, "pyfcstm inspect payload")
        for output_format in ("human", "llm-json", "llm-md"):
            rendered = build_inspect_output(
                str(model_path),
                output_format=output_format,
                color_enabled=False,
            )
            if output_format == "llm-json":
                _assert_clean(
                    json.loads(rendered),
                    "pyfcstm inspect llm-json payload",
                )
            else:
                _assert_text_clean(
                    rendered,
                    f"pyfcstm inspect {output_format} output",
                )
        bmc_text, _exit_code = build_bmc_output(
            str(model_path),
            str(query_path),
            json_output=True,
        )
        _assert_clean(json.loads(bmc_text), "pyfcstm bmc payload")
    print("public inspect/BMC payload contract has no version markers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
