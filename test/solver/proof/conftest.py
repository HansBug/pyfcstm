"""Fixed captured evidence for proof-layout and complete-text regressions."""

import json
from pathlib import Path

import pytest

from pyfcstm.solver.proof import UnsatReport


@pytest.fixture
def proof_snapshot():
    def load(name):
        path = Path(__file__).with_name('proof_readings') / (name + '.json')
        return UnsatReport.from_canonical(json.loads(path.read_text(encoding='utf-8')))
    return load


@pytest.fixture
def captured_branch_proof(monkeypatch, proof_snapshot):
    from pyfcstm.solver.proof import _z3_proof

    # Replay an actual capture for the branch query. Folder tests require this
    # valid scoped layout even when native propagation now finds a shorter one.
    report = proof_snapshot('branches')
    monkeypatch.setattr(_z3_proof, 'capture_proof', lambda *args: report)
