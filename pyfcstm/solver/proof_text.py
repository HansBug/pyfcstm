"""Evidence-preserving readable deductions, usable without a native solver."""

from dataclasses import InitVar, asdict, dataclass, replace
from fractions import Fraction
from types import MappingProxyType
from typing import Callable, Optional, Tuple

from .proof import ProofGap, ProofGraph, SourceAdapter, SourceDescription, SourceLink


@dataclass(frozen=True)
class FoldProposal:
    """A domain title for an exact, connected slice of readable evidence.

    :param root_id: Selected slice's conclusion block.
    :param block_ids: Blocks to replace, including the root.
    :param premise_block_ids: All external premises of the selected slice.
    :param claims: Exactly the root's existing claims.
    :param active_hypotheses: Exactly the root's existing open hypotheses.
    :param title_en: English presentation title, supplied by trusted caller code.
    :param title_zh: Chinese presentation title, supplied by trusted caller code.
    """

    root_id: str
    block_ids: Tuple[str, ...]
    premise_block_ids: Tuple[str, ...]
    claims: Tuple[str, ...]
    active_hypotheses: Tuple[str, ...]
    title_en: str
    title_zh: str


@dataclass(frozen=True)
class ReadingFolder:
    """Propose domain folds; the reader validates every structural boundary.

    :param propose: Callable taking a reading and returning fold proposals.
        Titles are trusted presentation metadata, never additional premises.
        A proposal referring to blocks removed by an earlier fold is rejected.
    """

    propose: Callable

    def __post_init__(self):
        if not callable(self.propose):
            raise TypeError('propose must be callable')


@dataclass(frozen=True)
class ReadingBlock:
    """A readable inference with exact premises, hypotheses and native evidence.

    :param block_id: Identity in the containing reading.
    :param kind: Semantic inference category.
    :param claims: Concluded term identifiers.
    :param premise_block_ids: Direct readable premises.
    :param active_hypotheses: Native local hypotheses still in scope.
    :param evidence_node_ids: Native steps including hidden mechanical rewrites.
    :param source_links: Explicit source relationships.
    :param detail_block_ids: Original blocks hidden by a domain fold.
    :param title_en: Optional caller-supplied English domain title.
    :param title_zh: Optional caller-supplied Chinese domain title.
    """

    block_id: str
    kind: str
    claims: Tuple[str, ...]
    premise_block_ids: Tuple[str, ...]
    active_hypotheses: Tuple[str, ...]
    evidence_node_ids: Tuple[str, ...]
    source_links: Tuple[SourceLink, ...] = ()
    detail_block_ids: Tuple[str, ...] = ()
    title_en: Optional[str] = None
    title_zh: Optional[str] = None


@dataclass(frozen=True)
class ProofReading:
    """A complete or explicitly partial reading of shared proof evidence.

    :param query_id: Exact query identity.
    :param solver_status: Solver outcome, not a property verdict.
    :param root_id: Refutation reading block, or ``None`` when unavailable.
    :param status: ``complete``, ``partial`` or ``not_requested``.
    :param blocks: Ordered readable inferences.
    :param sources: Portable source descriptions.
    :param gaps: Explicit missing evidence.
    :param graph: Shared proof graph, bound for reading but not serialized twice.
    :param detail_blocks: Original reading blocks retained for fold expansion.
    """

    query_id: str
    solver_status: str
    root_id: Optional[str]
    status: str
    blocks: Tuple[ReadingBlock, ...]
    sources: Tuple[SourceDescription, ...]
    gaps: Tuple[ProofGap, ...]
    graph: InitVar[Optional[ProofGraph]]
    detail_blocks: Tuple[ReadingBlock, ...] = ()

    def __post_init__(self, graph):
        object.__setattr__(self, '_graph', graph)
        object.__setattr__(self, '_blocks', MappingProxyType(
            {b.block_id: b for b in self.blocks + self.detail_blocks}))
        object.__setattr__(self, '_sources', MappingProxyType({s.source_id: s for s in self.sources}))

    def get_block(self, block_id: str) -> ReadingBlock:
        """Return one block, raising :class:`KeyError` for an unknown identity."""
        return self._blocks[block_id]

    def expand(self, block_id: str) -> Tuple[ReadingBlock, ...]:
        """Expand a domain fold, otherwise return direct readable premises."""
        block = self.get_block(block_id)
        return tuple(self.get_block(key) for key in (block.detail_block_ids or block.premise_block_ids))

    def get_source(self, source_id: str) -> SourceDescription:
        """Return one source, raising :class:`KeyError` for an unknown identity."""
        return self._sources[source_id]

    def to_canonical(self) -> dict:
        """Return reading data whose term/evidence references use the report graph."""
        return asdict(self)

    def to_text(self, language: str = 'en') -> str:
        """Render all readable deductions in English or Chinese.

        :param language: ``en`` or ``zh``.
        :return: Plain text, without terminal escapes or truncated deductions.
        :raises ValueError: For an unsupported language.
        """
        if language not in ('en', 'zh'):
            raise ValueError('language must be en or zh')
        return _render(self, language)


def _term_texts(graph):
    values = {}
    for term in graph.terms:
        args = [values[child] for child in term.arguments]
        if term.kind in ('constant', 'literal', 'algebraic'):
            text = term.value
        elif term.parameters:
            text = '%s[%s](%s)' % (term.operator, ', '.join(parameter.value for parameter in term.parameters),
                                   ', '.join(args))
        elif term.operator_kind == 'uninterpreted':
            text = '%s(%s)' % (term.operator, ', '.join(args))
        elif term.kind == 'variable':
            text = '#' + term.value
        elif term.kind == 'quantifier':
            text = '(%s %s. %s)' % (term.operator, ', '.join('%s: %s' % item for item in term.bindings), args[0])
        elif term.operator == 'not':
            text = 'not (%s)' % args[0]
        elif term.operator == 'ite':
            text = '(if %s then %s else %s)' % tuple(args)
        elif term.operator in ('=', '<', '<=', '>', '>=', '+', '*', 'and', 'or', '=>', '~'):
            text = '(' + (' %s ' % term.operator).join(args) + ')'
        elif term.operator in ('-', 'uminus'):
            text = '(-%s)' % args[0] if len(args) == 1 else '(' + ' - '.join(args) + ')'
        else:
            text = '%s(%s)' % (term.operator, ', '.join(args))
        values[term.term_id] = text
    return values


def _linear_text(bound, terms):
    parts = []
    for term_id, value in bound.coefficients:
        coefficient = Fraction(value)
        parts.append(terms[term_id] if coefficient == 1 else '%s * %s' % (value, terms[term_id]))
    if Fraction(bound.constant) or not parts:
        parts.append(bound.constant)
    relation = {'le': '<=', 'lt': '<', 'eq': '='}[bound.relation]
    return '%s %s 0' % (' + '.join(parts), relation)


def _render(reading, language):
    zh = language == 'zh'
    choose = lambda english, chinese: chinese if zh else english
    lines = [choose('Query: ', '查询：') + reading.query_id,
             choose('Solver result: ', '求解结果：') + reading.solver_status.upper(),
             choose('Reading: ', '阅读完整度：') + reading.status, '']
    if reading.root_id is None:
        lines.append(choose('No refutation is available.', '没有可用的反证。'))
        return '\n'.join(lines) + '\n'
    graph = reading._graph
    terms = _term_texts(graph)
    inputs = {item.occurrence_id: item for item in graph.inputs}
    labels = {block.block_id: 'P%d' % (i + 1) for i, block in enumerate(reading.blocks)}
    node_labels = {block.evidence_node_ids[0]: labels[block.block_id] for block in reading.blocks}
    titles = {
        'input': choose('Input', '输入条件'), 'assumption': choose('Assume', '局部假设'),
        'discharge': choose('Discharge local assumptions', '关闭局部假设'),
        'arithmetic': choose('Exact linear combination', '精确线性组合'),
        'resolution': choose('Resolve the clauses', '消解子句'),
        'definition': choose('Internal definition / defining clause', '内部定义／定义子句'),
        'logical': choose('Logical consequence', '逻辑推导'),
        'equality': choose('Equality substitution', '等式替换'),
        'rewrite': choose('Equivalent rewriting', '等价改写'),
        'opaque': choose('Unsupported inference', '尚未解释的推导'),
    }
    for block in reading.blocks:
        node = graph.node(block.evidence_node_ids[0])
        title = choose(block.title_en, block.title_zh) if block.kind == 'domain' else titles[block.kind]
        lines.append('%s  %s' % (labels[block.block_id], title))
        if block.premise_block_ids:
            lines.append('  ' + choose('From: ', '根据：') + ', '.join(labels[key] for key in block.premise_block_ids))
        if node.input_occurrences:
            origins = tuple(dict.fromkeys(inputs[key].constraint_id for key in node.input_occurrences))
            lines.append('  ' + choose('Input origins: ', '输入来源：') + ', '.join(origins))
            if len(origins) > 1:
                lines.append('  ' + choose('These are alternative occurrences of the same formula.',
                                          '这些是同一公式的不同来源候选。'))
        if block.active_hypotheses:
            lines.append('  ' + choose('Under assumptions: ', '当前假设：') + ', '.join(
                node_labels[key] for key in block.active_hypotheses))
        if node.discharged_hypotheses and block.kind != 'domain':
            lines.append('  ' + choose('Closed: ', '已关闭：') + ', '.join(
                node_labels[key] for key in node.discharged_hypotheses))
        if node.certificate is not None and block.kind != 'domain':
            certificate = node.certificate
            temporary = tuple(bound for bound in certificate.bounds if bound.negated)
            if temporary:
                lines.append('  ' + choose('To refute the negated conclusion, temporarily assume:',
                                          '为反驳结论的否定，暂时假设：'))
                for bound in temporary:
                    literal = graph.term(bound.term_id)
                    assumption = (terms[literal.arguments[0]] if literal.operator == 'not'
                                  else 'not (%s)' % terms[bound.term_id])
                    lines.append('    ' + assumption)
            for bound, weight in zip(certificate.bounds, certificate.weights):
                lines.append('  %s * [%s]' % (weight, _linear_text(bound, terms)))
            relation = '<' if certificate.strict else '<='
            lines.append('  ' + choose('Sum: ', '相加得到：') + '%s %s 0; ' % (certificate.constant, relation) +
                         choose('contradiction.', '矛盾。'))
            if temporary:
                lines.append('  ' + choose('Discharge these temporary assumptions.', '关闭上述临时假设。'))
        for claim in block.claims:
            lines.append('  ' + choose('Therefore: ', '得到：') + terms[claim])
        if block.detail_block_ids:
            lines.append('  ' + choose('Expandable proof steps: ', '可展开的证明步骤：') +
                         str(len(block.detail_block_ids)))
        for link in block.source_links:
            source = reading.get_source(link.source_id)
            location = '' if source.document_id is None else ' [%s]' % source.document_id
            prefix = {'logical': choose('Source: ', '来源：'),
                      'construction': choose('Construction source: ', '构造来源：'),
                      'context': choose('Context source: ', '上下文来源：')}[link.relation]
            lines.append('  ' + prefix + source.title + location)
        lines.append('')
    lines.append(choose('Conclusion: the submitted conjunction is inconsistent.',
                        '结论：提交的条件合取不可满足。'))
    if reading.gaps:
        lines.append(choose('Unexplained or invalid evidence:', '尚未解释或无效的证据：'))
        lines.extend('  %s: %s' % (gap.reason, gap.detail) for gap in reading.gaps)
    return '\n'.join(lines) + '\n'


def _fold(reading, proposal):
    if not isinstance(proposal, FoldProposal):
        raise TypeError('reading folder must return FoldProposal objects')
    blocks = {block.block_id: block for block in reading.blocks}
    selected = set(proposal.block_ids)
    if len(selected) != len(proposal.block_ids):
        raise ValueError('fold contains duplicate blocks')
    if selected - set(blocks):
        raise ValueError('fold contains an unknown block')
    if proposal.root_id not in selected:
        raise ValueError('fold root must belong to the selected blocks')
    root = blocks[proposal.root_id]
    if proposal.claims != root.claims:
        raise ValueError('fold must preserve root claims')
    if proposal.active_hypotheses != root.active_hypotheses:
        raise ValueError('fold must preserve root hypotheses')
    if not all(isinstance(title, str) and title.strip() for title in (proposal.title_en, proposal.title_zh)):
        raise ValueError('fold title must be nonempty in both languages')
    reachable, pending = set(), [proposal.root_id]
    while pending:
        key = pending.pop()
        if key not in reachable:
            reachable.add(key)
            pending.extend(parent for parent in blocks[key].premise_block_ids if parent in selected)
    if reachable != selected:
        raise ValueError('fold blocks must form a connected proof slice')
    boundary = {parent for key in selected for parent in blocks[key].premise_block_ids if parent not in selected}
    if (set(proposal.premise_block_ids) != boundary or
            len(proposal.premise_block_ids) != len(boundary)):
        raise ValueError('fold must preserve all external premises')
    covered = tuple(block for block in reading.blocks if block.block_id in selected)
    hidden_hypotheses = {node for block in covered if block.kind == 'assumption'
                         for node in block.evidence_node_ids}
    for block in reading.blocks:
        if block.block_id not in selected:
            if set(block.premise_block_ids) & (selected - {proposal.root_id}):
                raise ValueError('fold would hide a premise used outside its root')
            if set(block.active_hypotheses) & hidden_hypotheses:
                raise ValueError('fold would hide active hypotheses used outside its root')
    if set(root.active_hypotheses) & hidden_hypotheses:
        raise ValueError('fold would hide active hypotheses at its root')
    folded_id = 'fold:' + root.block_id
    evidence = tuple(dict.fromkeys(root.evidence_node_ids + tuple(
        key for block in covered for key in block.evidence_node_ids)))
    folded = ReadingBlock(folded_id, 'domain', root.claims, proposal.premise_block_ids,
                          root.active_hypotheses, evidence,
                          tuple(dict.fromkeys(link for block in covered for link in block.source_links)),
                          tuple(block.block_id for block in covered), proposal.title_en, proposal.title_zh)
    result = []
    for block in reading.blocks:
        if block.block_id == root.block_id:
            result.append(folded)
        elif block.block_id not in selected:
            result.append(replace(block, premise_block_ids=tuple(
                folded_id if key == root.block_id else key for key in block.premise_block_ids)))
    return replace(reading, graph=reading._graph, blocks=tuple(result),
                   root_id=folded_id if reading.root_id == root.block_id else reading.root_id,
                   detail_blocks=reading.detail_blocks + covered)


def build_reading(report, query, extensions, budget):
    """Fold mechanical steps while retaining their exact external premises."""
    graph = report.proof
    if graph is None or report.proof_status != 'captured':
        return ProofReading(query.query_id, report.solver_status, None, 'not_requested',
                            (), (), report.gaps, graph), 'absent'
    adapter = extensions.source_adapter or SourceAdapter()
    sources, source_by_group = {}, {}
    def register(source):
        if not isinstance(source, SourceDescription):
            raise TypeError('source adapter must return SourceDescription')
        if source.source_id in sources and sources[source.source_id] != source:
            raise ValueError('conflicting source descriptions: ' + source.source_id)
        sources[source.source_id] = source

    for group in query.background + query.constraints:
        budget.checkpoint('proof reading')
        if group.source is not None:
            source = adapter.describe(group.source)
            register(source)
            source_by_group[group.stable_id] = source.source_id
    term_links = {}
    for binding in graph.source_bindings:
        register(binding.description)
        term_links.setdefault(binding.term_id, []).append(SourceLink(
            binding.description.source_id, binding.relation, term_id=binding.term_id))
    # Only exact term occurrences in a displayed claim carry construction links.
    # Parent proof dependencies remain separate; a source is not thereby necessary.
    for term in graph.terms:
        budget.checkpoint('proof reading')
        term_links[term.term_id] = tuple(dict.fromkeys(
            tuple(term_links.get(term.term_id, ())) + tuple(
                link for child in term.arguments for link in term_links[child])))
    by_occurrence = {item.occurrence_id: item for item in graph.inputs}
    hidden_rules = {'rewrite', 'refl', 'symm', 'trans', 'monotonicity', 'commutativity', 'mp', 'mp~'}
    hidden = {node.node_id for node in graph.nodes if node.rule in hidden_rules and node.node_id != graph.root_id}
    # Retain the formulas at arithmetic boundaries. Otherwise a linear sum can
    # use a rewritten inequality that none of its displayed premises states.
    boundaries = {parent for node in graph.nodes if node.certificate is not None for parent in node.parents}
    hidden -= {key for key in boundaries if not any(
        graph.node(parent).conclusion == graph.node(key).conclusion for parent in graph.node(key).parents)}
    frontiers, slices, blocks = {}, {}, []
    identities = {node.node_id: 'p%d' % index for index, node in enumerate(graph.nodes) if node.node_id not in hidden}
    used_groups = set()
    for node in graph.nodes:
        budget.checkpoint('proof reading')
        premises = tuple(dict.fromkeys(key for parent in node.parents for key in frontiers[parent]))
        evidence = (node.node_id,) + tuple(dict.fromkeys(
            key for parent in node.parents if parent in hidden for key in slices[parent]))
        slices[node.node_id] = evidence
        if node.node_id in hidden:
            frontiers[node.node_id] = premises
            continue
        frontiers[node.node_id] = (node.node_id,)
        links = []
        for occurrence in node.input_occurrences:
            group_id = by_occurrence[occurrence].constraint_id
            used_groups.add(group_id)
            if group_id in source_by_group:
                links.append(SourceLink(source_by_group[group_id], 'logical', occurrence))
        if node.conclusion is not None:
            links.extend(term_links[node.conclusion])
        blocks.append(ReadingBlock(
            identities[node.node_id], node.inference_kind,
            () if node.conclusion is None else (node.conclusion,),
            tuple(identities[key] for key in premises), node.open_hypotheses, evidence, tuple(links),
        ))
    status = 'partial' if report.gaps or report.scope_check != 'passed' else 'complete'
    source_status = ('absent' if not sources else
                     ('complete' if used_groups <= set(source_by_group) else 'partial'))
    reading = ProofReading(query.query_id, report.solver_status, identities[graph.root_id], status,
                           tuple(blocks), tuple(sources.values()), report.gaps, graph)
    for folder in extensions.reading_folders:
        if not isinstance(folder, ReadingFolder):
            raise TypeError('reading_folders must contain ReadingFolder objects')
        for proposal in folder.propose(reading):
            budget.checkpoint('proof reading')
            reading = _fold(reading, proposal)
    budget.checkpoint('proof reading')
    return reading, source_status
