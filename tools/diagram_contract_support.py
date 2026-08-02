"""Small normal-path fixtures shared by diagram maintenance gates."""

import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pyfcstm.diagram import DiagramOptions, DiagramViewState  # noqa: E402
from pyfcstm.model import (  # noqa: E402
    load_state_machine_from_file,
    load_state_machine_from_text,
)


# One representative machine rather than a two-state toy: the gates that share
# it have to exercise nested composites, a guarded transition with an effect, a
# self-loop, lifecycle and aspect actions, CJK display names, and several
# objects declared on one source line (source-link cycling).
SAMPLE_SOURCE = """def int counter = 0;

state Root {
    state Idle named "空闲状态" {
        enter { counter = 0; }
        during { counter = counter + 1; }
    }
    state Running named "控制器运行状态" {
        state Warmup named "预热阶段";
        state Steady named "稳态阶段";
        [*] -> Warmup;
        Warmup -> Steady : if [counter > 2] effect { counter = 0; }
        Steady -> Steady;
        >> during before { counter = counter + 1; }
        exit abstract Teardown;
    }
    event Go named "启动事件";
    event Back named "返回事件";
    [*] -> Idle; Idle -> Running :: Go; Running -> Idle :: Back;
}
"""


def sample_diagram(
    *,
    cjk_locale: str = "sc",
    direction: str = "TB",
    view_mode: str = "compare",
):
    """Build one ordinary source-backed diagram for maintenance checks."""
    model = load_state_machine_from_text(SAMPLE_SOURCE)
    return model.diagram(
        options=DiagramOptions(cjk_locale=cjk_locale, direction=direction),
        view_state=DiagramViewState(mode=view_mode),
    )


# A machine whose leaf states carry both events and lifecycle actions, so the
# three detail presets have something to disagree about. The ordinary sample has
# events but no actions, which makes ``normal`` and ``full`` draw the same
# picture and hides half of what the presets are for.
# Kept small on purpose. An earlier version carried a third leaf and a shared
# event so the gate could watch edge tinting too, and its Details drawer grew
# tall enough to leave the stacked comparison four pixels short at 750x900 --
# at every level, including the one whose drawing this change does not touch.
# Edge tinting needs no browser, so it is held by the jsfcstm suite instead and
# the fixture stays inside the layout it is rendered in.
DETAIL_LEVEL_SOURCE = """
def int counter = 0;

state Board {
    state PowerOn {
        enter { counter = 0; }
        during { counter = counter + 1; }
    }
    state Idle;
    [*] -> PowerOn;
    PowerOn -> Idle :: Boot effect { counter = counter + 1; }
}
"""

# What the viewer should draw at each level: event rows and action rows inside
# state bodies, and whether a transition effect gets a note pad of its own.
#
# ``minimal`` shows titles only and writes effects inline; ``normal`` adds the
# one state event (``PowerOn::Boot``) and moves effects into notes; ``full``
# adds that state's two lifecycle actions as well. Three settings of the four
# the presets disagree on are visible here; the fourth, edge tinting, is held
# by the jsfcstm suite, which can read a stroke colour without a browser.
DETAIL_LEVEL_EXPECTATIONS = {
    "minimal": {"eventRows": 0, "actionRows": 0, "notes": False},
    "normal": {"eventRows": 1, "actionRows": 0, "notes": True},
    "full": {"eventRows": 1, "actionRows": 2, "notes": True},
}


def write_detail_level_sample_html(
    path: Path, *, cjk_locale: str = "sc", direction: str = "TB", level: str = "normal"
) -> None:
    """Write a standalone viewer fixture at one detail level."""
    model = load_state_machine_from_text(DETAIL_LEVEL_SOURCE)
    path.write_text(
        model.diagram(
            options=DiagramOptions(
                cjk_locale=cjk_locale, direction=direction, detail_level=level
            ),
            view_state=DiagramViewState(mode="compare"),
        ).to_html(),
        encoding="utf-8",
    )


def write_sample_html(
    path: Path, *, cjk_locale: str = "sc", direction: str = "TB"
) -> None:
    """Write an ordinary standalone viewer fixture."""
    path.write_text(
        sample_diagram(cjk_locale=cjk_locale, direction=direction).to_html(),
        encoding="utf-8",
    )


# A model whose states come from two source files, so the viewer renders the
# document picker and the source panel has to resolve IDs per document. The
# single-document fixture above leaves that whole path unexercised.
IMPORT_MAIN_SOURCE = """def int counter = 0;

state Root {
    import "./child.fcstm" as Running;
    state Idle named "空闲状态" {
        enter { counter = 0; }
    }
    [*] -> Idle;
    event Go named "启动事件";
    event Back named "返回事件";
    Idle -> Running :: Go;
    Running -> Idle :: Back;
}
"""

IMPORT_CHILD_SOURCE = """state Running named "控制器运行状态" {
    state Warmup named "预热阶段";
    state Steady named "稳态阶段";
    [*] -> Warmup;
    Warmup -> Steady : if [counter > 2] effect { counter = 0; }
    Steady -> Steady;
}
"""


def write_multi_document_sample_html(
    path: Path, *, cjk_locale: str = "sc", direction: str = "TB"
) -> None:
    """
    Write a viewer fixture whose model spans two source documents.

    :param path: Destination for the generated viewer.
    :type path: pathlib.Path
    :param cjk_locale: Embedded CJK font locale, defaults to ``'sc'``.
    :type cjk_locale: str, optional
    :param direction: Layout direction, defaults to ``'TB'``.
    :type direction: str, optional
    :return: ``None``.
    :rtype: None
    """
    with tempfile.TemporaryDirectory(prefix="pyfcstm-diagram-imports-") as directory:
        base = Path(directory)
        (base / "child.fcstm").write_text(IMPORT_CHILD_SOURCE, encoding="utf-8")
        (base / "main.fcstm").write_text(IMPORT_MAIN_SOURCE, encoding="utf-8")
        model = load_state_machine_from_file(base / "main.fcstm")
        document = model.diagram(
            options=DiagramOptions(cjk_locale=cjk_locale, direction=direction),
            view_state=DiagramViewState(mode="compare"),
        ).to_html()
    path.write_text(document, encoding="utf-8")
