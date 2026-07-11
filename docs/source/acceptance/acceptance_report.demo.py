"""Generate reproducible acceptance evidence snippets."""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from pygments.lexers import get_lexer_by_name

from pyfcstm.diagnostics.inspect import inspect_model
from pyfcstm.dsl.error import GrammarParseError
from pyfcstm.model import load_state_machine_from_text, parse_expr_from_string
from pyfcstm.render import StateMachineCodeRenderer
from pyfcstm.template import extract_template, list_templates
from pyfcstm.utils.validate import ModelValidationError

SOURCE = Path(__file__).with_name("acceptance.fcstm")
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
TEMPLATES = ("python", "c", "c_poll", "cpp", "cpp_poll")


def _sanitize_evidence_text(text):
    replacements = (
        (str(REPOSITORY_ROOT), "<repo>"),
        (str(Path.home()), "<home>"),
        (tempfile.gettempdir(), "<tmp>"),
    )
    for source, replacement in replacements:
        text = text.replace(source, replacement)
    return text


def _run_command(args, cwd=None):
    completed = subprocess.run(
        list(args),
        cwd=str(cwd) if cwd is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "command": _sanitize_evidence_text(" ".join(str(item) for item in args)),
        "returncode": completed.returncode,
        "stdout_tail": [
            _sanitize_evidence_text(line)
            for line in completed.stdout.strip().splitlines()[-8:]
        ],
        "stderr_tail": [
            _sanitize_evidence_text(line)
            for line in completed.stderr.strip().splitlines()[-8:]
        ],
    }


def _run_pyfcstm(*args):
    return _run_command(["pyfcstm", *args])


def _print_json(label, payload):
    print("## {0}".format(label))
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _write_cmake_project(template_name, output_dir):
    if template_name in {"c", "c_poll"}:
        project_line = "project(pyfcstm_acceptance_{0} C)".format(template_name)
        add_library = "add_library(machine STATIC machine.c)"
    else:
        project_line = "project(pyfcstm_acceptance_{0} C CXX)".format(template_name)
        add_library = "add_library(machine STATIC machine.c machine.cpp)"
    cmake_text = "\n".join(
        [
            "cmake_minimum_required(VERSION 3.5)",
            project_line,
            add_library,
            "target_include_directories(machine PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})",
            "",
        ]
    )
    (output_dir / "CMakeLists.txt").write_text(cmake_text, encoding="utf-8")


def _build_native_template(template_name, output_dir):
    cmake = shutil.which("cmake")
    if cmake is None:
        return {"available": False, "reason": "cmake not found"}
    _write_cmake_project(template_name, output_dir)
    build_dir = output_dir / "build"
    build_dir.mkdir()
    configure = _run_command([cmake, ".."], cwd=build_dir)
    if configure["returncode"] != 0:
        return {"available": True, "configure": configure, "build": None}
    build = _run_command([cmake, "--build", ".", "--config", "Release"], cwd=build_dir)
    return {"available": True, "configure": configure, "build": build}


def main():
    source_text = SOURCE.read_text(encoding="utf-8")
    model = load_state_machine_from_text(source_text, path=str(SOURCE))
    report = inspect_model(model).to_json()
    _print_json(
        "inspect-json-summary",
        {
            "diagnostics": len(report.get("diagnostics", [])),
            "state_count": len(report.get("states", [])),
            "transition_count": len(report.get("transitions", [])),
        },
    )

    try:
        load_state_machine_from_text("state Broken { state A;", path="syntax-demo.fcstm")
    except GrammarParseError as error:
        # GrammarParseError: load_state_machine_from_text reports malformed FCSTM syntax.
        first = error.errors[0]
        _print_json(
            "syntax-diagnostic",
            {
                "line": first.line,
                "column": first.column,
                "message": first.msg,
                "raw": first.raw_msg,
            },
        )

    try:
        load_state_machine_from_text(
            "state Root { state A; [*] -> Missing; }",
            path="structure-demo.fcstm",
        )
    except ModelValidationError as error:
        # ModelValidationError: model validation rejects a dangling transition target.
        diagnostic = error.diagnostics[0]
        _print_json(
            "structure-diagnostic",
            {
                "code": diagnostic.code,
                "severity": diagnostic.severity,
                "message": diagnostic.message,
            },
        )

    with tempfile.TemporaryDirectory(prefix="pyfcstm-acceptance-generate-") as directory:
        root = Path(directory)
        generated = {}
        native = {}
        for template_name in TEMPLATES:
            template_dir = root / "template" / template_name
            output_dir = root / "generated" / template_name
            extracted_template = extract_template(template_name, str(template_dir))
            StateMachineCodeRenderer(extracted_template).render(
                model,
                str(output_dir),
                clear_previous_directory=True,
            )
            generated[template_name] = sorted(path.name for path in output_dir.iterdir())
            if template_name in {"c", "c_poll", "cpp", "cpp_poll"}:
                native[template_name] = _build_native_template(template_name, output_dir)
        _print_json("five-template-generation", generated)
        _print_json("cmake-native-evidence", native)

    rc_data = _run_pyfcstm("simulate", "-i", str(SOURCE), "-e", "cycle; current")
    _print_json("cli-simulation", rc_data)
    plantuml_data = _run_pyfcstm("plantuml", "-i", str(SOURCE), "--level", "normal")
    _print_json("cli-plantuml", plantuml_data)
    _print_json("template-list", {"templates": list_templates()})

    lexer = get_lexer_by_name("fcstm")
    _print_json(
        "pygments-entry-point",
        {
            "aliases": list(lexer.aliases),
            "filenames": list(lexer.filenames),
            "class": "{0}.{1}".format(type(lexer).__module__, type(lexer).__name__),
        },
    )

    java_path = shutil.which("java")
    antlr_jar = Path(__file__).resolve().parents[3] / "antlr-4.9.3.jar"
    java_evidence = {
        "java": _run_command([java_path, "-version"]) if java_path else {"returncode": None, "stderr_tail": ["java not found"]},
        "antlr_jar_exists": antlr_jar.is_file(),
        "antlr_jar": antlr_jar.name,
    }
    _print_json("java-jar-prerequisite", java_evidence)

    parse_expr_from_string("temperature > 100 && enabled == 1", mode="logical")
    parse_expr_from_string("counter + 1", mode="numeric")
    try:
        parse_expr_from_string("temperature > (100 &&", mode="logical")
    except GrammarParseError as error:
        # GrammarParseError: parse_expr_from_string reports invalid GUI formula text.
        _print_json("formula-error", {"message": error.errors[0].msg})
    load_state_machine_from_text(
        """
        def int counter = 0;
        state Root {
            state Active {
                during { counter = counter + 1; }
            }
            [*] -> Active;
        }
        """
    )
    _print_json("formula-smoke", {"logical": "ok", "numeric": "ok", "action": "ok"})


if __name__ == "__main__":
    main()
