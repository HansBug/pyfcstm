"""Run the documented solver examples and print their actual readable proofs."""

import argparse

import z3

from pyfcstm.solver import SymbolNames, UnsatConstraint, UnsatQuery
from pyfcstm.solver.proof import (
    FoldProposal, ProofExtensions, ReadingFolder, SourceAdapter, SourceBinding,
    SourceDescription, explain_unsat,
)


class AllocationSources(SourceAdapter):
    """Translate application handles and bind an exact allocation expression."""

    def __init__(self, allocation):
        self.allocation = allocation

    def describe(self, handle):
        return SourceDescription(handle['key'], handle['title'], 'config:allocation',
                                 excerpt=handle['expression'])

    def bindings(self):
        return (SourceBinding(self.allocation, {
            'key': 'allocation', 'title': 'Requested allocation', 'expression': 'allocation',
        }, 'construction'),)


def build(case):
    """Return an exact query, display names and an optional application adapter."""
    before, after, noise = z3.Ints('before after noise')
    names = SymbolNames()
    names.register(before, 'balance@0')
    names.register(after, 'balance@1')
    if case == 'linear':
        query = UnsatQuery(case, (
            UnsatConstraint('initial', (before >= 0,)),
            UnsatConstraint('update', (after == before + 1,)),
            UnsatConstraint('goal', (after < 0,)),
            UnsatConstraint('unrelated', (noise >= 0,)),
        ))
        return query, names, None
    if case == 'branches':
        query = UnsatQuery(case, (
            UnsatConstraint('update', (after == z3.If(before >= 0, before + 1, 0),)),
            UnsatConstraint('goal', (after < 0,)),
        ))
        return query, names, None
    if case == 'equal_squares':
        x, y = z3.Reals('x y')
        return UnsatQuery(case, (UnsatConstraint('conditions', (
            x == y, x ** 2 != y * y,
        )),)), None, None
    if case == 'shared_square':
        x, y = z3.Reals('x y')
        return UnsatQuery(case, (UnsatConstraint('conditions', (
            x * x == 2, y * y == 3, x == y,
        )),)), None, None
    if case == 'square':
        x = z3.Int('x')
        return UnsatQuery(case, (UnsatConstraint('target', (x * x == 2,)),)), None, None
    if case == 'product':
        x, y = z3.Reals('x y')
        return UnsatQuery(case, (
            UnsatConstraint('minimum_x', (x >= 2,)),
            UnsatConstraint('minimum_y', (y >= 3,)),
            UnsatConstraint('target', (x * y < 6,)),
        )), None, None
    allocation = z3.Int('allocation')
    query = UnsatQuery(case, (
        UnsatConstraint('minimum', (allocation > 0,), {
            'key': 'minimum', 'title': 'Minimum allocation', 'expression': 'allocation > 0',
        }),
        UnsatConstraint('capacity', (allocation <= 0,), {
            'key': 'capacity', 'title': 'Available capacity', 'expression': 'allocation <= 0',
        }),
    ))
    return query, None, AllocationSources(allocation)


def summarize(reading):
    """Name the complete deduction slice while preserving all input premises."""
    root = reading.get_block(reading.root_id)
    selected = tuple(block.block_id for block in reading.blocks if block.kind != 'input')
    premises = tuple(block.block_id for block in reading.blocks if block.kind == 'input')
    yield FoldProposal(root.block_id, selected, premises, root.claims, root.active_hypotheses,
                       'The target contradicts the given conditions', '目标与给定条件矛盾')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=('all', 'linear', 'branches', 'sources', 'square', 'product', 'shared_square', 'equal_squares'), default='all')
    parser.add_argument('--language', choices=('all', 'en', 'zh'), default='all')
    parser.add_argument('--minimize', action='store_true')
    parser.add_argument('--fold', action='store_true')
    options = parser.parse_args()
    cases = ('linear', 'branches', 'sources', 'square', 'product', 'shared_square', 'equal_squares') if options.case == 'all' else (options.case,)
    languages = ('en', 'zh') if options.language == 'all' else (options.language,)
    for case in cases:
        query, names, adapter = build(case)
        extensions = ProofExtensions(source_adapter=adapter,
                                     reading_folders=(ReadingFolder(summarize),) if options.fold else ())
        report = explain_unsat(query, names=names, extensions=extensions, minimize=options.minimize)
        for language in languages:
            print('BEGIN %s %s' % (case, language))
            print(report.reading.to_text(language), end='')
            print('END %s %s' % (case, language))
        if report.core is not None:
            print('core_ids=%r; subset_minimality=%s; proof_scope=%s' % (
                report.core.core_ids, report.core.subset_minimality, report.proof_scope))


if __name__ == '__main__':
    main()
