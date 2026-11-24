"""
Generated C configuration code: compiled behaviour and agreement with the simulator.

Every model below is rendered through the packaged ``c`` template, so the
generated code is checked inside the real ``machine.h`` and ``machine.c``. A
small C driver exposes the generated functions over a line protocol on
stdin/stdout, and the simulator's
:class:`pyfcstm.model.Configuration` is the oracle for every answer.
"""

import binascii
import itertools
import os
import random
import re
import shutil
import subprocess

import pytest

from pyfcstm.model import Configuration, load_state_machine_from_text
from pyfcstm.render import StateMachineCodeRenderer
from pyfcstm.render.c_configuration import (
    render_c_configuration_header,
    render_c_configuration_source,
)
from pyfcstm.template import extract_template

pytestmark = pytest.mark.unittest

LONG_OWNER = "Coordinator" + "X" * 140
LONG_REGION = "Monitoring" + "Y" * 60
MODELS = {
    "motion": """
        state Root {
            [*] -> Run;
            state Run {
                region Motion { [*] -> Stop; state Stop; state Move; Stop -> Move :: Go; }
                region Guard { [*] -> Watch; state Watch; }
            }
            state Off;
            Run -> Off :: Halt;
        }
    """,
    "nested": """
        state Plant {
            [*] -> Idle;
            state Idle;
            state Work {
                region Line {
                    [*] -> Route;
                    pseudo state Route;
                    Route -> Feed;
                    state Feed {
                        [*] -> Load;
                        state Load;
                        state Unload;
                        Load -> Unload :: Next;
                    }
                    state Cell {
                        region Arm { [*] -> Reach; state Reach; state Grip; Reach -> Grip :: Next; }
                        region Belt { [*] -> Roll; state Roll; Roll -> [*] :: Stop; }
                    }
                    Feed -> Cell :: Next;
                }
                region Audit { [*] -> Log; state Log; Log -> [*] :: Stop; }
            }
            Idle -> Work :: Start;
        }
    """,
    "deep": """
        state Deep {
            [*] -> A;
            state A {
                region R1 {
                    [*] -> B;
                    state B {
                        region R2 {
                            [*] -> C;
                            state C { region R3 { [*] -> D; state D; } }
                        }
                    }
                }
            }
        }
    """,
    "cases": """
        state Case {
            [*] -> Pair;
            state Pair {
                region R { [*] -> Alpha; state Alpha; state alpha; Alpha -> alpha :: Go; }
                region r { [*] -> Beta; state Beta; state beta; Beta -> beta :: Go; }
            }
            state pair;
            Pair -> pair :: Leave;
        }
    """,
    "hub": """
        state Hub {
            region Left { [*] -> L1; state L1; state L2; L1 -> L2 :: Go; }
            region Right { [*] -> R1; state R1; }
        }
    """,
    "lamp": "state Lamp { [*] -> Off; state Off; state On; Off -> On :: Toggle; }",
    "long": "state Station { [*] -> %s; state %s { region %s { [*] -> Leaf; state Leaf; } } }"
    % (
        LONG_OWNER,
        LONG_OWNER,
        LONG_REGION,
    ),
}

DRIVER_SOURCE = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "driver_names.h"

#define LINE_SIZE 1048576
static char line[LINE_SIZE];

static void put_hex(const char *value, size_t length)
{
    size_t index;
    if (length == 0) {
        fputs(" -", stdout);
        return;
    }
    fputc(' ', stdout);
    for (index = 0; index < length; ++index) {
        printf("%02x", (unsigned char)value[index]);
    }
}

static void read_configuration(char **cursor, CFG_T *configuration)
{
    int index;
    memset(configuration, 0, sizeof(*configuration));
    configuration->at = (int)strtol(*cursor, cursor, 10);
    for (index = 0; index < (int)(sizeof(configuration->regions) / sizeof(configuration->regions[0])); ++index) {
        configuration->regions[index] = (int)strtol(*cursor, cursor, 10);
    }
}

#ifndef PYFCSTM_GENERATED_NO_CONFIGURATION_TEXT
static char text[LINE_SIZE / 2];

static void put_configuration(const CFG_T *configuration)
{
    int index;
    printf(" %d", configuration->at);
    for (index = 0; index < (int)(sizeof(configuration->regions) / sizeof(configuration->regions[0])); ++index) {
        printf(" %d", configuration->regions[index]);
    }
}

#endif

static void put_error(const CFG_E *error)
{
    printf(" %d %lu", error->kind, (unsigned long)error->position);
    put_hex(error->message, strlen(error->message));
}

static void query(const CFG_T *configuration)
{
    CFG_E error;
    CFG_STATE leaves[CFG_STATE_COUNT + 1];
    size_t count;
    size_t index;
    int item;
    int valid;
    memset(&error, 0, sizeof(error));
    valid = CFG_FN(validate)(configuration, &error);
    printf("%d", valid == CFG_SUCCESS);
    put_error(&error);
#ifndef PYFCSTM_GENERATED_NO_CONFIGURATION_TEXT
    {
        static char buffer[65536];
        size_t length = CFG_FN(format)(configuration, buffer, sizeof(buffer));
        printf(" %lu", (unsigned long)length);
        put_hex(buffer, strlen(buffer));
    }
#else
    fputs(" 0 -", stdout);
#endif
    for (item = 0; item < CFG_REGION_COUNT; ++item) {
        printf(" %d", (int)CFG_FN(region_status)(configuration, item));
    }
    fputs(" |", stdout);
    for (item = 0; item < CFG_STATE_COUNT; ++item) {
        printf(" %d", CFG_FN(is_active)(configuration, item) != 0);
    }
    count = CFG_FN(leaves)(configuration, leaves, CFG_STATE_COUNT + 1);
    printf(" | %lu", (unsigned long)count);
    for (index = 0; index < count && index <= CFG_STATE_COUNT; ++index) {
        printf(" %d", leaves[index]);
    }
    fputc('\n', stdout);
}

#ifndef PYFCSTM_GENERATED_NO_CONFIGURATION_TEXT
static int hex_digit(char c)
{
    if (c >= '0' && c <= '9') {
        return c - '0';
    }
    if (c >= 'a' && c <= 'f') {
        return c - 'a' + 10;
    }
    if (c >= 'A' && c <= 'F') {
        return c - 'A' + 10;
    }
    return -1;
}

static size_t unhex(const char *hex, char *out)
{
    size_t length = 0;
    while (hex_digit(hex[0]) >= 0 && hex_digit(hex[1]) >= 0) {
        out[length++] = (char)(hex_digit(hex[0]) * 16 + hex_digit(hex[1]));
        hex += 2;
    }
    out[length] = '\0';
    return length;
}
#endif

int main(void)
{
    char *cursor;
    CFG_T configuration;
    while (fgets(line, sizeof(line), stdin) != NULL) {
        cursor = line + 2;
        if (line[0] == 'Q') {
            read_configuration(&cursor, &configuration);
            query(&configuration);
        } else if (line[0] == 'C') {
            CFG_STATE leaves[CFG_STATE_COUNT + 2];
            size_t capacity = (size_t)strtoul(cursor, &cursor, 10);
            size_t count;
            size_t index;
            memset(leaves, 0x7f, sizeof(leaves));
            read_configuration(&cursor, &configuration);
            count = CFG_FN(leaves)(&configuration, capacity == 0 ? NULL : leaves, capacity);
            printf("%lu", (unsigned long)count);
            for (index = 0; index < CFG_STATE_COUNT + 2; ++index) {
                printf(" %d", leaves[index]);
            }
            fputc('\n', stdout);
        } else if (line[0] == 'N') {
            CFG_E error;
            CFG_STATE leaf = 0;
            memset(&configuration, 0, sizeof(configuration));
            printf("%d", CFG_FN(validate)(NULL, NULL) == CFG_SUCCESS);
            memset(&error, 0, sizeof(error));
            printf(" %d", CFG_FN(validate)(NULL, &error) == CFG_SUCCESS);
            put_error(&error);
            printf(" %d %d %lu %lu",
                   (int)CFG_FN(region_status)(NULL, 0),
                   CFG_FN(is_active)(NULL, 0),
                   (unsigned long)CFG_FN(leaves)(NULL, &leaf, 1),
                   (unsigned long)CFG_FN(leaves)(&configuration, NULL, 5));
            printf(" %d %d %d",
                   (int)CFG_FN(region_status)(&configuration, -1),
                   (int)CFG_FN(region_status)(&configuration, CFG_REGION_COUNT),
                   CFG_FN(is_active)(&configuration, CFG_STATE_COUNT));
            configuration.at = CFG_STATE_COUNT;
            printf(" %d %d %lu",
                   (int)CFG_FN(region_status)(&configuration, 0),
                   CFG_FN(is_active)(&configuration, 0),
                   (unsigned long)CFG_FN(leaves)(&configuration, &leaf, 1));
#ifndef PYFCSTM_GENERATED_NO_CONFIGURATION_TEXT
            {
                char buffer[8];
                memset(buffer, 'x', sizeof(buffer));
                printf(" %lu", (unsigned long)CFG_FN(format)(&configuration, buffer, sizeof(buffer)));
                printf(" %d", buffer[0]);
                memset(&configuration, 0, sizeof(configuration));
                printf(" %lu", (unsigned long)CFG_FN(format)(&configuration, NULL, 0));
                printf(" %lu", (unsigned long)CFG_FN(format)(&configuration, NULL, 4));
                printf(" %lu", (unsigned long)CFG_FN(format)(NULL, NULL, 0));
                printf(" %d", CFG_FN(parse)("x", NULL, NULL) == CFG_SUCCESS);
                memset(&error, 0, sizeof(error));
                printf(" %d", CFG_FN(parse)(NULL, &configuration, &error) == CFG_SUCCESS);
                put_error(&error);
                memset(&error, 0, sizeof(error));
                printf(" %d", CFG_FN(parse)("x", NULL, &error) == CFG_SUCCESS);
                put_error(&error);
            }
#endif
            fputc('\n', stdout);
#ifndef PYFCSTM_GENERATED_NO_CONFIGURATION_TEXT
        } else if (line[0] == 'P') {
            CFG_E error;
            CFG_T sentinel;
            int status;
            unhex(cursor, text);
            memset(&error, 0, sizeof(error));
            memset(&sentinel, 0x5a, sizeof(sentinel));
            configuration = sentinel;
            status = CFG_FN(parse)(text, &configuration, line[1] == '!' ? NULL : &error);
            if (status == CFG_SUCCESS) {
                static char buffer[65536];
                fputs("OK", stdout);
                put_configuration(&configuration);
                CFG_FN(format)(&configuration, buffer, sizeof(buffer));
                put_hex(buffer, strlen(buffer));
            } else {
                printf("ERR %d", memcmp(&configuration, &sentinel, sizeof(sentinel)) == 0);
                put_error(&error);
            }
            fputc('\n', stdout);
        } else if (line[0] == 'T') {
            static char buffer[65536 + 16];
            size_t size = (size_t)strtoul(cursor, &cursor, 10);
            size_t length;
            size_t index;
            int intact = 1;
            read_configuration(&cursor, &configuration);
            memset(buffer, 'x', sizeof(buffer));
            length = CFG_FN(format)(&configuration, buffer, size);
            for (index = size; index < sizeof(buffer); ++index) {
                intact = intact && buffer[index] == 'x';
            }
            printf("%lu %d", (unsigned long)length, intact);
            put_hex(buffer, size == 0 ? 0 : strlen(buffer));
            fputc('\n', stdout);
#endif
        }
        fflush(stdout);
    }
    return 0;
}
"""

NAMES_TEMPLATE = """\
#include "machine.h"
#define CFG_T {{ machine_class_name(model) }}Configuration
#define CFG_E {{ machine_class_name(model) }}ConfigurationError
#define CFG_STATE {{ machine_class_name(model) }}StateId
#define CFG_FN(name) {{ machine_class_name(model) }}_configuration_##name
#define CFG_STATE_COUNT {{ machine_macro_name(model) }}_STATE_COUNT
#define CFG_REGION_COUNT {{ machine_macro_name(model) }}_REGION_COUNT
#define CFG_SUCCESS {{ machine_macro_name(model) }}_SUCCESS{{ '\\n' }}
"""

ERROR_KINDS = {
    "ARGUMENT": 1,
    "SYNTAX": 2,
    "UNKNOWN_PATH": 3,
    "REGION_PATH": 4,
    "MISSING_REGION_BLOCK": 5,
    "UNKNOWN_REGION": 6,
    "DUPLICATE_REGION": 7,
    "TOO_DEEP": 8,
    "INVALID_STATE": 9,
    "STATE_NOT_IN_REGION": 10,
    "INACTIVE_REGION": 11,
}
STATUS_NAMES = {0: "inactive", 1: "pending", 2: "live", 3: "done"}


def _hex(text):
    return binascii.hexlify(text.encode("utf-8")).decode("ascii")


def _unhex(token):
    return "" if token == "-" else binascii.unhexlify(token).decode("utf-8")


def _executable(build_dir, name):
    for root, _, files in os.walk(build_dir):
        for filename in files:
            if filename in (name, name + ".exe"):
                return os.path.join(root, filename)
    raise FileNotFoundError(name)


def _cmake_or_skip():
    cmake = shutil.which("cmake")
    if cmake is None:
        pytest.skip("cmake is required for generated C configuration tests.")
    return cmake


def _cmake_build(cmake, source_dir, build_dir):
    os.makedirs(build_dir)
    generator = ["-G", "MinGW Makefiles"] if os.name == "nt" else []
    for command in (
        [cmake] + generator + ["-DCMAKE_POLICY_VERSION_MINIMUM=3.5", source_dir],
        [cmake, "--build", ".", "--config", "Release"],
    ):
        result = subprocess.run(
            command,
            cwd=build_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        assert result.returncode == 0, result.stdout


def _render_template(tmp_dir):
    """Packaged C template plus the files of the protocol driver."""
    template_dir = extract_template("c", os.path.join(tmp_dir, "template"))
    for name, content in (
        ("driver_names.h.j2", NAMES_TEMPLATE),
        ("driver.c", DRIVER_SOURCE),
    ):
        with open(os.path.join(template_dir, name), "w", encoding="utf-8") as stream:
            stream.write(content)
    return StateMachineCodeRenderer(template_dir)


class Driver:
    """One compiled driver process speaking the line protocol."""

    def __init__(self, executable, model):
        self.executable = executable
        self.model = model
        self.states = [tuple(state.path) for state in model.walk_states()]
        self.regions = [
            tuple(region.path)
            for state in model.walk_states()
            for region in state.regions.values()
        ]

    def run(self, lines):
        result = subprocess.run(
            [self.executable],
            input="".join(line + "\n" for line in lines),
            stdout=subprocess.PIPE,
            universal_newlines=True,
            check=True,
        )
        output = result.stdout.splitlines()
        assert len(output) == len(lines)
        return output

    def slots(self, values):
        return " ".join(str(value) for value in values)

    def query(self, structs):
        rows = []
        for line in self.run(["Q " + self.slots(values) for values in structs]):
            head, active, leaves = line.split(" | ")
            fields = head.split(" ")
            rows.append(
                {
                    "valid": fields[0] == "1",
                    "kind": int(fields[1]),
                    "position": int(fields[2]),
                    "message": _unhex(fields[3]),
                    "length": int(fields[4]),
                    "text": _unhex(fields[5]),
                    "status": [STATUS_NAMES[int(item)] for item in fields[6:]],
                    "active": [item == "1" for item in active.split(" ")],
                    "leaves": [int(item) for item in leaves.split(" ")[1:]],
                    "leaf_count": int(leaves.split(" ")[0]),
                }
            )
        return rows

    def parse(self, texts, with_error=True):
        rows = []
        prefix = "P " if with_error else "P!"
        for line in self.run([prefix + (_hex(text) or "-") for text in texts]):
            fields = line.split(" ")
            if fields[0] == "OK":
                rows.append(
                    {
                        "ok": True,
                        "struct": [int(item) for item in fields[1:-1]],
                        "text": _unhex(fields[-1]),
                    }
                )
            else:
                rows.append(
                    {
                        "ok": False,
                        "untouched": fields[1] == "1",
                        "kind": int(fields[2]),
                        "position": int(fields[3]),
                        "message": _unhex(fields[4]),
                    }
                )
        return rows


def struct_of(driver, config):
    """Expected C value of a simulator configuration."""
    data = config.to_dict()
    slots = [0] * max(1, len(driver.regions))

    def walk(node):
        path = tuple(node["state"].split("."))
        for entry in node["regions"]:
            region = driver.regions.index(path + (entry["name"],))
            child = entry["configuration"]
            if child is None:
                slots[region] = -1
            else:
                slots[region] = driver.states.index(tuple(child["state"].split(".")))
                walk(child)

    walk(data)
    return [driver.states.index(tuple(data["state"].split(".")))] + slots


def transient_texts(model):
    """Every transient configuration of a small model, as text."""
    region_paths = {
        tuple(region.path)
        for state in model.walk_states()
        for region in state.regions.values()
    }

    def scope(path):
        for end in range(len(path) - 1, 0, -1):
            if path[:end] in region_paths:
                return path[:end]
        return ()

    def branches(region):
        for state in model.walk_states():
            path = tuple(state.path)
            if scope(path) != region:
                continue
            name = ".".join(path[len(region) :])
            if not state.regions:
                yield name
                continue
            options = [
                [
                    "%s: %s" % (child.name, value)
                    for value in ["[init]", "[done]"]
                    + list(branches(tuple(child.path)))
                ]
                for child in state.regions.values()
            ]
            for combination in itertools.product(*options):
                yield "%s{%s}" % (name, ", ".join(combination))

    return list(branches(()))


@pytest.fixture(scope="module")
def drivers(tmp_path_factory):
    cmake = _cmake_or_skip()
    root = str(tmp_path_factory.mktemp("c_configuration"))
    renderer = _render_template(root)
    sources = os.path.join(root, "sources")
    models = {}
    lines = [
        "cmake_minimum_required(VERSION 3.5)",
        "project(configuration_check C)",
        'set(STRICT_FLAGS "")',
        'if(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")',
        "    set(STRICT_FLAGS -std=c99 -pedantic -Wall -Wextra -Werror)",
        "endif()",
        "link_libraries(m)",
    ]
    for name, text in MODELS.items():
        model = load_state_machine_from_text(text)
        models[name] = model
        renderer.render(model, os.path.join(sources, name))
        for target, definition in (
            (name, None),
            (name + "_notext", "PYFCSTM_GENERATED_NO_CONFIGURATION_TEXT"),
        ):
            lines.append(
                "add_executable(%s %s/driver.c %s/machine.c)"
                % (target, name, name)
            )
            lines.append(
                "target_include_directories(%s PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/%s)"
                % (target, name)
            )
            lines.append("target_compile_options(%s PRIVATE ${STRICT_FLAGS})" % target)
            if definition:
                lines.append(
                    "target_compile_definitions(%s PRIVATE %s)" % (target, definition)
                )
    with open(os.path.join(sources, "CMakeLists.txt"), "w", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")
    build = os.path.join(root, "build")
    _cmake_build(cmake, sources, build)
    result = {}
    for name, model in models.items():
        result[name] = Driver(_executable(build, name), model)
        result[name + "_notext"] = Driver(_executable(build, name + "_notext"), model)
    result["_sources"] = sources
    return result


@pytest.mark.parametrize("name", sorted(MODELS))
def test_every_transient_configuration_agrees_with_the_simulator(drivers, name):
    driver = drivers[name]
    texts = transient_texts(driver.model)
    configs = [
        Configuration.parse(driver.model, text, mode="transient") for text in texts
    ]
    structs = [struct_of(driver, config) for config in configs]
    region_paths = [".".join(path) for path in driver.regions]
    state_paths = [".".join(path) for path in driver.states]
    for config, struct, row in zip(configs, structs, driver.query(structs)):
        assert row["valid"], (str(config), row["message"])
        assert (row["kind"], row["message"]) == (0, "")
        assert row["text"] == str(config)
        assert row["length"] == len(str(config).encode("utf-8"))
        assert row["status"] == [config.region_status(path) for path in region_paths]
        assert row["active"] == [config.is_active(path) for path in state_paths]
        assert row["leaves"] == [
            driver.states.index(tuple(state.path)) for state in config.leaves
        ]
        assert row["leaf_count"] == len(config.leaves)
    for config, struct, row in zip(
        configs, structs, driver.parse([str(config) for config in configs])
    ):
        assert row == {"ok": True, "struct": struct, "text": str(config)}
    for struct, row in zip(structs, drivers[name + "_notext"].query(structs)):
        assert row["valid"] and row["text"] == "" and row["message"] == ""


def test_zeroed_configuration_is_the_uninitialized_root(drivers):
    driver = drivers["hub"]
    row = driver.query([[0, 0, 0]])[0]
    assert row["valid"] and row["text"] == "Hub{Left: [init], Right: [init]}"
    assert row["status"] == ["pending", "pending"] and row["leaf_count"] == 0
    assert (
        str(Configuration.parse(driver.model, "Hub", mode="transient")) == row["text"]
    )


def _mutations(rng, text, names):
    """Plausible damage to configuration text."""
    words = re.findall(r"[A-Za-z_][A-Za-z_0-9]*|\[init\]|\[done\]", text)
    yield text[:-1]
    yield text + ","
    yield "  %s\n" % text.replace(", ", ",\n\t")
    for _ in range(12):
        position = rng.randrange(len(text) + 1)
        choice = rng.randrange(7)
        if choice == 0 and position < len(text):
            yield text[:position] + text[position + 1 :]
        elif choice == 1:
            yield text[:position] + rng.choice("{}:,. []") + text[position:]
        elif choice == 2 and words:
            old = rng.choice(words)
            yield text.replace(old, rng.choice(names + ["[init]", "[done]"]), 1)
        elif choice == 3 and words:
            old = rng.choice(words)
            yield text.replace(old, "%s.%s" % (old, rng.choice(names)), 1)
        elif choice == 4 and "{" in text:
            yield text.replace("{", "{%s: [done], " % rng.choice(names), 1)
        elif choice == 5 and "}" in text:
            yield text.replace(
                "}", ", %s: %s}" % (rng.choice(names), rng.choice(names)), 1
            )
        else:
            yield text.replace(rng.choice(["{", "}", ":", ",", "."]), "", 1)


@pytest.mark.parametrize("name", sorted(MODELS))
def test_parse_accepts_exactly_what_the_simulator_accepts(drivers, name):
    driver = drivers[name]
    rng = random.Random(name)
    names = sorted({path[-1] for path in driver.states + driver.regions})
    texts = sorted(
        {
            mutated
            for text in transient_texts(driver.model)
            for mutated in _mutations(rng, text, names)
            if "\0" not in mutated
        }
    )
    for text, row in zip(texts, driver.parse(texts)):
        try:
            config = Configuration.parse(driver.model, text, mode="transient")
        except ValueError:
            assert not row["ok"], (text, row)
            assert row["untouched"] and row["kind"] in ERROR_KINDS.values()
        else:
            assert row == {
                "ok": True,
                "struct": struct_of(driver, config),
                "text": str(config),
            }, text


@pytest.mark.parametrize(
    "name, text, kind, position, fragment",
    [
        (
            "motion",
            "Root.Run{Motion Stop}",
            "SYNTAX",
            16,
            "Expected ':' at byte 16, got 'Stop'.",
        ),
        (
            "motion",
            "",
            "SYNTAX",
            0,
            "Expected a configuration identifier at byte 0, got end of input.",
        ),
        ("motion", " \n[init]", "SYNTAX", 2, "got '[init]'"),
        ("motion", "Root.Run{Motion: Stop,}", "SYNTAX", 22, "got '}'"),
        ("motion", "Root.Run{Motion: Stop} x", "SYNTAX", 23, "Expected end of input"),
        ("motion", "Root.Run{Motion: Stop", "SYNTAX", 21, "Expected '}'"),
        ("motion", "Root.Run{Motion: é}", "SYNTAX", 17, "got 'é'."),
        ("motion", "Boot", "UNKNOWN_PATH", 0, "Unknown name 'Boot' at byte 0."),
        ("motion", "Root . Nope", "UNKNOWN_PATH", 7, "'Nope'"),
        ("motion", "Root.Run{Motion: Watch}", "UNKNOWN_PATH", 17, "'Watch'"),
        (
            "motion",
            "Root.Run.Motion",
            "REGION_PATH",
            0,
            "Path ends at a region of 'Root.Run' at byte 0.",
        ),
        (
            "motion",
            "Root.Run.Motion.Stop",
            "MISSING_REGION_BLOCK",
            0,
            "regions of 'Root.Run'",
        ),
        (
            "motion",
            "Root.Run{Speed: Stop}",
            "UNKNOWN_REGION",
            9,
            "Unknown region 'Speed' at byte 9.",
        ),
        ("motion", "Root.Off{Motion: Stop}", "UNKNOWN_REGION", 9, "'Motion'"),
        (
            "motion",
            "Root.Run{Motion: Stop, Motion: Move}",
            "DUPLICATE_REGION",
            23,
            "Duplicate region 'Motion'",
        ),
        (
            "motion",
            "Root.Run{Motion: [init], Motion: [done]}",
            "DUPLICATE_REGION",
            25,
            "'Motion'",
        ),
        (
            "nested",
            "Plant.Work{Line: Cell.Arm.Reach}",
            "MISSING_REGION_BLOCK",
            17,
            "'Plant.Work.Line.Cell'",
        ),
        (
            "nested",
            "Plant.Work{Line: Cell.Arm}",
            "REGION_PATH",
            17,
            "'Plant.Work.Line.Cell'",
        ),
        (
            "nested",
            "Plant.Work{Line: Feed{Arm: [done]}}",
            "UNKNOWN_REGION",
            22,
            "'Arm'",
        ),
        ("deep", "Deep.A{R1: B{R2: C{R3: D{R4: E}}}}", "UNKNOWN_REGION", 25, "'R4'"),
        ("deep", "Deep.A{R1: B{R2: C{R3: D{R4: E{R5: F}}}}}", "TOO_DEEP", 35, "'F'"),
        ("lamp", "Lamp.Off{X: Y}", "UNKNOWN_REGION", 9, "'X'"),
        (
            "lamp",
            "Lamp.Off{X: Y{Z: W}}",
            "TOO_DEEP",
            17,
            "nest deeper than the model allows near 'W' at byte 17.",
        ),
        ("lamp", "Lamp.Off{X: [done]}", "UNKNOWN_REGION", 9, "'X'"),
        ("cases", "Case.Pair{R: Beta}", "UNKNOWN_PATH", 13, "'Beta'"),
        ("cases", "Case.Pair{r: alpha}", "UNKNOWN_PATH", 13, "'alpha'"),
    ],
)
def test_parse_reports_the_cause_and_byte_offset(
    drivers, name, text, kind, position, fragment
):
    driver = drivers[name]
    with pytest.raises(ValueError):
        Configuration.parse(driver.model, text, mode="transient")
    row = driver.parse([text])[0]
    assert (row["ok"], row["untouched"], row["kind"], row["position"]) == (
        False,
        True,
        ERROR_KINDS[kind],
        position,
    )
    assert fragment in row["message"]
    assert driver.parse([text], with_error=False)[0]["untouched"]


def test_parse_message_stays_inside_its_buffer(drivers):
    long_name = "N" * 300
    row = drivers["motion"].parse(["Root." + long_name])[0]
    assert row["kind"] == ERROR_KINDS["UNKNOWN_PATH"]
    assert row["message"] == "Unknown name '%s...' at byte 5." % ("N" * 37)
    row = drivers["long"].parse(["Station.%s.%s.Leaf" % (LONG_OWNER, LONG_REGION)])[0]
    assert row["kind"] == ERROR_KINDS["MISSING_REGION_BLOCK"]
    assert (
        row["message"]
        == ("Path passes through the regions of 'Station.%s' at byte 0." % LONG_OWNER)[
            :159
        ]
    )
    row = drivers["long"].query([[0, 2]])[0]
    assert row["kind"] == ERROR_KINDS["INACTIVE_REGION"]
    assert (
        row["message"]
        == ("Region Station.%s.%s is not active" % (LONG_OWNER, LONG_REGION))[:159]
    )


def test_parse_reads_whitespace_like_the_simulator(drivers):
    driver = drivers["lamp"]
    characters = [
        chr(code) for code in range(1, 0x10000) if not 0xD800 <= code < 0xE000
    ]
    characters += ["\U0001f600", "\U000e0020"]
    texts = ["Lamp%s.On" % character for character in characters]
    for text, character, row in zip(texts, characters, driver.parse(texts)):
        assert row["ok"] == (re.fullmatch(r"\s", character) is not None), hex(
            ord(character)
        )
    assert sum(1 for character in characters if re.fullmatch(r"\s", character)) == 29
    text = "　Lamp\n.\tOn "
    assert driver.parse([text])[0] == {"ok": True, "struct": [2, 0], "text": "Lamp.On"}
    assert str(Configuration.parse(driver.model, text, mode="transient")) == "Lamp.On"


@pytest.mark.parametrize(
    "name, struct, kind, fragment",
    [
        (
            "motion",
            [2, 0, 0],
            "INVALID_STATE",
            "Configuration at = 2 is not a state outside every region.",
        ),
        ("motion", [6, 0, 0], "INVALID_STATE", "at = 6 "),
        ("motion", [-7, 0, 0], "INVALID_STATE", "at = -7 "),
        (
            "motion",
            [1, 4, 4],
            "STATE_NOT_IN_REGION",
            "Region Root.Run.Motion holds 4, which is not a state",
        ),
        (
            "motion",
            [1, 2, 99],
            "STATE_NOT_IN_REGION",
            "Region Root.Run.Guard holds 99,",
        ),
        ("motion", [1, -2, 0], "STATE_NOT_IN_REGION", "holds -2,"),
        (
            "motion",
            [5, -1, 0],
            "INACTIVE_REGION",
            "Region Root.Run.Motion is not active, so its slot must be pending.",
        ),
        ("motion", [5, 0, 4], "INACTIVE_REGION", "Root.Run.Guard"),
        (
            "nested",
            [2, 4, 0, 8, 0],
            "INACTIVE_REGION",
            "Region Plant.Work.Line.Cell.Arm is not active",
        ),
        (
            "nested",
            [2, 4, 0, 0, -1],
            "INACTIVE_REGION",
            "Region Plant.Work.Line.Cell.Belt is not active",
        ),
        (
            "nested",
            [2, 7, -1, 10, 0],
            "STATE_NOT_IN_REGION",
            "Region Plant.Work.Line.Cell.Arm holds 10,",
        ),
        ("lamp", [1, 3], "INACTIVE_REGION", "Unused region slot must be pending."),
    ],
)
def test_validate_names_the_broken_slot(drivers, name, struct, kind, fragment):
    row = drivers[name].query([struct])[0]
    assert (row["valid"], row["kind"], row["position"]) == (False, ERROR_KINDS[kind], 0)
    assert fragment in row["message"]
    assert (row["length"], row["text"]) == (0, "")
    notext = drivers[name + "_notext"].query([struct])[0]
    assert (notext["valid"], notext["kind"], notext["message"]) == (
        False,
        ERROR_KINDS[kind],
        "",
    )


def test_format_truncates_like_snprintf(drivers):
    driver = drivers["motion"]
    expected = "Root.Run{Motion: Stop, Guard: [done]}"
    struct = " ".join(str(item) for item in [1, 2, -1])
    lines = ["T %d %s" % (size, struct) for size in range(len(expected) + 3)]
    for size, line in enumerate(driver.run(lines)):
        length, intact, shown = line.split(" ")
        assert (int(length), intact) == (len(expected), "1")
        assert _unhex(shown) == expected[: max(0, size - 1)]


def test_leaves_report_the_total_beyond_the_capacity(drivers):
    driver = drivers["nested"]
    config = Configuration.parse(
        driver.model, "Plant.Work{Line: Cell{Arm: Grip, Belt: Roll}, Audit: Log}"
    )
    struct = struct_of(driver, config)
    expected = [driver.states.index(tuple(state.path)) for state in config.leaves]
    lines = ["C %d %s" % (capacity, driver.slots(struct)) for capacity in range(5)]
    filler = 0x7F7F7F7F
    for capacity, line in enumerate(driver.run(lines)):
        fields = [int(item) for item in line.split(" ")]
        written = min(capacity, len(expected))
        assert fields[0] == len(expected) == 3
        assert fields[1 : 1 + written] == expected[:written]
        assert set(fields[1 + written :]) == {filler}


@pytest.mark.parametrize("name", ["motion", "motion_notext"])
def test_null_arguments_are_refused_without_crashing(drivers, name):
    fields = drivers[name].run(["N"])[0].split(" ")
    notext = name.endswith("_notext")
    assert fields[:4] == ["0", "0", "1", "0"]
    assert _unhex(fields[4]) == ("" if notext else "Configuration pointer is NULL.")
    assert fields[5:15] == ["0"] * 10
    if notext:
        assert fields[15:] == []
    else:
        assert fields[15:] == [
            "0",
            "0",
            "4",
            "4",
            "0",
            "0",
            "0",
            "1",
            "0",
            _hex("Text pointer is NULL."),
            "0",
            "1",
            "0",
            _hex("Configuration pointer is NULL."),
        ]


def _strict_cxx_compiler():
    for name in ("c++", "g++", "clang++"):
        path = shutil.which(name)
        if path is not None:
            return path
    pytest.skip("a C++ compiler is required for the C++98 header check.")


@pytest.mark.parametrize("name", sorted(MODELS))
def test_header_compiles_as_strict_cxx98(drivers, tmp_path, name):
    compiler = _strict_cxx_compiler()
    source = tmp_path / "check.cpp"
    source.write_text(
        '#include "driver_names.h"\n'
        "int main() { CFG_T value; value.at = 0; value.regions[0] = 0; "
        "return CFG_FN(validate)(&value, 0) == CFG_SUCCESS ? 0 : 1; }\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            compiler,
            "-std=c++98",
            "-pedantic-errors",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-fsyntax-only",
            "-I",
            os.path.join(drivers["_sources"], name),
            str(source),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )
    assert result.returncode == 0, result.stdout


def test_generated_source_depends_only_on_string_h():
    model = load_state_machine_from_text(MODELS["nested"])
    source = render_c_configuration_source(model, "PlantMachine", "PLANT_MACHINE")
    assert re.findall(r"#include\s*<[^>]+>", source) == ["#include <string.h>"]
    for function in ("snprintf", "sprintf", "malloc", "free", "strtol", "printf"):
        assert re.search(r"\b%s\s*\(" % function, source) is None


def test_case_only_names_get_distinct_ids():
    model = load_state_machine_from_text(MODELS["cases"])
    header = render_c_configuration_header(model, "CaseMachine", "CASE_MACHINE")
    assert (
        "#define CASE_MACHINE_REGION_p4_Case_p4_Pair_p1_R ((CaseMachineRegionId)0)"
        in header
    )
    assert (
        "#define CASE_MACHINE_REGION_p4_Case_p4_Pair_p1_r ((CaseMachineRegionId)1)"
        in header
    )


@pytest.mark.parametrize(
    "class_name, macro_name, message",
    [
        (
            "Bad-Name",
            "GOOD",
            "machine_class_name must be a C identifier, got 'Bad-Name'.",
        ),
        ("Good", "9BAD", "machine_macro_name must be a C identifier, got '9BAD'."),
        ("Good", None, "machine_macro_name must be a C identifier, got None."),
    ],
)
@pytest.mark.parametrize(
    "render", [render_c_configuration_header, render_c_configuration_source]
)
def test_names_must_be_c_identifiers(render, class_name, macro_name, message):
    model = load_state_machine_from_text(MODELS["lamp"])
    with pytest.raises(ValueError) as info:
        render(model, class_name, macro_name)
    assert str(info.value) == message
