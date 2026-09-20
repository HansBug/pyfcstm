"""Read construction records using source positions and conditional frame links.

This renderer does not execute model statements or discover logical consequences.
It retains native formulas and uses the recorded value graph for read references;
equal expressions never stand in for execution identity.
"""

import z3

from pyfcstm.solver.symbols import SymbolNames

from .relation import BmcSymbolSource
from .domain import STATE_INIT_ID, STATE_TERMINATE_ID


def _display_names(original):
    """Use authored event paths without changing the shared symbol registry."""
    names = SymbolNames()
    if original is not None:
        for entry in original.entries:
            source = entry.source
            if isinstance(source, BmcSymbolSource) and source.kind == 'event':
                display = 'event("%s")@step%d' % (source.name, source.step)
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


def _split_lines(lines):
    for line in lines:
        parts = line.split('\n')
        yield parts[0]
        indent = ' ' * (len(line) - len(line.lstrip()) + 2)
        for part in parts[1:]:
            yield indent + part


def _expanded_lines(value, names):
    lines = ['expanded: ' + names.render(value)]
    simplified = z3.simplify(value)
    if not z3.eq(simplified, value):
        lines.append('Z3 simplification: ' + names.render(simplified))
    return lines


def _action_text(action, names=None, *, expanded=False, incoming=None):
    """Return local text and exported references; callers supply case context."""
    if not isinstance(expanded, bool):
        raise TypeError('expanded must be Boolean')
    names = _display_names(names) if incoming is None else names
    ordinal = action.index + 1
    block = action.block
    lines = ['Action %d: %s %s' % (ordinal, block.owner_state_path, block.runtime_role)]
    if block.action_name and not block.action_name.endswith(".<unnamed>"):
        lines.append('  Named action: ' + block.action_name)
    if block.named_ref:
        lines.append('  Call site: ' + block.named_ref)
    if block.execution_state_path and block.execution_state_path != block.owner_state_path:
        lines.append('  Execution state: ' + block.execution_state_path)
    local_view = incoming is None
    if local_view:
        incoming = {name: '%s [action %d entry]' % (name, ordinal) for name in action.before}
        lines.append('  Local view: enclosing frame/case conditions are not shown.')
        for name, expression in (action.before.items() if action.execution is not None else ()):
            lines.append('  Entry: %s = %s' % (incoming[name], names.render(expression)))
    if action.execution is None:
        lines.append('  Abstract hook: recorded call, no modeled writes.')
        return tuple(_split_lines(lines)), dict(incoming)
    graph = action.execution
    refs = {index: incoming[name] for name, index in graph.initial_versions.items()}
    assignments = {}
    merges = {}
    source_iter = iter(action.sources)
    for value in graph.values:
        if value.kind == 'input':
            continue
        original = action.source_paths[value.path]
        position = _position(original)
        if value.kind == 'assignment':
            refs[value.identifier] = '%s [action %d, after statement %s]' % (value.name, ordinal, position)
            assignments[value.path] = (value, next(source_iter))
        else:
            prior = refs[value.reads[0][1]]
            if all(refs[index] == prior for _, index in value.alternatives):
                # A branch join for an untouched value is just preservation.
                # Identity assignments still have distinct references above.
                refs[value.identifier] = prior
                continue
            refs[value.identifier] = '%s [action %d, after join %s]' % (value.name, ordinal, position)
            merges.setdefault(value.path, []).append(value)
    branches = {branch.path: branch for branch in graph.branches}

    def reads(items):
        return ', '.join('%s <- %s' % (name, refs[index]) for name, index in items) or '(none)'

    def walk(statements, prefix=(), indent='  '):
        for index, statement in enumerate(statements):
            path = (*prefix, index)
            position = _position(action.source_paths.get(path, path))
            if path in assignments:
                value, source = assignments[path]
                lines.append('%sStatement %s: %s [%s]' % (
                    indent, position, value.source.to_ast_node(), _location(source)))
                lines.append(indent + '  reads: ' + reads(value.reads))
                lines.append(indent + '  produces: ' + refs[value.identifier])
                if value.name not in graph.initial_versions:
                    lines.append(indent + '  local to this action invocation')
                if value.path_conditions:
                    lines.append(indent + '  scope: ' + names.render(z3.And(*value.path_conditions)))
                domains = (*value.definedness, *(item.constraint for part in value.subexpressions
                                                for item in part.definedness_constraints))
                if domains:
                    lines.append(indent + '  recorded definedness: ' + names.render(z3.And(*domains)))
                if expanded:
                    lines.extend(indent + '  ' + line for line in _expanded_lines(value.expression, names))
            else:
                lines.append(indent + 'Conditional statement %s: ordered alternatives (not sequential execution).' % position)
                for branch_index, source_branch in enumerate(statement.branches):
                    branch = branches[(*path, branch_index)]
                    lines.append('%s  Branch %d (%s): %s' % (
                        indent, branch_index + 1, branch.kind,
                        source_branch.condition.to_ast_node() if source_branch.condition is not None else 'otherwise'))
                    lines.append(indent + '    condition reads: ' + reads(branch.reads))
                    lines.append(indent + '    effective scope: ' + names.render(z3.And(*branch.path_conditions)))
                    lines.append(indent + '    executor reachability: ' + branch.status + ' (not rechecked by rendering)')
                    if branch.status == 'unsat':
                        lines.append(indent + '    No body construction: pruned by the executor.')
                    else:
                        walk(source_branch.statements, (*path, branch_index), indent + '    ')
                for value in merges.get(path, ()):
                    lines.append(indent + 'Join: ' + refs[value.identifier])
                    for selector, version in value.alternatives:
                        lines.append(indent + '  when %s: %s' % (names.render(selector), refs[version]))
                    lines.append(indent + '  otherwise preserve: ' + refs[value.reads[0][1]])
                    if expanded:
                        lines.extend(indent + '  ' + line for line in _expanded_lines(value.expression, names))

    walk(graph.statements)
    return tuple(_split_lines(lines)), {name: refs[index] for name, index in graph.final_versions.items()}


def _state_label(state_id, domain):
    if state_id == STATE_INIT_ID:
        return 'cold (before model entry)'
    if state_id == STATE_TERMINATE_ID:
        return 'terminated'
    return domain.state_by_id(state_id).path


def _formula_lines(title, expression, names, domain):
    """Annotate actual state comparisons, never reinterpret unrelated integers."""
    lines = [title + names.render(expression)]
    meanings = set()
    pending = [expression]
    seen = set()
    while pending:
        node = pending.pop()
        if node.get_id() in seen:
            continue
        seen.add(node.get_id())
        children = node.children()
        pending.extend(children)
        if node.decl().kind() not in (z3.Z3_OP_EQ, z3.Z3_OP_DISTINCT) or len(children) != 2:
            continue
        for slot, code in (children, children[::-1]):
            entry = names.lookup(slot)
            if entry is not None and getattr(entry.source, 'kind', None) == 'state' and z3.is_int_value(code):
                meanings.add((entry.source.frame, code.as_long(), _state_label(code.as_long(), domain)))
    lines.extend('  state[%d] code %d means %s' % meaning for meaning in sorted(meanings))
    return lines


def _report_text(report, *, expanded=False):
    """Read original groups and case boundaries without choosing an execution."""
    if not isinstance(expanded, bool):
        raise TypeError('expanded must be Boolean')
    core = report.core
    names = _display_names(core.symbols.names)
    domain = core.symbols.domain
    lines = [
        'Source construction (no reachability, coverage or UNSAT proof).',
        'Cases are conditional alternatives, not a selected execution trace.',
        'Frame values connect adjacent steps; action references are local to their case.',
        'Selected groups: ' + (', '.join(report.group_ids) or '(none)'),
    ]
    for group in report.groups:
        if group.category in ('transition.step', 'transition.case'):
            continue
        lines.append('')
        lines.append('Group %s (%s)' % (group.stable_id, group.category))
        source = group.source_ref
        lines.append('  Source: ' + _location(source))
        excerpt = core.context._source_registry.excerpt(source)
        if excerpt:
            lines.append('  Source text: ' + excerpt)
        for expression in group.expressions:
            lines.extend('  ' + line for line in _formula_lines('Constraint: ', expression, names, domain))
    for evidence in report.cases:
        step = evidence.step_index
        case = evidence.case
        relations = core.steps[step].case_relations
        relation = next(item for item in relations if item.case is case)
        lines.extend(('', 'Step %d: frame %d -> frame %d' % (step, step, step + 1),
                      'Case: ' + case.label,
                      '  Start control state: ' + _state_label(case.source_state_id, domain),
                      '  End control state if this case applies: ' + _state_label(case.target_state_id, domain)))
        lines.extend('  ' + line for line in _formula_lines('Effective condition: ', evidence.antecedent, names, domain))
        for use in case.used_events:
            lines.append('  Event read: %s at step %d (%s, %s).' % (use.path, step, use.reason, use.polarity))
        if case.used_events:
            lines.append('  Event reads alone do not imply occurrence or acceptance; use the effective condition above.')
        if case.consumed_events:
            lines.append('  Events consumed if this case applies: ' + ', '.join(case.consumed_events))
        for exclusion in case.priority_exclusions:
            for label in exclusion.excluded_case_labels:
                excluded = next(item for item in relations if item.case.label == label)
                lines.append('  Excluded acceptance (%s): %s' % (exclusion.reason, label))
                lines.extend('    ' + line for line in _formula_lines(
                    'Acceptance condition (embedded dependency, not an extra premise): ',
                    excluded.antecedent, names, domain))
        incoming = {name: names.render(expression) for name, expression in evidence.before.items()}
        for anchor in range(len(evidence.actions) + 1):
            for guard in evidence.guards:
                if guard.requirement.after_action_block_index != anchor:
                    continue
                lines.append('  Guard after %d action(s): %s [%s]' % (
                    anchor, guard.requirement.expr.to_ast_node(), _location(guard.source)))
                lines.append('    polarity: ' + guard.requirement.polarity)
                if expanded:
                    lines.append('    encoding use: %s; transition: %s' % (
                        guard.requirement.reason, guard.requirement.transition_label))
                lines.append('    reads: ' + (', '.join('%s <- %s' % (var.name, incoming[var.name])
                                                       for var in guard.requirement.expr.list_variables()) or '(none)'))
                lines.append('    compiled guard: ' + names.render(guard.expression))
            if anchor < len(evidence.actions):
                action_lines, incoming = _action_text(
                    evidence.actions[anchor], names, expanded=expanded, incoming=incoming)
                lines.extend('  ' + line for line in action_lines)
        lines.append('  Frame boundary under this case:')
        lines.append('    state[%d] = %s' % (step + 1, _state_label(case.target_state_id, domain)))
        for name, expression in relation.post_var_exprs.items():
            target = names.render(core.symbols.frame_var(step + 1, name))
            unchanged = incoming[name] == names.render(evidence.before[name])
            lines.append('    %s = %s%s' % (target, incoming[name], ' (preserved)' if unchanged else ''))
            if expanded:
                lines.append('      compiled post value: ' + names.render(expression))
        post_terms = relation.consequent.children() if z3.is_and(relation.consequent) else (relation.consequent,)
        for term in post_terms:
            if z3.is_not(term):
                entry = names.lookup(term.arg(0))
                if entry is not None and getattr(entry.source, 'kind', None) == 'event':
                    lines.append('    Boundary event requirement: ' + names.render(term))
        for constraint in relation.definedness_constraints:
            lines.append('  Required definedness under this case: ' + names.render(constraint.constraint))
        if expanded:
            lines.extend('  ' + line for line in _formula_lines('Submitted formula: ', evidence.expression, names, domain))
    return tuple(_split_lines(lines))
