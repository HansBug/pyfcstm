"""Tests for the standard-library self-check argument contracts."""

import pytest


@pytest.mark.unittest
def test_network_requires_visualize_after_parse_order_is_known():
    """Cross-option validation is independent of option order."""
    from pyfcstm._selfcheck.arguments import SelfCheckArgumentError
    from pyfcstm._selfcheck.arguments import parse_selfcheck_args

    for argv in (
        ("--network", "--profile", "visualize"),
        ("--profile", "visualize", "--network"),
    ):
        assert parse_selfcheck_args(argv).network is True

    with pytest.raises(SelfCheckArgumentError):
        parse_selfcheck_args(("--network", "--profile", "default"))


@pytest.mark.unittest
def test_timeout_scale_and_profile_defaults_are_stable():
    """The parser exposes documented defaults without importing Click."""
    from pyfcstm._selfcheck.arguments import parse_selfcheck_args

    options = parse_selfcheck_args(())
    assert options.profile == "default"
    assert options.output_format == "human"
    assert options.timeout_scale == 1.0


@pytest.mark.unittest
def test_supervisor_parser_rejects_abbreviated_option_names():
    """Public self-check options require their exact long names."""
    from pyfcstm._selfcheck.arguments import SelfCheckArgumentError
    from pyfcstm._selfcheck.arguments import parse_selfcheck_args

    with pytest.raises(SelfCheckArgumentError):
        parse_selfcheck_args(("--pro", "visualize"))


@pytest.mark.unittest
def test_worker_parser_requires_exact_protocol_fields():
    """Hidden worker parsing rejects missing or extra protocol fields."""
    from pyfcstm._selfcheck.arguments import SelfCheckArgumentError
    from pyfcstm._selfcheck.arguments import parse_worker_args

    options = parse_worker_args(
        (
            "--check-id",
            "artifact.self_dispatch",
            "--worker-key",
            "self_dispatch",
            "--nonce",
            "0" * 32,
            "--result-mode",
            "stdout",
        )
    )
    assert options.nonce == "0" * 32

    with pytest.raises(SelfCheckArgumentError):
        parse_worker_args(("--check-id", "artifact.self_dispatch"))


@pytest.mark.unittest
def test_worker_flag_value_is_not_treated_as_mode_token():
    """Mode conflict detection uses exact argv tokens, not substrings."""
    from pyfcstm._selfcheck.arguments import parse_worker_args

    options = parse_worker_args(
        (
            "--check-id",
            "value--self-check",
            "--worker-key",
            "self_dispatch",
            "--nonce",
            "1" * 32,
            "--result-mode",
            "stdout",
        )
    )
    assert options.check_id == "value--self-check"


@pytest.mark.unittest
def test_worker_parser_rejects_abbreviated_option_names():
    """Hidden worker argv uses exact option names, never argparse abbreviations."""
    from pyfcstm._selfcheck.arguments import SelfCheckArgumentError
    from pyfcstm._selfcheck.arguments import parse_worker_args

    with pytest.raises(SelfCheckArgumentError):
        parse_worker_args(
            (
                "--check",
                "demo",
                "--worker-key",
                "self_dispatch",
                "--nonce",
                "0" * 32,
                "--result-mode",
                "stdout",
            )
        )


@pytest.mark.unittest
def test_argument_errors_cover_bounds_and_mode_exclusivity():
    """Bounds, unknown options, and result-mode combinations are rejected."""
    from pyfcstm._selfcheck.arguments import SelfCheckArgumentError
    from pyfcstm._selfcheck.arguments import parse_selfcheck_args
    from pyfcstm._selfcheck.arguments import parse_worker_args

    with pytest.raises(SelfCheckArgumentError):
        parse_selfcheck_args(("--timeout-scale", "0.01"))
    with pytest.raises(SelfCheckArgumentError):
        parse_selfcheck_args(("--unknown",))
    with pytest.raises(SelfCheckArgumentError):
        parse_worker_args(
            (
                "--check-id",
                "demo",
                "--worker-key",
                "demo",
                "--nonce",
                "0" * 32,
                "--result-mode",
                "file",
            )
        )
    with pytest.raises(SelfCheckArgumentError):
        parse_worker_args(
            (
                "--check-id",
                "demo",
                "--worker-key",
                "demo",
                "--nonce",
                "0" * 32,
                "--result-mode",
                "stdout",
                "--result-file",
                "result.log",
            )
        )
