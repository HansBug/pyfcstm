"""Completion of every command of the simulate REPL through the public completer.

The completer is the object the REPL hands to ``prompt_toolkit``; these tests
type partial lines into it the way a user would and read what it offers.
"""

import os
import sys

import pytest
from prompt_toolkit.document import Document

from pyfcstm.entry.simulate.commands import CommandProcessor
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime

pytestmark = pytest.mark.unittest

MODEL = """
def int count = 0;
def float ratio = 0.5;
state Root {
    event Reset;
    [*] -> Idle;
    state Idle;
    state Busy;
    Idle -> Busy :: Start;
    Busy -> Idle :: Stop;
}
"""


@pytest.fixture()
def complete():
    runtime = SimulationRuntime(load_state_machine_from_text(MODEL))
    runtime.cycle()
    completer = CommandProcessor(runtime).create_completer()

    def offered(text):
        return [
            (item.text, item.display_meta_text)
            for item in completer.get_completions(Document(text, len(text)), None)
        ]

    return offered


def _texts(items):
    return [text for text, _ in items]


def test_cycle_offers_only_the_events_that_start_the_typed_word(complete):
    assert _texts(complete("cycle St")) == ["Start"]
    # After a count the same filter applies to the next word.
    assert "Start" in _texts(complete("cycle 3 St"))
    assert "Stop" not in _texts(complete("cycle 3 St"))
    assert "5" in _texts(complete("cycle 5"))
    assert _texts(complete("cycle 3 Zz")) == []


def test_init_offers_example_values_of_the_typed_variable(complete):
    assert _texts(complete("init Root.Idle count=")) == [
        "count=0", "count=1", "count=10", "count=100", "count=0xFF", "count=0b1010",
    ]
    assert _texts(complete("init Root.Idle count=0b")) == ["count=0b1010"]
    assert _texts(complete("init Root.Idle ratio=1")) == ["ratio=1.0", "ratio=10.5", "ratio=1e-3"]
    # A name the model does not have gets no example values.
    assert complete("init Root.Idle nothing=") == []


def test_init_offers_the_variables_that_are_still_missing(complete):
    assert _texts(complete("init Root.Idle ")) == ["count=", "ratio="]
    assert _texts(complete("init Root.Idle count=1 ")) == ["ratio="]
    assert _texts(complete("init Root.Idle co")) == ["count="]


def test_init_offers_the_states_with_their_kind(complete):
    offered = dict(complete("init Root"))
    assert offered["Root"] == "composite state"
    assert offered["Root.Idle"] == "leaf state"


def test_history_offers_all_and_common_counts(complete):
    assert _texts(complete("history ")) == ["all", "5", "10", "20", "50", "100"]
    assert _texts(complete("history a")) == ["all"]
    assert _texts(complete("history 1")) == ["10", "100"]
    assert complete("history 5 ") == []


def test_setting_offers_the_keys_and_the_values_of_each(complete):
    assert _texts(complete("setting ")) == [
        "table_max_rows", "history_size", "color", "log_level", "diagnostics",
    ]
    assert _texts(complete("setting hi")) == ["history_size"]
    assert "debug" in _texts(complete("setting log_level "))
    assert _texts(complete("setting log_level de")) == ["debug"]
    assert _texts(complete("setting color o")) == ["on", "off"]
    assert _texts(complete("setting diagnostics t")) == ["true"]
    assert _texts(complete("setting history_size 1")) == ["10", "100", "1000"]
    assert _texts(complete("setting table_max_rows 5")) == ["50", "500"]
    # A key with no list of values offers none.
    assert complete("setting unknown ") == []


def test_decisions_and_why_offer_their_flags(complete):
    assert _texts(complete("decisions ")) == ["--verbose"]
    assert _texts(complete("why --v")) == ["--verbose"]


def test_a_command_is_completed_from_its_first_letters(complete):
    assert "history" in _texts(complete("hi"))
    assert _texts(complete("zz")) == []


def test_export_offers_the_supported_files_directories_and_history_names(
    complete, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "notes.txt").write_text("x")
    (tmp_path / "run.json").write_text("{}")
    (tmp_path / "history.csv").write_text("")
    (tmp_path / "sub").mkdir()
    offered = dict(complete("export "))
    assert offered["sub" + os.sep] == "directory"
    assert offered["run.json"] == "JSON file"
    assert offered["notes.txt"] == "TXT file"
    # ``history.csv`` exists, so it is not offered a second time as a suggestion.
    assert _texts(complete("export ")).count("history.csv") == 1
    assert "history.yaml" in offered
    assert _texts(complete("export ru")) == ["run.json"]
    assert _texts(complete("export sub/")) == []
    (tmp_path / "sub" / "out.csv").write_text("")
    assert _texts(complete("export sub/o")) == [os.path.join("sub", "out.csv")]
    assert _texts(complete("export sub" + os.sep)) == ["out.csv"]
    # Only the first argument of export is a path.
    assert complete("export run.json ") == []
    # No such directory: nothing to list and no common names beside a path.
    assert complete("export nowhere/") == []
    (tmp_path / "plain").write_text("")
    assert _texts(complete("export pl")) == ["plain"]


@pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="needs a directory the current user cannot read",
)
def test_export_offers_nothing_from_a_directory_it_cannot_read(
    complete, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    locked = tmp_path / "locked"
    locked.mkdir()
    (locked / "a.csv").write_text("")
    locked.chmod(0)
    try:
        assert complete("export locked/") == []
    finally:
        locked.chmod(0o700)
