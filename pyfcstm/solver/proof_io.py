"""Strict loading of portable proof data, with no native solver dependency."""

from dataclasses import fields, is_dataclass
from fractions import Fraction
from typing import Union, get_type_hints

from . import proof, proof_text


def _decode(value, annotation, graph=None):
    origin = getattr(annotation, '__origin__', None)
    arguments = getattr(annotation, '__args__', ())
    if origin is Union:
        # Public evidence unions are Optional[T], never shape-dispatched payloads.
        return None if value is None else _decode(value, arguments[0], graph)
    if origin is tuple:
        if not isinstance(value, (tuple, list)):
            raise ValueError('expected an array')
        if len(arguments) == 2 and arguments[1] is Ellipsis:
            return tuple(_decode(item, arguments[0], graph) for item in value)
        if len(value) != len(arguments):
            raise ValueError('wrong tuple length')
        return tuple(_decode(item, kind, graph) for item, kind in zip(value, arguments))
    if is_dataclass(annotation):
        definitions = fields(annotation)
        if not isinstance(value, dict) or set(value) != {field.name for field in definitions}:
            raise ValueError('invalid fields for ' + annotation.__name__)
        hints = get_type_hints(annotation, vars(proof), vars(proof_text))
        decoded = {}
        for field in definitions:
            decoded[field.name] = _decode(value[field.name], hints[field.name], graph)
            if annotation is proof.UnsatReport and field.name == 'proof':
                graph = decoded['proof']
        if annotation is proof_text.ProofReading:
            decoded['graph'] = graph
        result = annotation(**decoded)
        _validate(result)
        return result
    if type(value) is not annotation:
        raise ValueError('wrong field type: expected ' + annotation.__name__)
    return value


def _choice(value, choices):
    if value not in choices:
        raise ValueError('unknown contract value: ' + str(value))


def _nonempty(value):
    if not value:
        raise ValueError('identity or description must not be empty')


def _rational(value):
    try:
        Fraction(value)
    except (ValueError, ZeroDivisionError) as error:
        # Fraction rejects malformed rational text or a zero denominator.
        raise ValueError('invalid rational: ' + value) from error


def _unique(items, attribute):
    identities = [getattr(item, attribute) for item in items]
    if len(identities) != len(set(identities)):
        raise ValueError('duplicate ' + attribute)
    return set(identities)


def _references(references, known):
    if not set(references) <= known:
        raise ValueError('unknown or non-topological reference')


def _distinct(values):
    if len(set(values)) != len(values):
        raise ValueError('duplicate identifiers')


def _acyclic(edges):
    done = set()
    active = set()
    for root in edges:
        pending = [(root, False)]
        while pending:
            key, ready = pending.pop()
            if ready:
                active.remove(key)
                done.add(key)
            elif key not in done:
                if key in active:
                    raise ValueError('cyclic reading references')
                active.add(key)
                pending.append((key, True))
                pending.extend((child, False) for child in reversed(edges[key]))


def _validate_graph(graph):
    _unique(graph.terms, 'term_id')
    nodes = _unique(graph.nodes, 'node_id')
    occurrences = _unique(graph.inputs, 'occurrence_id')
    terms = set()
    for term in graph.terms:
        _references(term.arguments, terms)
        terms.add(term.term_id)
    for item in graph.inputs:
        _references((item.term_id,), terms)
    known = set()
    hypotheses = {node.node_id for node in graph.nodes if node.rule == 'hypothesis'}
    for node in graph.nodes:
        _references(node.parents, known)
        _references(node.operands + (() if node.conclusion is None else (node.conclusion,)), terms)
        _references(node.input_occurrences, occurrences)
        _references(node.open_hypotheses + node.discharged_hypotheses, hypotheses)
        if node.certificate is not None:
            for bound in node.certificate.bounds:
                _references((bound.term_id,) + tuple(term for term, _ in bound.coefficients), terms)
        known.add(node.node_id)
    _references((graph.root_id,), nodes)
    for binding in graph.source_bindings:
        _references((binding.term_id,), terms)


def _validate_reading(reading):
    blocks = reading.blocks + reading.detail_blocks
    identities = _unique(blocks, 'block_id')
    sources = _unique(reading.sources, 'source_id')
    if reading.root_id is None:
        if blocks:
            raise ValueError('reading without a root cannot contain blocks')
        return
    _references((reading.root_id,), {block.block_id for block in reading.blocks})
    graph = reading._graph
    if graph is None:
        raise ValueError('reading blocks require a proof graph')
    nodes = {node.node_id for node in graph.nodes}
    hypotheses = {node.node_id for node in graph.nodes if node.rule == 'hypothesis'}
    visible = {block.block_id for block in reading.blocks}
    visible_hypotheses = {block.evidence_node_ids[0] for block in reading.blocks
                          if block.evidence_node_ids} & hypotheses
    terms = {term.term_id for term in graph.terms}
    occurrences = {item.occurrence_id for item in graph.inputs}
    for block in blocks:
        _references(block.premise_block_ids + block.detail_block_ids, identities)
        _references(block.claims, terms)
        _references(block.evidence_node_ids, nodes)
        _references(block.active_hypotheses, hypotheses)
        if not block.evidence_node_ids:
            raise ValueError('reading block requires evidence')
        if block.block_id in visible:
            _references(block.premise_block_ids, visible)
            _references(block.active_hypotheses, visible_hypotheses)
            if block.kind != 'domain':
                _references(graph.node(block.evidence_node_ids[0]).discharged_hypotheses,
                            visible_hypotheses)
        for link in block.source_links:
            _references((link.source_id,), sources)
            if link.term_id is not None:
                _references((link.term_id,), terms)
            if link.occurrence_id is not None:
                _references((link.occurrence_id,), occurrences)
    _acyclic({block.block_id: block.premise_block_ids + block.detail_block_ids for block in blocks})


def _validate(value):
    if isinstance(value, proof.ProofTerm):
        _nonempty(value.term_id)
        _nonempty(value.sort)
        _choice(value.operator_kind, ('builtin', 'uninterpreted'))
        _choice(value.kind, ('literal', 'algebraic', 'constant', 'application', 'variable', 'quantifier'))
        count = len(value.arguments)
        if value.kind in ('literal', 'algebraic', 'constant', 'variable') and count:
            raise ValueError('atomic term cannot have arguments')
        if value.kind == 'quantifier' and count != 1:
            raise ValueError('binder requires one body')
        if value.kind == 'application' and value.operator_kind == 'builtin':
            arities = {'not': 1, 'ite': 3, 'to_real': 1, 'uminus': 1,
                       '<': 2, '<=': 2, '>': 2, '>=': 2}
            if value.operator in arities and count != arities[value.operator]:
                raise ValueError('wrong builtin arity')
            if value.operator in ('+', '-', '*', '=', 'and', 'or', '=>', '~') and not count:
                raise ValueError('operator requires arguments')
        if value.kind == 'literal' and value.sort in ('Int', 'Real'):
            _rational(value.value)
        if value.kind == 'algebraic':
            _choice(value.sort, ('Real',))
            _nonempty(value.value)
    elif isinstance(value, proof.ProofNode):
        _nonempty(value.node_id)
        _nonempty(value.rule)
        _choice(value.local_check, ('not_run', 'checked', 'trusted', 'unsupported', 'invalid'))
        _choice(value.inference_kind, ('opaque', 'input', 'assumption', 'discharge', 'arithmetic',
                                      'logical', 'equality', 'rewrite', 'definition', 'resolution'))
    elif isinstance(value, proof.ProofParameter):
        _choice(value.kind, ('integer', 'double', 'rational', 'symbol', 'sort', 'expression', 'declaration'))
        if value.kind == 'rational':
            _rational(value.value)
    elif isinstance(value, proof.ProofInput):
        _nonempty(value.occurrence_id)
        _nonempty(value.constraint_id)
        if value.expression_index < 0:
            raise ValueError('expression_index must be nonnegative')
    elif isinstance(value, proof.SourceLink):
        _choice(value.relation, ('logical', 'construction', 'context'))
    elif isinstance(value, proof.ProofSource):
        _choice(value.relation, ('construction', 'context'))
    elif isinstance(value, proof.LinearBound):
        _choice(value.relation, ('le', 'lt', 'eq'))
        _rational(value.constant)
        for _, coefficient in value.coefficients:
            _rational(coefficient)
    elif isinstance(value, proof.ArithmeticCertificate):
        _rational(value.constant)
        if len(value.bounds) != len(value.weights):
            raise ValueError('certificate bounds and weights must align')
        for weight in value.weights:
            _rational(weight)
    elif isinstance(value, proof.ProofGraph):
        _nonempty(value.execution_id)
        _validate_graph(value)
    elif isinstance(value, proof_text.ReadingBlock):
        _nonempty(value.block_id)
        _choice(value.kind, ('opaque', 'input', 'assumption', 'discharge', 'arithmetic',
                             'logical', 'equality', 'rewrite', 'definition', 'resolution', 'domain'))
        if value.kind == 'domain':
            if not value.title_en or not value.title_zh or not value.detail_block_ids:
                raise ValueError('domain fold requires titles and details')
    elif isinstance(value, proof_text.ProofReading):
        _choice(value.status, ('complete', 'partial', 'not_requested'))
        _choice(value.solver_status, ('sat', 'unsat', 'unknown', 'timeout'))
        _validate_reading(value)
    elif isinstance(value, proof.CoreEvidence):
        _choice(value.core_check, ('verified', 'not_checked', 'sat', 'unknown', 'timeout'))
        _choice(value.subset_minimality, ('proven', 'not_proven'))
        _choice(value.reduction, ('raw', 'partial_minimized', 'subset_minimal'))
        _distinct(value.constraint_ids + value.background_ids)
        if value.core_ids is not None:
            _distinct(value.core_ids)
            _references(value.core_ids, set(value.constraint_ids))
        if (value.core_check == 'verified') != (value.core_ids is not None):
            raise ValueError('verified core requires a selected subset')
        if value.subset_minimality == 'proven' and value.core_check != 'verified':
            raise ValueError('minimality requires a verified core')
    elif isinstance(value, proof.UnsatReport):
        _nonempty(value.query_id)
        nodes = set() if value.proof is None else {node.node_id for node in value.proof.nodes}
        _references(tuple(gap.node_id for gap in value.gaps if gap.node_id is not None), nodes)
        _choice(value.solver_status, ('sat', 'unsat', 'unknown', 'timeout'))
        _choice(value.proof_status, ('captured', 'invalid', 'unavailable', 'not_requested'))
        _choice(value.proof_scope, ('none', 'full', 'core'))
        _choice(value.input_check, ('not_run', 'passed', 'failed'))
        _choice(value.scope_check, ('not_run', 'passed', 'partial', 'failed'))
        _choice(value.rule_check, ('not_run', 'complete', 'partial', 'failed'))
        _choice(value.reading_status, ('not_requested', 'complete', 'partial'))
        _choice(value.source_status, ('absent', 'complete', 'partial'))
        if value.reading is not None and (value.reading.query_id != value.query_id or
                value.reading.solver_status != value.solver_status or value.reading.status != value.reading_status or
                value.reading.gaps != value.gaps):
            raise ValueError('report and reading disagree')
        if (value.proof is not None) != (value.proof_status in ('captured', 'invalid')):
            raise ValueError('proof availability and status disagree')
        if (value.proof is None) != (value.proof_scope == 'none'):
            raise ValueError('proof scope and availability disagree')
        if value.proof is not None and value.solver_status != 'unsat':
            raise ValueError('proof requires an UNSAT result')
        if value.proof_scope == 'core' and (value.core is None or value.full_proof is None):
            raise ValueError('reduced proof requires the original graph and core')
        if value.proof is not None and value.scope_check == 'passed':
            root = value.proof.node(value.proof.root_id)
            term = None if root.conclusion is None else value.proof.term(root.conclusion)
            if (term is None or term.kind != 'literal' or term.sort != 'Bool' or
                    term.value != 'false' or root.open_hypotheses):
                raise ValueError('closed refutation must conclude False')
        if value.reading_status == 'complete' and (value.scope_check != 'passed' or
                value.proof_status != 'captured' or value.gaps):
            raise ValueError('complete reading requires a closed proof without gaps')


def load_report(data):
    """Decode exactly the public report dataclasses and check graph references."""
    return _decode(data, proof.UnsatReport)
