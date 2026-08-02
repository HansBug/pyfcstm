#!/usr/bin/env python3
"""Validate BMC documentation structure, equations, and landing surfaces."""

from __future__ import annotations

import argparse
import json
import re
import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


_REPO_ROOT = Path(__file__).resolve().parents[1]

_EQUATION_LABELS = (
    "bmc-trace-frame-domain",
    "bmc-trace-event-domain",
    "bmc-trace-variable-domain",
    "bmc-trace-selector-domain",
    "bmc-domain-formula",
    "bmc-initial-control",
    "bmc-initial-retained",
    "bmc-initial-havoc",
    "bmc-initial-where",
    "bmc-case-antecedent",
    "bmc-case-selector",
    "bmc-case-relation",
    "bmc-case-post-control",
    "bmc-case-variable-write",
    "bmc-case-variable-carry",
    "bmc-step-fallback",
    "bmc-step-terminated-absorb",
    "bmc-step-delta-gamma",
    "bmc-transition-formula",
    "bmc-environment-formula",
    "bmc-core-formula",
    "bmc-predicate-defined",
    "bmc-predicate-good",
    "bmc-predicate-bad-true",
    "bmc-predicate-bad-false",
    "bmc-objective-reach",
    "bmc-objective-forbid",
    "bmc-objective-invariant",
    "bmc-objective-must-reach",
    "bmc-objective-exists-always",
    "bmc-call-count",
    "bmc-objective-cover",
    "bmc-response-violation",
    "bmc-response-trigger-undefined",
    "bmc-response-incomplete",
    "bmc-solve-formulas",
    "bmc-verdict-map",
    "bmc-witness-projection",
    "bmc-replay-agreement",
    "bmc-symbol-growth",
    "bmc-core-soundness",
    "bmc-core-subset-minimality",
    "bmc-proof-input-binding",
    "bmc-proof-input-bijection",
)

_PAGE_PAIRS = (
    "tutorials/bmc/index",
    "how_to/bmc/index",
    "explanations/bmc_semantics/index",
    "explanations/bmc_properties/index",
    "explanations/bmc_solving/index",
    "reference/bmc_query/index",
    "reference/bmc_results/index",
    # The CLI reference documents ``pyfcstm bmc`` alongside the other commands,
    # so it carries BMC option contracts and belongs under the same structural
    # checks.  It was outside them while the only BMC option surface lived on
    # the result-protocol page.
    "reference/cli/index",
)

_EQUATION_PAIRS = (
    "explanations/bmc_semantics/index",
    "explanations/bmc_properties/index",
    "explanations/bmc_solving/index",
)

_SCHEMA_RELATIVE_PATH = Path("reference/bmc_results/bmc_cli.schema.json")
_SCHEMA_ID = (
    "https://github.com/HansBug/pyfcstm/blob/main/"
    "docs/source/reference/bmc_results/bmc_cli.schema.json"
)

_TUTORIAL_DIAGRAMS = (
    ("bmc_pipeline.puml", "bmc_pipeline_zh.puml"),
    ("first_check_en.puml", "first_check_zh.puml"),
)

# The optional scenario-infeasibility explanation is published on three surfaces
# at once -- a human report block, a JSON object, and a set of public dataclasses
# -- and the vocabularies below are closed enums in the code.  Every value a
# reader can be handed therefore needs somewhere to look it up, which is why
# these are checked as whole sets rather than as a few representative names.
#
# The values are transcribed from pyfcstm/bmc/explanation.py.  They are copied
# rather than imported because this checker guards documentation against the
# code, and importing the code would make a renamed value silently agree with a
# stale page instead of failing.

#: Every ``rule_id`` a proof node can carry.
_PROOF_RULE_IDS = (
    "source_fact",
    "transition_assignment",
    "equality_substitution",
    "arithmetic_evaluation",
    "interval_intersection",
    "state_domain_exhaustion",
    "definedness_failure",
    "incompatible_equalities",
    "boolean_complement",
)

#: Every way a proof step can be checked before it is published.
_PROOF_VERIFICATION_METHODS = ("core_binding", "rule_checker", "solver_entailment")

#: Every kind of node a proof graph contains.
_PROOF_NODE_KINDS = ("input", "derived", "contradiction")

#: Every classification the explanation can reach.
_CLASSIFICATIONS = (
    "kernel_conflict",
    "initialization_self_conflict",
    "initialization_domain_conflict",
    "initialization_kernel_conflict",
    "assumptions_self_conflict",
    "assumptions_domain_conflict",
    "assumptions_prefix_conflict",
)

#: The depths a caller can request, and the states the attempt can end in.
_EXPLANATION_MODES = ("none", "formal", "proof")
_EXPLANATION_STATUSES = ("complete", "partial", "unknown", "timeout")

#: Every headline the reference page must show a real example of.
#:
#: This one *is* the complete set, and it is the only constant here that can say
#: so honestly: ``_ALL_EXPLANATION_HEADLINES`` collects all six in one mapping
#: rather than leaving two of them in a renderer fallback, so "all of them" is a
#: fact about one mapping instead of a reading of scattered code.  Twice before
#: that refactor a constant here claimed a closed vocabulary the renderer did not
#: honour, and because the page was written from the same reading, the gate agreed
#: with it by construction.  Transcribe from that private mapping, not from the
#: published ``EXPLANATION_HEADLINES``, which documents itself as covering the
#: achieved depths only.
#:
#: Still transcribed rather than imported, and what protects the transcription is
#: this checker itself: a value edited here no longer appears on the page, so
#: ``--check`` reports it as undocumented on the next run.  Editing the code's
#: mapping instead fails the transcription guard in test/bmc/test_explanation.py.
#: Renaming a headline therefore has to touch three places -- the mapping, that
#: guard, and this tuple -- and skipping any one of them is caught.
#:
#: That guard does *not* cover this tuple, though an earlier version of this
#: comment claimed it did: it compares the code's mapping against a literal in
#: the test file, and the pytest boundary rules forbid a test importing tools/.
_EXPLANATION_HEADLINES = (
    "COMPLETE FORMAL DOMAIN EXPLANATION",
    "PARTIAL FORMAL DOMAIN EXPLANATION",
    "COMPLETE VERIFIED DOMAIN PROOF",
    "PARTIAL VERIFIED DOMAIN PROOF",
    "FORMAL EXPLANATION NOT ACHIEVED",
    "PROOF EXPLANATION NOT ACHIEVED",
)

#: How far minimization got, and what the proof's own minimality claims are.
_CORE_REDUCTIONS = ("raw", "partial_minimized", "subset_minimal")
_PROOF_MINIMALITY = ("subset_minimal", "dependency_pruned", "verified")

#: The published dataclasses a Python caller reads the explanation through.
_EXPLANATION_TYPES = (
    "BmcInfeasibilityExplanation",
    "BmcConflictCore",
    "BmcCoreItem",
    "BmcConflictNarrative",
    "BmcReasoningStep",
    "BmcConflictProof",
    "BmcProofNode",
    "BmcConstraintRef",
    "BmcSourceRef",
)

#: Which prose page owns which part of the vocabulary.
#:
#: Keyed by page pair, so each requirement is checked in the English page and its
#: Chinese counterpart.  Only the ``index.rst`` / ``index_zh.rst`` prose is read:
#: the same names also appear in ``bmc_cli.schema.json`` and in the generated
#: ``api_doc`` pages, and an anchor that those files could satisfy would report
#: success while the prose stayed empty.
_EXPLANATION_VOCABULARY: Dict[str, Tuple[str, ...]] = {
    "reference/bmc_results/index": (
        _PROOF_RULE_IDS
        + _PROOF_VERIFICATION_METHODS
        + _CLASSIFICATIONS
        + _CORE_REDUCTIONS
        + _PROOF_MINIMALITY
        + _EXPLANATION_STATUSES
        + _EXPLANATION_TYPES
        + _EXPLANATION_HEADLINES
        + (
            "--explain-infeasibility",
            "result.feasibility.explanation",
        )
    ),
    "reference/cli/index": (
        _EXPLANATION_MODES
        + (
            "--explain-infeasibility",
            "NO_COLOR",
        )
    ),
    "tutorials/bmc/index": (
        "--explain-infeasibility",
        "COMPLETE VERIFIED DOMAIN PROOF",
        "verification_method",
    ),
    "how_to/bmc/index": (
        "--explain-infeasibility",
        "achieved_mode",
        "requested_mode",
    ),
    "explanations/bmc_solving/index": (
        _PROOF_VERIFICATION_METHODS
        + (
            "subset_minimal",
            "structural_only",
        )
    ),
}

#: Vocabularies that must be tabulated together rather than mentioned apart.
#:
#: A reader looking up one ``rule_id`` needs to see the others to know the list
#: is closed; nine names scattered over nine sections do not answer that.  The
#: window is a single contiguous run of non-blank lines, which is what a reST
#: table or definition list is.
_TABULATED_VOCABULARY: Dict[str, Tuple[Tuple[str, ...], ...]] = {
    "reference/bmc_results/index": (
        _PROOF_RULE_IDS,
        _PROOF_VERIFICATION_METHODS,
        _PROOF_NODE_KINDS,
    ),
}

#: Rules the reference page must mark as currently unreachable.
#:
#: Four of the nine are part of the closed vocabulary a consumer has to accept
#: while no query reaches them.  Listing all nine without saying which is which
#: reads as nine available readings, so a reader who picks ``proof`` depth for one
#: of these four is surprised by a degraded result.  The measured ratio belongs to
#: the benchmark corpus rather than to a reference page, but *which* rules are
#: unreachable is a user-facing fact, and it is the kind that goes stale quietly.
_UNREACHABLE_RULES = (
    "transition_assignment",
    "equality_substitution",
    "arithmetic_evaluation",
    "boolean_complement",
)

#: Sentences that were true when written and are now misleading.
#:
#: The proof tier landed after this page described it as never closing, so the
#: page told a reader the feature does not work.  A stale claim is worse than a
#: missing one, and nothing else in this checker would notice it.
_FORBIDDEN_CLAIMS: Dict[str, Tuple[Tuple[str, str], ...]] = {
    "reference/bmc_results/index": (
        (
            "reports as unclosed rather than fabricating",
            "the proof tier does close for reachable cases; describe both the "
            "closing and the degrading outcome instead",
        ),
    ),
}


class CheckFailure(Exception):
    """Raised when one or more BMC documentation contracts fail."""


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        # OSError: the required source is missing/unreadable;
        # UnicodeDecodeError: documentation sources must be UTF-8.
        raise CheckFailure("%s cannot be read as UTF-8: %s" % (path, err))


def _extract_equations(path: Path) -> List[Tuple[str, str]]:
    lines = _read(path).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    equations: List[Tuple[str, str]] = []
    index = 0
    while index < len(lines):
        if lines[index].strip() != ".. math::":
            index += 1
            continue
        index += 1
        label = None
        while index < len(lines):
            stripped = lines[index].strip()
            if not stripped:
                index += 1
                continue
            if stripped.startswith(":"):
                if stripped.startswith(":label:"):
                    label = stripped.partition(":label:")[2].strip()
                index += 1
                continue
            break
        body: List[str] = []
        while index < len(lines) and (
            not lines[index] or lines[index].startswith("   ")
        ):
            body.append(lines[index])
            index += 1
        if label is None:
            raise CheckFailure("%s has an unlabeled math block." % path)
        latex = textwrap.dedent("\n".join(body)).strip("\n")
        latex = "\n".join(line.rstrip() for line in latex.split("\n"))
        if not latex.strip():
            raise CheckFailure("%s equation %s is empty." % (path, label))
        equations.append((label, latex))
    return equations


def _equation_references(path: Path) -> List[str]:
    """Return every ``:eq:`label``` reference in one page, in order.

    :param path: Page to scan.
    :type path: pathlib.Path
    :return: The referenced labels, duplicates kept.
    :rtype: List[str]
    """
    return re.findall(r":eq:`([^`]+)`", path.read_text(encoding="utf-8"))


def _check_equation_references(errors: List[str]) -> None:
    """Check that every equation reference resolves and every equation is cited.

    The ledger's whole job is that each labelled equation can be traced to its
    implementation, its tests, and a query that exercises it.  A typo in a
    reference points that row at an equation which does not exist, and Sphinx
    answers with a warning among the dozens a full build already emits.  So the
    label list alone is not enough to check: what the reader follows is the
    reference.

    The reverse direction matters too.  An equation nobody cites has dropped out
    of the ledger even though its ``:label:`` is still there, which the frozen
    list cannot see either.

    :param errors: Collected problems, appended to.
    :type errors: List[str]
    :return: ``None``.
    :rtype: None
    """
    known = set(_EQUATION_LABELS)
    source = _REPO_ROOT / "docs/source"
    for language, suffix in (("English", ".rst"), ("Chinese", "_zh.rst")):
        cited: set = set()
        for relative in _EQUATION_PAIRS:
            page = source / (relative + suffix)
            for label in _equation_references(page):
                cited.add(label)
                if label not in known:
                    errors.append(
                        "%s references equation %r, which no labelled block "
                        "defines." % (page.relative_to(_REPO_ROOT), label)
                    )
        # Counted across the pages together, because the labels are spread over
        # them and no single page carries the whole list.
        missing = [label for label in _EQUATION_LABELS if label not in cited]
        if missing:
            errors.append(
                "The %s pages never reference %s, so those equations are outside "
                "the ledger." % (language, ", ".join(missing))
            )


def _check_equations(errors: List[str]) -> None:
    english: List[Tuple[str, str]] = []
    chinese: List[Tuple[str, str]] = []
    source = _REPO_ROOT / "docs/source"
    for relative in _EQUATION_PAIRS:
        english.extend(_extract_equations(source / (relative + ".rst")))
        chinese.extend(_extract_equations(source / (relative + "_zh.rst")))
    english_labels = tuple(label for label, _latex in english)
    chinese_labels = tuple(label for label, _latex in chinese)
    if english_labels != _EQUATION_LABELS:
        errors.append(
            "English BMC equation ledger does not match the frozen label list."
        )
    if chinese_labels != _EQUATION_LABELS:
        errors.append(
            "Chinese BMC equation ledger does not match the frozen label list."
        )
    if english != chinese:
        errors.append("English and Chinese BMC equation labels/LaTeX differ.")


def _check_pages(errors: List[str]) -> None:
    source = _REPO_ROOT / "docs/source"
    root_en = _read(source / "index_en.rst")
    root_zh = _read(source / "index_zh.rst")
    for relative in _PAGE_PAIRS:
        english = source / (relative + ".rst")
        chinese = source / (relative + "_zh.rst")
        for path in (english, chinese):
            text = _read(path)
            if ".. toctree::" in text:
                errors.append("%s must not own sibling pages through a toctree." % path)
        if relative not in root_en:
            errors.append("English root index does not directly list %s." % relative)
        if relative + "_zh" not in root_zh:
            errors.append("Chinese root index does not directly list %s_zh." % relative)

    roadmap_requirements: Dict[str, Tuple[str, ...]] = {
        "tutorials/index.rst": ("bmc/index",),
        "tutorials/index_zh.rst": ("bmc/index_zh",),
        "how_to/index.rst": ("bmc/index",),
        "how_to/index_zh.rst": ("bmc/index_zh",),
        "explanations/index.rst": (
            "bmc_semantics/index",
            "bmc_properties/index",
            "bmc_solving/index",
        ),
        "explanations/index_zh.rst": (
            "bmc_semantics/index_zh",
            "bmc_properties/index_zh",
            "bmc_solving/index_zh",
        ),
        "reference/index.rst": ("bmc_query/index", "bmc_results/index"),
        "reference/index_zh.rst": (
            "bmc_query/index_zh",
            "bmc_results/index_zh",
        ),
    }
    for relative, required in roadmap_requirements.items():
        text = _read(source / relative)
        for target in required:
            if target not in text:
                errors.append("%s does not link to %s." % (relative, target))


def _check_readme(errors: List[str]) -> None:
    text = _read(_REPO_ROOT / "README.md")
    requirements = (
        "def int latch_engaged = 1;",
        "Locked -> Unlocked : Unlock effect {",
        "latch_engaged = 0;",
        "Unlocked -> Open : OpenDoor;",
        "Locked -> Open : ServiceOverride;",
        'active("Door.Open") && latch_engaged == 1;',
        "pyfcstm bmc -i door.fcstm -q door_latch_safety.fbmcq",
        "BMC forbid <= 2: PROPERTY DOES NOT HOLD WITHIN BOUND; COUNTEREXAMPLE FOUND",
        "Door.Locked -> Door.Open",
        "events=Door.ServiceOverride",
        "Running the same query now reports `PROPERTY GUARANTEED WITHIN BOUND; NO COUNTEREXAMPLE`",
        "--json -o bmc-result.json",
        "--color auto|always|never",
        "Every result is bounded",
        "replayed through the runtime",
    )
    for requirement in requirements:
        if requirement not in text:
            errors.append("README.md is missing BMC landing fact: %s" % requirement)
    for relative in _PAGE_PAIRS:
        url_path = relative.replace("/index", "/index.html")
        if url_path not in text:
            errors.append("README.md is missing BMC documentation link: %s" % url_path)


def _check_localized_diagrams(errors: List[str]) -> None:
    source = _REPO_ROOT / "docs/source/tutorials/bmc"
    english = _read(source / "index.rst")
    chinese = _read(source / "index_zh.rst")
    for english_name, chinese_name in _TUTORIAL_DIAGRAMS:
        if english_name + ".svg" not in english:
            errors.append("English BMC tutorial does not use %s.svg." % english_name)
        if chinese_name + ".svg" not in chinese:
            errors.append("Chinese BMC tutorial does not use %s.svg." % chinese_name)
        if chinese_name + ".svg" in english:
            errors.append(
                "English BMC tutorial uses Chinese diagram %s." % chinese_name
            )
        if english_name + ".svg" in chinese:
            errors.append(
                "Chinese BMC tutorial uses English diagram %s." % english_name
            )
        for name in (english_name, chinese_name):
            for suffix in ("", ".png", ".svg"):
                path = source / (name + suffix)
                if not path.is_file():
                    errors.append("BMC tutorial diagram asset is missing: %s" % path)


def _check_schema(errors: List[str]) -> None:
    docs_schema = _REPO_ROOT / "docs/source" / _SCHEMA_RELATIVE_PATH
    legacy_schemas = sorted(
        path
        for path in docs_schema.parent.glob("bmc_cli_*.schema.json")
        if path != docs_schema
    )
    for legacy_schema in legacy_schemas:
        errors.append("Legacy BMC JSON schema path still exists: %s" % legacy_schema)
    package_schemas = sorted((_REPO_ROOT / "pyfcstm").rglob("bmc_cli.schema.json"))
    for package_schema in package_schemas:
        errors.append(
            "BMC JSON schema must not be shipped inside pyfcstm: %s"
            % package_schema.relative_to(_REPO_ROOT)
        )
    docs_text = _read(docs_schema)
    try:
        schema = json.loads(docs_text)
    except json.JSONDecodeError as err:
        errors.append("BMC documentation schema is invalid JSON: %s" % err)
    else:
        if schema.get("$id") != _SCHEMA_ID:
            errors.append("BMC documentation schema has an unexpected $id.")
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append(
                "BMC documentation schema must retain the standard dialect URI."
            )
        properties = schema.get("properties", {})
        if any("version" in str(name).casefold() for name in properties):
            errors.append(
                "BMC documentation schema must not expose version properties."
            )
        runtime_step = schema.get("$defs", {}).get("runtimeStep", {})
        if "delta" not in runtime_step.get("required", []):
            errors.append("BMC runtime-step schema must require delta.")
    for relative in (
        "reference/bmc_results/index.rst",
        "reference/bmc_results/index_zh.rst",
    ):
        text = _read(_REPO_ROOT / "docs/source" / relative)
        if "<bmc_cli.schema.json>" not in text:
            errors.append("%s does not expose the schema download." % relative)
        schema_references = set(
            re.findall(r"bmc_cli_[A-Za-z0-9_.-]+\.schema\.json", text)
        )
        if (
            any(reference != docs_schema.name for reference in schema_references)
            or "pyfcstm/entry/bmc_cli.schema.json" in text
            or "pkgutil.get_data" in text
        ):
            errors.append("%s still describes the removed package resource." % relative)


def _visible_text(path: Path) -> str:
    """Return a page's text with reST comment blocks removed.

    A vocabulary anchor is meant to prove a reader can look the value up, and a
    comment proves the opposite: the words are in the file and not on the page.
    Reading the raw character stream cannot tell those apart -- prefixing one
    ``..`` line turned this page's whole proof-vocabulary section into a comment
    while every anchor still matched, and the rendered HTML lost the content.

    A comment is a line that starts with ``..`` and is neither a directive
    (``.. name::``) nor a target (``.. _label:``), together with the indented
    block that follows it.  Directives and targets are kept, since their content
    does render.

    :param path: Page to read.
    :type path: pathlib.Path
    :return: The page text with comment blocks blanked out.
    :rtype: str
    """
    lines = _read(path).replace("\r\n", "\n").split("\n")
    kept: List[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        is_comment_marker = stripped == ".." or (
            stripped.startswith(".. ")
            and not re.match(r"^\.\.\s+[^\s]+::", stripped)
            and not re.match(r"^\.\.\s+_", stripped)
        )
        if not is_comment_marker:
            kept.append(line)
            index += 1
            continue
        indent = len(line) - len(line.lstrip())
        kept.append("")
        index += 1
        # The comment body is every following line that is blank or indented
        # deeper than the marker.  Blank lines alone do not end it.
        while index < len(lines):
            following = lines[index]
            if not following.strip():
                kept.append("")
                index += 1
                continue
            if len(following) - len(following.lstrip()) > indent:
                kept.append("")
                index += 1
                continue
            break
    return "\n".join(kept)


def _prose_pages(relative: str) -> List[Tuple[str, Path]]:
    """Return the English and Chinese prose pages of one page pair.

    :param relative: Page pair path without the ``.rst`` suffix.
    :type relative: str
    :return: ``(label, path)`` for each page of the pair.
    :rtype: List[Tuple[str, pathlib.Path]]
    """
    source = _REPO_ROOT / "docs/source"
    return [
        (relative + ".rst", source / (relative + ".rst")),
        (relative + "_zh.rst", source / (relative + "_zh.rst")),
    ]


def _check_explanation_vocabulary(errors: List[str]) -> None:
    """Confirm each prose page documents the vocabulary it owns.

    :param errors: Accumulator the caller raises from.
    :type errors: List[str]
    :return: ``None``.
    :rtype: None
    """
    for relative, required in sorted(_EXPLANATION_VOCABULARY.items()):
        for label, path in _prose_pages(relative):
            text = _visible_text(path)
            missing = [value for value in required if value not in text]
            if missing:
                errors.append(
                    "%s does not document %s."
                    % (label, ", ".join(sorted(set(missing))))
                )


def _contiguous_blocks(text: str) -> List[str]:
    """Split page text into runs of consecutive non-blank lines.

    :param text: Page contents.
    :type text: str
    :return: One string per run, blank-line separated in the source.
    :rtype: List[str]
    """
    blocks: List[str] = []
    current: List[str] = []
    for line in text.splitlines():
        if line.strip():
            current.append(line)
            continue
        if current:
            blocks.append("\n".join(current))
            current = []
    if current:
        blocks.append("\n".join(current))
    return blocks


def _check_tabulated_vocabulary(errors: List[str]) -> None:
    """Confirm closed vocabularies appear together rather than scattered.

    :param errors: Accumulator the caller raises from.
    :type errors: List[str]
    :return: ``None``.
    :rtype: None
    """
    for relative, groups in sorted(_TABULATED_VOCABULARY.items()):
        for label, path in _prose_pages(relative):
            blocks = _contiguous_blocks(_visible_text(path))
            for group in groups:
                if any(all(value in block for value in group) for block in blocks):
                    continue
                errors.append(
                    "%s mentions %s apart rather than in one table, so a reader "
                    "cannot see that the list is closed."
                    % (label, " / ".join(group[:3]) + ("..." if len(group) > 3 else ""))
                )


def _check_forbidden_claims(errors: List[str]) -> None:
    """Confirm no page still carries a claim the implementation outgrew.

    :param errors: Accumulator the caller raises from.
    :type errors: List[str]
    :return: ``None``.
    :rtype: None
    """
    for relative, claims in sorted(_FORBIDDEN_CLAIMS.items()):
        for label, path in _prose_pages(relative):
            text = _read(path)
            for phrase, guidance in claims:
                if phrase in text:
                    errors.append("%s still claims %r; %s." % (label, phrase, guidance))


def _schema_field_vocabularies(field: str) -> List[Tuple[str, ...]]:
    """Return every closed value list the schema gives one property name.

    A name can appear in several places with different subsets -- ``status``
    means one thing for a solver check and another for an explanation, and
    ``classification`` is narrowed per conflict scope.  Returning all of them
    lets the caller decide whether it wants an exact match somewhere or a union.

    :param field: Property name to collect.
    :type field: str
    :return: One tuple per occurrence that closes its values.
    :rtype: List[Tuple[str, ...]]
    """
    schema = json.loads(_read(_REPO_ROOT / "docs/source" / _SCHEMA_RELATIVE_PATH))
    found: List[Tuple[str, ...]] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            properties = node.get("properties")
            if isinstance(properties, dict):
                spec = properties.get(field)
                if isinstance(spec, dict) and isinstance(spec.get("enum"), list):
                    found.append(
                        tuple(value for value in spec["enum"] if value is not None)
                    )
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(schema)
    return found


def _check_schema_vocabularies(errors: List[str]) -> None:
    """Confirm the schema's closed lists still match the published vocabularies.

    The reference tables written above are transcribed from the code, and the
    schema is what a machine consumer validates against.  If those two drift, a
    consumer that trusts the schema and a reader who trusts the table disagree
    about which values exist, and nothing else here would notice.

    :param errors: Accumulator the caller raises from.
    :type errors: List[str]
    :return: ``None``.
    :rtype: None
    """
    exact = {
        "rule_id": _PROOF_RULE_IDS,
        "verification_method": _PROOF_VERIFICATION_METHODS,
        "kind": _PROOF_NODE_KINDS,
        "reduction": _CORE_REDUCTIONS,
        "requested_mode": _EXPLANATION_MODES,
        "achieved_mode": _EXPLANATION_MODES,
        "status": _EXPLANATION_STATUSES,
    }
    for field, expected in sorted(exact.items()):
        occurrences = _schema_field_vocabularies(field)
        if not any(set(values) == set(expected) for values in occurrences):
            errors.append(
                "bmc_cli.schema.json has no %s enum matching the documented "
                "%d values." % (field, len(expected))
            )
    # classification is narrowed per conflict scope, which is stricter than the
    # flat vocabulary rather than inconsistent with it -- so the union is what has
    # to agree, and a value reachable in no scope would be a real gap.
    union = {
        value
        for values in _schema_field_vocabularies("classification")
        for value in values
    }
    if union != set(_CLASSIFICATIONS):
        errors.append(
            "The union of the schema's classification enums does not match the "
            "documented list; schema-only %s, documented-only %s."
            % (
                sorted(union - set(_CLASSIFICATIONS)),
                sorted(set(_CLASSIFICATIONS) - union),
            )
        )


def _check_rule_reachability(errors: List[str]) -> None:
    """Confirm the reference page still says which rules no query reaches.

    Matched against the table row's exact shape rather than against the marker
    appearing anywhere nearby.  The looser reading passed while the English
    column was missing entirely: ``"no" in block`` is satisfied by ``no value``,
    ``nodes``, or ``not``, so the check agreed with a two-column table.  Both
    languages are checked with the same predicate against their own marker word,
    because writing one check per language is how the two drift apart.

    :param errors: Accumulator the caller raises from.
    :type errors: List[str]
    :return: ``None``.
    :rtype: None
    """
    markers = {
        "reference/bmc_results/index.rst": "no",
        "reference/bmc_results/index_zh.rst": "\u5426",
    }
    for label, path in _prose_pages("reference/bmc_results/index"):
        text = _visible_text(path)
        for rule in _UNREACHABLE_RULES:
            row = "   * - ``%s``\n     - %s\n" % (rule, markers[label])
            if row in text:
                continue
            errors.append(
                "%s does not mark %s unreachable in its own table row, so the "
                "catalog reads as nine available readings." % (label, rule)
            )


def _rendered_text(html_root: Path, relative: str) -> str:
    """Return the visible text of one built page.

    Reading the source can only approximate what reaches a reader.  Sphinx
    resolves ``only``, ``include``, substitutions and metadata long after the
    text a source-level check sees, so a table inside a false ``only`` block --
    or an anchor sitting in a ``meta`` directive -- is present in the file and
    absent from the page.  Both are ordinary directives, so no amount of regex
    on the source settles it; the built page does.

    :param html_root: Directory a Sphinx HTML build wrote to.
    :type html_root: pathlib.Path
    :param relative: Page path without the ``.rst`` suffix.
    :type relative: str
    :return: The page's text with tags removed.
    :rtype: str
    :raises CheckFailure: If the page is missing from the build.
    """
    page = html_root / (relative + ".html")
    if not page.exists():
        raise CheckFailure("%s is not in the build at %s." % (relative, html_root))
    markup = page.read_text(encoding="utf-8", errors="replace")
    # Script and style content is in the file and not on the page.
    markup = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", markup)
    # Narrow to the article body before stripping tags.  The theme renders the
    # global toctree into every page's sidebar and puts page titles in the
    # next/previous links, so a value named anywhere in the project counts as
    # shown on every page -- which is the same "present but not where a reader
    # is looking" failure this function exists to catch, one layer out.
    # Cut from the body's opening tag to the footer rather than trying to match
    # its closing tag: the body contains nested divs, so a non-greedy match to
    # </div> stops at the first inner one and a greedy one runs past the footer.
    start = re.search(r'(?is)<div[^>]+\bitemprop=["\']articleBody["\']', markup)
    if start is None:
        start = re.search(r"(?is)<main\b", markup)
    if start is not None:
        rest = markup[start.end() :]
        end = re.search(r"(?is)<footer\b|</main\b", rest)
        markup = rest[: end.start()] if end else rest
    return _collapse(re.sub(r"(?s)<[^>]+>", " ", markup))


def _collapse(text: str) -> str:
    """Collapse whitespace runs so both sides of a comparison agree.

    Sphinx renders an inline literal as one ``<span class="pre">`` per word, so
    stripping tags leaves the words separated by several spaces.  Comparing a
    single-spaced needle against that finds nothing, which reads exactly like the
    value being absent.  Both the page and the value it is searched for go
    through this function, because two sides normalizing differently is how a
    check ends up covering neither.

    :param text: Text to normalize.
    :type text: str
    :return: The text with every whitespace run reduced to one space.
    :rtype: str
    """
    return re.sub(r"\s+", " ", text)


def check_rendered(html_roots: Dict[str, Path]) -> None:
    """Re-check the vocabulary anchors against built pages.

    The source-level checks stay as the fast gate.  This one asks a narrower but
    stronger question: is the value in the article body of the built page, rather
    than merely in the source that produced it.

    It does *not* establish visibility.  Stripping tags cannot resolve CSS, so an
    element the browser hides -- ``<span hidden>`` from a ``raw`` directive, or
    anything a stylesheet sets to ``display: none`` -- still counts here.  What
    computed style hides is the visual gate's question, and
    ``tools/check_bmc_math_visual.py`` is the one holding a browser.  Saying so
    is the point: a check that claimed to answer visibility while measuring DOM
    presence would be the same overclaim this slice keeps finding in prose.

    :param html_roots: ``{"en": path, "zh": path}`` for two language builds.
    :type html_roots: Dict[str, pathlib.Path]
    :return: ``None``.
    :rtype: None
    :raises CheckFailure: If a required value is absent from a built page.
    """
    errors: List[str] = []
    for relative, required in sorted(_EXPLANATION_VOCABULARY.items()):
        for language, suffix in (("en", ""), ("zh", "_zh")):
            root = html_roots.get(language)
            if root is None:
                continue
            text = _rendered_text(root, relative + suffix)
            missing = [value for value in required if _collapse(value) not in text]
            if missing:
                errors.append(
                    "%s.html in the %s build does not show %s."
                    % (relative + suffix, language, ", ".join(sorted(set(missing))))
                )
    if errors:
        raise CheckFailure(
            "BMC rendered documentation check failed:\n" + "\n".join(errors)
        )


def check() -> None:
    """Run every deterministic BMC documentation contract check."""
    errors: List[str] = []
    _check_equations(errors)
    _check_equation_references(errors)
    _check_pages(errors)
    _check_readme(errors)
    _check_localized_diagrams(errors)
    _check_schema(errors)
    _check_explanation_vocabulary(errors)
    _check_tabulated_vocabulary(errors)
    _check_forbidden_claims(errors)
    _check_schema_vocabularies(errors)
    _check_rule_reachability(errors)
    if errors:
        raise CheckFailure("BMC documentation check failed:\n" + "\n".join(errors))


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the tools-only command-line checker."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--html-root-en", type=Path)
    parser.add_argument("--html-root-zh", type=Path)
    args = parser.parse_args(argv)
    if not args.check:
        parser.error("Only --check mode is supported.")
    try:
        check()
        roots = {
            language: root
            for language, root in (("en", args.html_root_en), ("zh", args.html_root_zh))
            if root is not None
        }
        if roots:
            check_rendered(roots)
    except CheckFailure as err:
        # CheckFailure: one or more deterministic documentation contracts failed.
        print(str(err))
        return 1
    print("BMC documentation structure, diagrams, and equation ledger are up to date.")
    if args.html_root_en or args.html_root_zh:
        print("Required values are present in the built pages, not only the source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
