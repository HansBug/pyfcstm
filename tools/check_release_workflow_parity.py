"""
Check that the Release Test workflow exercises what the release workflow runs.

``release.yml`` builds from a tag checkout, which is a detached HEAD, and passes
the build identity to the build explicitly; ``release_test.yml`` is the only gate
that runs before a tag exists. If the two drift apart, a defect that only a tag
build shows reaches a release. This tool is a repository-local helper, not part
of the ``pyfcstm`` package.

The check requires that:

* every job that runs ``make build_info`` passes ``PYFCSTM_BUILD_COMMIT``,
  ``PYFCSTM_BUILD_DIRTY`` and ``PYFCSTM_BUILD_REF``, in both workflows;
* every such job in ``release_test.yml`` detaches HEAD with ``git checkout --detach``;
* every ``--self-check`` command and every ``make`` target that ``release.yml``
  runs is also run by ``release_test.yml``.

Example::

    $ python tools/check_release_workflow_parity.py --check
"""
import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Set

import yaml

ROOT = Path(__file__).resolve().parent.parent
IDENTITY_KEYS = {"PYFCSTM_BUILD_COMMIT", "PYFCSTM_BUILD_DIRTY", "PYFCSTM_BUILD_REF"}


def _scripts(job: dict) -> List[str]:
    """Return the shell scripts of the steps of one job."""
    return [step["run"] for step in job.get("steps", []) if "run" in step]


def _commands(workflow: dict) -> Dict[str, Set[str]]:
    """Collect the normalized self-check commands and make targets of a workflow."""
    found = {"self-check": set(), "make": set()}
    for job in workflow["jobs"].values():
        for script in _scripts(job):
            for line in script.split("\n"):
                line = line.strip()
                if "--self-check" in line:
                    line = re.sub(r'--report\s+"[^"]*"', "--report X", line)
                    line = re.sub(r"\|.*$", "", line).strip()
                    line = re.sub(r'^("?\$[a-z_]+"?|\S*pyfcstm\S*)\s', "EXE ", line)
                    found["self-check"].add(line)
                match = re.match(r"^make ([a-z_]+)", line)
                if match:
                    found["make"].add(match.group(1))
    return found


def find_problems(release: dict, release_test: dict) -> List[str]:
    """Return the ways in which the Release Test workflow differs from release."""
    problems = []
    for name, workflow in (("release.yml", release), ("release_test.yml", release_test)):
        for job_name, job in workflow["jobs"].items():
            if not any("make build_info" in script for script in _scripts(job)):
                continue
            missing = IDENTITY_KEYS - set(job.get("env") or {})
            if missing:
                problems.append(
                    "{}: job {} builds without {}".format(name, job_name, sorted(missing))
                )
            if workflow is release_test and not any(
                "git checkout --detach" in script for script in _scripts(job)
            ):
                problems.append(
                    "{}: job {} does not detach HEAD like a tag checkout".format(name, job_name)
                )
    expected, actual = _commands(release), _commands(release_test)
    for kind in ("self-check", "make"):
        for item in sorted(expected[kind] - actual[kind]):
            problems.append(
                "release_test.yml never runs the {} step {!r} of release.yml".format(kind, item)
            )
    return problems


def _load(name: str) -> dict:
    """Load one workflow file of the repository."""
    return yaml.safe_load((ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8"))


def _self_check() -> None:
    """Show that each kind of drift is reported."""
    release, release_test = _load("release.yml"), _load("release_test.yml")
    assert find_problems(release, release_test) == []
    for job in release_test["jobs"].values():
        if "make build_info" in "".join(_scripts(job)):
            job["env"] = {}
            break
    assert any("builds without" in item for item in find_problems(release, release_test))
    release_test = _load("release_test.yml")
    for job in release_test["jobs"].values():
        for step in job.get("steps", []):
            if step.get("run") == "git checkout --detach":
                step["run"] = "true"
    assert any("detach" in item for item in find_problems(release, release_test))
    release_test = _load("release_test.yml")
    release["jobs"]["extra"] = {"steps": [{"run": "make a_new_release_gate"}]}
    assert any("a_new_release_gate" in item for item in find_problems(release, release_test))


def main(argv: List[str]) -> int:
    """Run the check or its self-check and return the process exit status."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--check", action="store_true", help="compare the two workflows")
    parser.add_argument("--self-check", action="store_true", help="prove the check can fail")
    args = parser.parse_args(argv)
    if args.self_check:
        _self_check()
    if args.check:
        problems = find_problems(_load("release.yml"), _load("release_test.yml"))
        for item in problems:
            print("ERROR:", item)
        if problems:
            return 1
        print("release workflow parity: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
