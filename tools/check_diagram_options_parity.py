"""Check snake-case/camel-case public option mappings."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pyfcstm.diagram import DiagramOptions, DiagramViewState  # noqa: E402
from diagram_contract_support import sample_diagram  # noqa: E402


def main() -> None:
    snake = sample_diagram().with_options(
        {"direction": "LR", "detail_level": "minimal", "cjk_locale": "jp"}
    )
    camel = sample_diagram().with_options(
        {"direction": "LR", "detailLevel": "minimal", "cjkLocale": "jp"}
    )
    if snake.options.to_dict() != camel.options.to_dict():
        raise SystemExit("snake-case and camel-case options diverged")
    if DiagramOptions(cjk_locale="JP").to_dict()["cjkLocale"] != "jp":
        raise SystemExit("locale normalization diverged")
    try:
        sample_diagram().with_view_state({"zoom": True})
    except ValueError:
        pass
    else:
        raise SystemExit("boolean zoom was accepted through mapping input")
    if DiagramViewState(mode="fcstm").to_dict()["mode"] != "fcstm":
        raise SystemExit("view state mapping contract changed")
    print("diagram options parity: mappings and validation passed")


if __name__ == "__main__":
    main()
