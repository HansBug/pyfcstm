"""Readable formulas resolve symbols by identity, never encoded-name parsing."""

import pytest
import z3

pytestmark = pytest.mark.unittest


def test_registered_names_render_nested_expressions_and_keep_origin():
    from pyfcstm.solver.symbols import SymbolNames

    names = SymbolNames()
    x = z3.Real('generated_87654_very_long_unreadable_identifier')
    origin = {'variable_id': 7, 'frame': 3}
    names.register(x, 'v7@3', origin)
    assert names.render(x / 2) == 'v7@3/2'
    assert names.lookup(x).source is origin
    assert names.entries == (names.lookup(x),)


def test_same_spelling_in_other_context_has_no_registered_origin():
    from pyfcstm.solver.symbols import SymbolNames

    names = SymbolNames()
    x = z3.Int('same')
    names.register(x, 'x@0')
    other = z3.Int('same', ctx=z3.Context())
    assert names.lookup(other) is None
    assert names.render(other + 1) == 'same + 1'


def test_display_names_cannot_silently_alias_different_symbols():
    from pyfcstm.solver.symbols import SymbolNames

    names = SymbolNames()
    x, y = z3.Ints('x y')
    names.register(x, 'v@0')
    with pytest.raises(ValueError, match='display'):
        names.register(y, 'v@0')


def test_unregistered_symbol_cannot_be_confused_with_display_alias():
    from pyfcstm.solver.symbols import SymbolNames

    names = SymbolNames()
    original, other = z3.Ints('encoded v0')
    names.register(original, 'v0')
    expression = original > other
    before = expression.sexpr()
    with pytest.raises(ValueError, match='unregistered symbol'):
        names.render(expression)
    assert expression.sexpr() == before


def test_registered_symbol_swap_preserves_formula_and_distinct_identities():
    from pyfcstm.solver.symbols import SymbolNames

    names = SymbolNames()
    x, y = z3.Ints('x y')
    names.register(x, 'y')
    names.register(y, 'x')
    expression = x - y > 0
    before = expression.sexpr()
    assert names.render(expression) == 'y - x > 0'
    assert expression.sexpr() == before


@pytest.mark.parametrize('operation', [
    lambda x, y: x % y,
    lambda x, y: x ** y,
    lambda x, y: z3.If(x > y, x, y),
    lambda x, y: z3.And(x != y, z3.Not(x <= y)),
    lambda x, y: z3.ToReal(x) / z3.ToReal(y),
])
def test_render_preserves_native_operations_without_operator_translation(operation):
    from pyfcstm.solver.symbols import SymbolNames

    names = SymbolNames()
    x, y = z3.Ints('generated_payload generated_limit')
    names.register(x, 'v0@2')
    names.register(y, 'v1@2')
    expression = operation(x, y)
    before = expression.sexpr()
    expected = operation(z3.Int('v0@2'), z3.Int('v1@2'))
    assert names.render(expression) == str(expected)
    assert expression.sexpr() == before


def test_render_keeps_all_members_beyond_native_default_display_limit(text_aligner):
    from pyfcstm.solver.symbols import SymbolNames

    names = SymbolNames()
    x = z3.Int('generated')
    names.register(x, 'v0@0')
    expression = z3.And(*(x != value for value in range(150)))
    rendered = names.render(expression)
    text_aligner.assert_equal(
        expect='And(' + ',\n    '.join('v0@0 != %d' % value for value in range(150)) + ')',
        actual=rendered,
    )


@pytest.mark.parametrize('symbol,display,error', [
    (z3.Int('x') + 1, 'x', TypeError),
    (z3.Int('x'), None, TypeError),
    (z3.Int('x'), ' ', ValueError),
    (z3.Int('x'), 'x\ny', ValueError),
    (z3.Int('x'), 'x\ry', ValueError),
])
def test_registration_rejects_invalid_symbol_or_display(symbol, display, error):
    from pyfcstm.solver.symbols import SymbolNames

    with pytest.raises(error):
        SymbolNames().register(symbol, display)


def test_registered_identity_cannot_be_replaced():
    from pyfcstm.solver.symbols import SymbolNames

    names = SymbolNames()
    x = z3.Int('original')
    names.register(x, 'v0')
    with pytest.raises(ValueError, match='already registered'):
        names.register(x, 'v1')
    assert names.lookup(x).display == 'v0'


def test_render_rejects_non_expression():
    from pyfcstm.solver.symbols import SymbolNames

    with pytest.raises(TypeError, match='Z3 expression'):
        SymbolNames().render('x + 1')


def test_alias_cannot_shadow_quantifier_bound_name_in_rendered_formula():
    from pyfcstm.solver.symbols import SymbolNames

    names = SymbolNames()
    x, y = z3.Ints('long_source y')
    names.register(x, 'y')
    expression = z3.ForAll(y, x > y)
    with pytest.raises(ValueError, match='bound name'):
        names.render(expression)


def test_quantified_expression_preserves_bound_variables_and_maps_free_constants():
    from pyfcstm.solver.symbols import SymbolNames

    names = SymbolNames()
    x, y = z3.Ints('long_source y')
    names.register(x, 'v0')
    expression = z3.ForAll(y, x > y)
    assert names.render(expression) == 'ForAll(y, v0 > y)'


def test_shared_bound_ast_is_rendered_in_each_quantifiers_own_scope():
    from pyfcstm.solver.symbols import SymbolNames

    names = SymbolNames()
    x, y, free = z3.Ints('x y generated')
    names.register(free, 'v0')
    expression = z3.And(z3.ForAll(x, x > free), z3.Exists(y, y > free))
    expected = z3.And(z3.ForAll(x, x > z3.Int('v0')), z3.Exists(y, y > z3.Int('v0')))
    assert names.render(expression) == str(expected)


def test_same_spelling_in_different_sorts_keeps_both_registered_identities():
    from pyfcstm.solver.symbols import SymbolNames

    names = SymbolNames()
    integer, real = z3.Int('original'), z3.Real('original')
    names.register(integer, 'integer_value')
    names.register(real, 'real_value')
    assert names.render(integer < real) == 'ToReal(integer_value) < real_value'
