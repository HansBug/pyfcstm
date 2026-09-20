"""Read recorded construction as scoped frame relations and source assignments.

The renderer neither executes model statements nor proves reachability. Local
versions follow recorded write identities; expanded boundaries use the actual
submitted post-state expressions. Only display formulas receive literal cleanup.
"""

from collections import defaultdict

import z3

from pyfcstm.solver.symbols import SymbolNames

from ._construction_formula import FormulaText, atom, combine, source_expression
from .relation import BmcSymbolSource
from .domain import STATE_INIT_ID, STATE_TERMINATE_ID


def _display_names(original):
    """Use model identities without changing the shared symbol registry."""
    names = SymbolNames()
    if original is not None:
        for entry in original.entries:
            source = entry.source
            if isinstance(source, BmcSymbolSource) and source.kind == 'event':
                display = 'event("%s")@%d' % (source.name, source.step)
            elif isinstance(source, BmcSymbolSource) and source.kind in ('variable', 'input', 'parameter'):
                suffix = {'variable': source.frame, 'input': 'input%s' % source.step,
                          'parameter': 'param'}[source.kind]
                display = '%s@%s' % (source.name, suffix)
            else:
                display = entry.display
            names.register(entry.symbol, display, source)
    return names


def _location(source):
    return ('%s:%d:%d' % (source.path, source.span.line, source.span.column)
            if source.span is not None else 'source location unavailable')


def _position(path):
    return '.'.join(str(index + 1) for index in path)


def _append_formula(lines, prefix, term, renderer, *, force=False):
    parts = renderer.lines(term, width=max(32, 96 - len(prefix)), force=force)
    lines.append(prefix + parts[0])
    indent = ' ' * (len(prefix) - len(prefix.lstrip()))
    lines.extend(indent + part for part in parts[1:])


def _action_text(action, names=None, *, expanded=False, incoming=None, counters=None, renderer=None):
    """Return action text and exported local versions in the caller's scope."""
    if not isinstance(expanded, bool):
        raise TypeError('expanded must be Boolean')
    local_view = incoming is None
    names = _display_names(names) if renderer is None else names
    renderer = renderer if renderer is not None else FormulaText(names)
    counters = defaultdict(int) if counters is None else counters
    ordinal = action.index + 1
    block = action.block
    # Combo lowering can host a transition effect on a synthetic state. Its
    # containing case and statement sources supply the modeler's identity.
    owner = '' if block.runtime_role == 'transition_effect' else block.owner_state_path + ' '
    lines = ['Action %d: %s%s' % (ordinal, owner, block.runtime_role)]
    if block.action_name and not block.action_name.endswith('.<unnamed>'):
        lines.append('  Named action: ' + block.action_name)
    if block.named_ref:
        lines.append('  Call site: ' + block.named_ref)
    if block.execution_state_path and block.execution_state_path != block.owner_state_path:
        lines.append('  Execution state: ' + block.execution_state_path)
    if local_view:
        incoming = {name: '%s@entry' % name for name in action.before}
        lines.append('  Local action view: frame/case conditions are not included; @entry means this call entry.')
        for name, expression in action.before.items():
            _append_formula(lines, '  %s := ' % incoming[name], renderer.term(expression), renderer)
    if action.execution is None:
        lines.append('  Abstract hook: recorded call, no modeled writes.')
        return tuple(lines), dict(incoming)
    graph = action.execution
    refs = {index: incoming[name] for name, index in graph.initial_versions.items()}
    assignments, merges = {}, {}
    source_iter = iter(action.sources)
    for value in graph.values:
        if value.kind == 'input':
            continue
        if value.kind == 'merge':
            prior = refs[value.reads[0][1]]
            if all(refs[index] == prior for _, index in value.alternatives):
                refs[value.identifier] = prior
                continue
        counters[value.name] += 1
        refs[value.identifier] = '%s#%d' % (value.name, counters[value.name])
        if value.kind == 'assignment':
            assignments[value.path] = (value, next(source_iter))
        else:
            merges.setdefault(value.path, []).append(value)
    branches = {branch.path: branch for branch in graph.branches}

    def bindings(items):
        return {name: refs[index] for name, index in items}

    def walk(statements, prefix=(), indent='  '):
        for index, statement in enumerate(statements):
            path = (*prefix, index)
            position = _position(action.source_paths.get(path, path))
            if path in assignments:
                value, source = assignments[path]
                lines.append('%sStatement %s [%s]:' % (indent, position, _location(source)))
                lines.append(indent + '  Source: ' + str(value.source.to_ast_node()))
                lines.append('%s  %s := %s' % (indent, refs[value.identifier],
                                               source_expression(value.source.expr, bindings(value.reads))))
                if value.name not in graph.initial_versions:
                    lines.append(indent + '  Local to this action invocation.')
                if expanded and value.definedness:
                    _append_formula(lines, indent + '  Recorded translation context (not new premises): ',
                                    renderer.term(z3.And(*value.definedness)), renderer)
                domains = tuple(item.constraint for part in value.subexpressions
                                for item in part.definedness_constraints)
                if domains:
                    domain_term = renderer.term(z3.And(*domains))
                    if domain_term != atom('true'):
                        _append_formula(lines, indent + '  Required definedness: ', domain_term, renderer)
                if expanded:
                    _append_formula(lines, indent + '  Expanded value: ', renderer.term(value.expression), renderer)
            else:
                lines.append(indent + 'Conditional statement %s (ordered alternatives):' % position)
                for branch_index, source_branch in enumerate(statement.branches):
                    branch = branches[(*path, branch_index)]
                    condition = source_expression(source_branch.condition, bindings(branch.reads)) \
                        if source_branch.condition is not None else 'otherwise'
                    lines.append('%s  Branch %d (%s): %s' % (indent, branch_index + 1, branch.kind, condition))
                    _append_formula(lines, indent + '    Effective scope: ',
                                    renderer.term(z3.And(*branch.path_conditions)), renderer)
                    lines.append(indent + '    Executor reachability: %s (recorded, not rechecked).' % branch.status)
                    if branch.status == 'unsat':
                        lines.append(indent + '    No body construction: pruned by the executor.')
                    else:
                        walk(source_branch.statements, (*path, branch_index), indent + '    ')
                for value in merges.get(path, ()):
                    result = atom(refs[value.reads[0][1]])
                    for selector, version in reversed(value.alternatives):
                        result = combine('?:', (renderer.term(selector), atom(refs[version]), result))
                    _append_formula(lines, indent + 'Join %s := ' % refs[value.identifier], result, renderer)
                    if expanded:
                        _append_formula(lines, indent + '  Expanded value: ', renderer.term(value.expression), renderer)

    walk(graph.statements)
    return tuple(lines), {name: refs[index] for name, index in graph.final_versions.items()}


def _state_label(state_id, domain):
    if state_id == STATE_INIT_ID:
        return 'cold (before model entry)'
    if state_id == STATE_TERMINATE_ID:
        return 'terminated (model ended)'
    entry = domain.state_by_id(state_id)
    return entry.path + ('' if entry.is_stoppable else ' (entry control position; not a stable leaf)')


def _definitions(lines, renderer):
    for reference, term in renderer.definitions:
        _append_formula(lines, '  %s := ' % reference.text, term, renderer, force=term.operator in ('&&', '||'))


def _case_text(core, evidence, names, expanded):
    step, case = evidence.step_index, evidence.case
    relations = core.steps[step].case_relations
    by_label = {item.case.label: item for item in relations}
    relation = by_label[case.label]
    renderer = FormulaText(names, core.symbols.domain)
    lines = ['Build frame %d from frame %d using step %d events/inputs.' % (step + 1, step, step),
             'Case: ' + case.label,
             '  Start: ' + _state_label(case.source_state_id, core.symbols.domain),
             '  Condition definitions (local to this frame/case, not additional premises):']
    conditions = [evidence.antecedent] + [guard.expression for guard in evidence.guards]
    conditions.extend(by_label[label].antecedent for exclusion in case.priority_exclusions
                      for label in exclusion.excluded_case_labels)
    for index, guard in enumerate(evidence.guards):
        term = renderer.term(guard.expression)
        if term.operator in ('&&', '||', '=>', 'iff', 'xor', '?:'):
            renderer.define(guard.expression, 'guard %d after action %d' % (
                index + 1, guard.requirement.after_action_block_index))
    for exclusion in case.priority_exclusions:
        for index, label in enumerate(exclusion.excluded_case_labels):
            excluded = by_label[label]
            description = ', '.join(excluded.case.consumed_events) or (
                '%s -> %s' % (excluded.case.source_state_path, excluded.case.target_state_path))
            renderer.define(excluded.antecedent, 'accept %s [%s %d]' % (description, exclusion.reason, index + 1))
    if not expanded:
        conditions.extend(z3.And(*branch.path_conditions)
                          for action in evidence.actions if action.execution is not None
                          for branch in action.execution.branches)
        renderer.share(conditions)
    applied = renderer.define(evidence.antecedent, 'apply this case')
    _definitions(lines, renderer)
    for use in case.used_events:
        lines.append('  event("%s")@%d: event input at step %d (%s, %s).' % (
            use.path, step, step, use.reason, use.polarity))
    if case.used_events:
        lines.append('  An event occurrence alone does not imply acceptance; exclusions negate the complete acceptance condition.')
    if case.consumed_events:
        lines.append('  Events consumed under %s: %s' % (applied.text, ', '.join(case.consumed_events)))
    lines.append('  Construction under %s:' % applied.text)
    incoming = {name: renderer.inline(renderer.term(expression)) for name, expression in evidence.before.items()}
    counters = defaultdict(int)
    for anchor in range(len(evidence.actions) + 1):
        for guard in evidence.guards:
            if guard.requirement.after_action_block_index != anchor:
                continue
            lines.append('    Guard after %d action(s) [%s]:' % (anchor, _location(guard.source)))
            lines.append('      Source: ' + str(guard.requirement.expr.to_ast_node()))
            lines.append('      Reads: ' + source_expression(guard.requirement.expr, incoming))
            lines.append('      Required polarity: ' + guard.requirement.polarity)
            if expanded:
                # Use a fresh formatter: expanded evidence never uses aliases.
                raw = FormulaText(names, core.symbols.domain)
                _append_formula(lines, '      Expanded guard: ', raw.term(guard.expression), raw)
        if anchor < len(evidence.actions):
            action_lines, incoming = _action_text(evidence.actions[anchor], names, expanded=expanded,
                                                   incoming=incoming, counters=counters, renderer=renderer)
            lines.extend('    ' + line for line in action_lines)
    lines.append('  Frame boundary (all retained persistent variables):')
    terms = [renderer.state(case.target_state_id, step + 1)]
    for name in relation.post_var_exprs:
        target = renderer.term(core.symbols.frame_var(step + 1, name))
        terms.append(combine('==', (target, atom(incoming[name]))))
    terms.extend(renderer.term(item.constraint) for item in relation.definedness_constraints)
    # Terminated cases constrain event inputs as part of the actual consequent.
    post_terms = relation.consequent.children() if z3.is_and(relation.consequent) else (relation.consequent,)
    for term in post_terms:
        if z3.is_not(term):
            entry = names.lookup(term.arg(0))
            if entry is not None and getattr(entry.source, 'kind', None) == 'event':
                terms.append(renderer.term(term))
    boundary = combine('=>', (applied, combine('&&', terms)))
    _append_formula(lines, '  ', boundary, renderer, force=True)
    if expanded:
        raw = FormulaText(names, core.symbols.domain)
        lines.append('  Expanded frame boundary (no local versions or aliases):')
        _append_formula(lines, '  ', raw.term(z3.Implies(evidence.antecedent, relation.consequent)), raw, force=True)
        lines.append('  Submitted case formula (including selector binding):')
        _append_formula(lines, '  ', raw.term(evidence.expression), raw, force=True)
    return lines


def _report_text(report, *, expanded=False):
    """Read selected groups and frame relations without selecting a trace."""
    if not isinstance(expanded, bool):
        raise TypeError('expanded must be Boolean')
    core = report.core
    names = _display_names(core.symbols.names)
    renderer = FormulaText(names, core.symbols.domain)
    lines = [
        'Source construction (no reachability, coverage or UNSAT proof).',
        'Cases are conditional alternatives, not a selected execution trace.',
        'x@f is a frame value; x#n is a local definition in one frame/case, never a cross-frame reference.',
        'event("path")@k is a step k input; active("leaf")@k is the frame k state.',
        'Parameters are shared; @inputk values are fresh step inputs, not persistent frame variables.',
        'Local Boolean cleanup preserves source groups; SMT-specific numeric functions keep their exact meaning.',
        'Selected groups: ' + (', '.join(report.group_ids) or '(none)'),
    ]
    if any(entry.is_root and entry.is_stoppable for entry in core.symbols.domain.states):
        lines.append('For a leaf root, !cold distinguishes its entered position from fbmcq active(root), which also holds at cold.')
    if core.cone_slice is not None and core.cone_slice.dropped_variables:
        lines.append('Not retained by this compilation (no invented preservation): ' + ', '.join(core.cone_slice.dropped_variables))
    for group in report.groups:
        if group.category in ('transition.step', 'transition.case'):
            continue
        lines.extend(('', 'Group %s (%s)' % (group.stable_id, group.category),
                      '  Source: ' + _location(group.source_ref)))
        excerpt = core.context._source_registry.excerpt(group.source_ref)
        if excerpt:
            lines.append('  Source text: ' + excerpt)
        for expression in group.expressions:
            _append_formula(lines, '  Constraint: ', renderer.term(expression), renderer)
    for evidence in report.cases:
        lines.append('')
        lines.extend(_case_text(core, evidence, names, expanded))
    return tuple(lines)
