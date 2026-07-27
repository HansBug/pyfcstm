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
