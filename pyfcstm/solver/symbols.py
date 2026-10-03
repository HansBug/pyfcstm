"""Construction-time names for symbolic expressions and their source objects.

The registry keys actual Z3 constants, including their context, rather than
parsing encoded names. Rendering substitutes display constants in a temporary
expression; it never changes the solver's formula.
"""

from io import StringIO
import sys
from typing import Any, NamedTuple, Optional, Tuple

import z3
from z3.z3printer import Formatter, PP

__all__ = ["SymbolName", "SymbolNames"]


class _NativeFormatter(Formatter):
    """Reuse native formatting of shared nodes outside bound-variable scopes.

    Each instance renders one retained expression with truncation disabled.
    Quantifier bodies use native formatting without memoization because a bound
    variable's display depends on its enclosing binders, not just its AST id.
    """

    def __init__(self):
        super().__init__()
        self._formats = {}

    def pp_expr(self, expression, depth, bound):
        if bound:
            return super().pp_expr(expression, depth, bound)
        key = expression.get_id()
        if key not in self._formats:
            self._formats[key] = super().pp_expr(expression, depth, bound)
        return self._formats[key]


def _expression_constants(expression, bound_names=None):
    """Visit each AST once and return free uninterpreted constants by identity.

    Unlike ``z3util.get_vars``, this does not print accumulated constants to
    deduplicate them. The result also keeps distinct same-spelling constants
    of different sorts separate.
    If supplied, ``bound_names`` also collects quantifier-bound identifiers for
    display collision checks.
    """
    symbols = []
    pending = [expression]
    visited = set()
    while pending:
        node = pending.pop()
        identity = node.get_id()
        if identity in visited:
            continue
        visited.add(identity)
        if bound_names is not None and z3.is_quantifier(node):
            bound_names.update(str(node.var_name(index)) for index in range(node.num_vars()))
        if z3.is_const(node) and node.decl().kind() == z3.Z3_OP_UNINTERPRETED:
            symbols.append(node)
        else:
            pending.extend(node.children())
    return symbols


class SymbolName(NamedTuple):
    """A symbolic value's display name and caller-owned source metadata.

    :param symbol: Original Z3 constant.
    :type symbol: z3.ExprRef
    :param display: Short display identifier.
    :type display: str
    :param source: Opaque construction-time origin, defaults to None.
    :type source: object
    """

    symbol: z3.ExprRef
    display: str
    source: Any = None


class SymbolNames:
    """Register readable names while constructing symbolic values.

    Names must be unique within a registry. Re-registering a symbol is rejected
    so an earlier explanation cannot silently acquire a different origin.
    Unregistered constants retain their original spelling. Rendering rejects
    a formula when that spelling collides with a displayed registered symbol.

    Example::

        >>> names = SymbolNames()
        >>> x = z3.Real('encoded_value')
        >>> names.register(x, 'x@2')
        >>> names.render(x / 2)
        'x@2/2'
    """

    def __init__(self):
        self._entries = {}
        self._displays = set()

    def register(self, symbol: z3.ExprRef, display: str, source: Any = None) -> None:
        """Bind one constant to a readable identifier and an opaque origin.

        :param symbol: An uninterpreted Z3 constant.
        :param display: Nonempty single-line display identifier.
        :param source: Original source object; retained by identity.
        :raises TypeError: For a nonconstant expression or nonstring display.
        :raises ValueError: For an empty/multiline or duplicate display, or
            an already registered symbol.
        """
        if not z3.is_const(symbol) or symbol.decl().kind() != z3.Z3_OP_UNINTERPRETED:
            raise TypeError("symbol must be an uninterpreted Z3 constant")
        if not isinstance(display, str):
            raise TypeError("display must be a string")
        if not display.strip() or '\n' in display or '\r' in display:
            raise ValueError("display must be nonempty and single-line")
        key = (symbol.ctx, symbol.get_id())
        if key in self._entries:
            raise ValueError("symbol is already registered")
        if display in self._displays:
            raise ValueError("display is already registered")
        self._entries[key] = SymbolName(symbol, display, source)
        self._displays.add(display)

    def lookup(self, symbol: z3.ExprRef) -> Optional[SymbolName]:
        """Return registered metadata for the exact constant, or None.

        :param symbol: Original Z3 expression.
        :return: Its construction-time identity, if registered.
        """
        return self._entries.get((symbol.ctx, symbol.get_id()))

    @property
    def entries(self) -> Tuple[SymbolName, ...]:
        """Return entries in construction order as an immutable tuple."""
        return tuple(self._entries.values())

    def render(self, expression: z3.ExprRef) -> str:
        """Render with registered names while preserving expression structure.

        :param expression: A Z3 expression to display, never to modify in place.
        :return: Z3's ordinary expression notation with display identifiers.
        :raises TypeError: For a non-Z3 expression.
        :raises ValueError: If an unregistered symbol would be confused with a
            registered display name in this expression.
        """
        if not isinstance(expression, z3.ExprRef):
            raise TypeError("expression must be a Z3 expression")
        bound_names = set()
        symbols = _expression_constants(expression, bound_names)
        entries = tuple(self.lookup(symbol) for symbol in symbols)
        displays = {entry.display for entry in entries if entry is not None}
        if displays & bound_names:
            raise ValueError("display name collides with a quantifier bound name")
        if any(entry is None and str(symbol) in displays
               for symbol, entry in zip(symbols, entries)):
            raise ValueError("display name collides with an unregistered symbol")
        substitutions = tuple(
            (entry.symbol, z3.Const(entry.display, entry.symbol.sort()))
            for entry in entries
            if entry is not None
        )
        renamed = z3.substitute(expression, *substitutions)
        # Keep Z3's notation without its interactive display truncation. Local
        # printer instances do not change options used by concurrent callers.
        formatter = _NativeFormatter()
        formatter.max_depth = sys.maxsize
        formatter.max_args = sys.maxsize
        formatter.max_visited = sys.maxsize
        printer = PP()
        printer.max_lines = sys.maxsize
        with StringIO() as output:
            printer(output, formatter(renamed))
            return output.getvalue()
