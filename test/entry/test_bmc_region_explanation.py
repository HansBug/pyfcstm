"""Infeasibility explanations on a model with regions."""

import json

import pytest
from click.testing import CliRunner

from pyfcstm.entry import pyfcstmcli

pytestmark = pytest.mark.unittest

MODEL = """
input int fault;
input int requested;
control int permit = 0;
output int motor = 0;
state Controller {
    event Start;
    [*] -> Idle;
    state Idle { during { motor = 0; } }
    state Running {
        region Safety {
            [*] -> Watching;
            state Watching {
                during { if [fault != 0] { permit = 0; } else { permit = 1; } }
            }
        }
        region Motion {
            [*] -> Off;
            state Off { during { motor = 0; } }
            state On { during { motor = 1; } }
            Off -> On : if [permit != 0 && requested != 0];
            On -> Off : if [permit == 0 || requested == 0];
        }
    }
    Idle -> Running : /Start;
}
"""


def feasibility(tmp_path, query, mode):
    (tmp_path / "m.fcstm").write_text(MODEL)
    (tmp_path / "q.fbmcq").write_text(query)
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "bmc",
            "-i",
            str(tmp_path / "m.fcstm"),
            "-q",
            str(tmp_path / "q.fbmcq"),
            "--explain-infeasibility",
            mode,
            "--json",
        ],
    )
    assert result.exit_code == 3, result.output
    return json.loads(result.output)["result"]["feasibility"]


@pytest.mark.parametrize("mode", ["formal", "proof"])
@pytest.mark.parametrize(
    "query, stage, explained",
    [
        ("init cold where motor == 5;\ncheck reach <= 2: motor == 1;", "initialization", "complete"),
        (
            "assume always: requested == 1 && requested == 0;\ncheck reach <= 2: motor == 1;",
            "assumptions",
            "partial",
        ),
    ],
)
def test_an_infeasible_query_is_localized_and_explained(
    tmp_path, query, stage, explained, mode
):
    found = feasibility(tmp_path, query, mode)
    assert found["infeasible_stage"] == stage
    assert found["explanation"]["status"] == explained
