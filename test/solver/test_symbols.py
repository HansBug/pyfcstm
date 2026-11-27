"""Construction-time symbolic names preserve identity and reject ambiguity."""

import pytest
import z3

import pyfcstm.solver as solver


pytestmark = pytest.mark.unittest


def test_names_render_actual_symbols_without_changing_solver_expressions():
    x, y = z3.Ints('encoded_x encoded_y')
    names = solver.SymbolNames()
    source = {'label': 'counter'}
    names.register(x, 'counter@0', source)
    assert names.lookup(x).source is source
    assert names.lookup(y) is None
    assert names.render(x + y) == 'counter@0 + encoded_y'
    assert str(x + y) == 'encoded_x + encoded_y'
    assert names.entries[0].symbol.eq(x)
    assert names.render(z3.IntVal(1)) == '1'


def test_equal_spelling_in_another_context_does_not_acquire_a_name():
    x = z3.Int('x')
    other = z3.Int('x', ctx=z3.Context())
    names = solver.SymbolNames()
    names.register(x, 'registered')
    assert names.lookup(other) is None
    assert names.render(other) == 'x'


@pytest.mark.parametrize('name,error', [
    ('', ValueError), ('  ', ValueError), ('x\ny', ValueError),
    ('x\ry', ValueError), (4, TypeError),
])
def test_invalid_display_name_is_rejected(name, error):
    with pytest.raises(error):
        solver.SymbolNames().register(z3.Int('x'), name)


def test_nonconstant_registration_and_nonexpression_render_are_rejected():
    names = solver.SymbolNames()
    with pytest.raises(TypeError):
        names.register(z3.Int('x') + 1, 'sum')
    with pytest.raises(TypeError):
        names.register(z3.IntVal(1), 'one')
    with pytest.raises(TypeError):
        names.render('x')


def test_duplicate_registration_and_display_collision_are_rejected():
    x, y = z3.Ints('x y')
    names = solver.SymbolNames()
    names.register(x, 'pretty')
    with pytest.raises(ValueError):
        names.register(x, 'again')
    with pytest.raises(ValueError):
        names.register(y, 'pretty')
    with pytest.raises(ValueError, match='collides'):
        names.render(x + z3.Int('pretty'))


def test_quantifier_binders_are_preserved_and_display_collisions_rejected():
    x, y = z3.Ints('x y')
    names = solver.SymbolNames()
    names.register(x, 'free')
    formula = z3.ForAll(y, x > y)
    assert 'ForAll(y, free > y)' == names.render(formula)
    colliding = solver.SymbolNames()
    colliding.register(x, 'y')
    with pytest.raises(ValueError, match='bound'):
        colliding.render(formula)


def test_shared_expression_and_long_formulas_are_not_truncated():
    names = solver.SymbolNames()
    x = z3.Int('x')
    names.register(x, 'counter')
    text = names.render(z3.And(*(x > i for i in range(150))))
    assert 'counter > 0' in text
    assert 'counter > 149' in text
    assert '...' not in text
