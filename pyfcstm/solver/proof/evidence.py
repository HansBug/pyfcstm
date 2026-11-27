"""Explicit certificate families shared by reconstruction, offline replay and readings.

The catalog contains no native solver objects and performs no proof search.
It is internal: callers extend native interpretation and domain readings through
``ProofExtensions``, rather than modifying a process-global registry.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable


@dataclass(frozen=True)
class CertificateHandler:
    """Associate one existing node field with its typed checker and reading function."""

    field: str
    kind: str
    payload_type: type
    check: Callable
    render: Callable
    reading_order: int

    def replay(self, node, graph, certificate, budget=None):
        """Check detached evidence using the optional shared live deadline."""
        return self.check(node, graph, certificate, budget=budget)


@lru_cache(maxsize=1)
def certificate_handlers():
    """Return the immutable catalog in the established offline validation order."""
    from .evidence_text import (render_arithmetic, render_linear_equality, render_divisibility,
                                render_polynomial, render_interval, render_cardinality)
    from .core import (ArithmeticCertificate, LinearEqualityCertificate,
                       DivisibilityCertificate, PolynomialCertificate,
                       IntervalCertificate, CardinalityCertificate)
    from .rules import (check_arithmetic_certificate, check_linear_equality_certificate,
                        check_cardinality_certificate)
    from .integer import check_divisibility_certificate
    from .polynomial import check_polynomial_certificate
    from .interval import check_interval_certificate

    return (
        CertificateHandler('certificate', 'arithmetic', ArithmeticCertificate,
                           check_arithmetic_certificate, render_arithmetic, 0),
        CertificateHandler('linear_equality', 'linear_equality', LinearEqualityCertificate,
                           check_linear_equality_certificate, render_linear_equality, 1),
        CertificateHandler('divisibility', 'divisibility', DivisibilityCertificate,
                           check_divisibility_certificate, render_divisibility, 3),
        CertificateHandler('polynomial', 'polynomial', PolynomialCertificate,
                           check_polynomial_certificate, render_polynomial, 2),
        CertificateHandler('interval', 'interval', IntervalCertificate,
                           check_interval_certificate, render_interval, 4),
        CertificateHandler('cardinality', 'cardinality', CardinalityCertificate,
                           check_cardinality_certificate, render_cardinality, 5),
    )


def iter_evidence(node, *, reading=False):
    """Yield attached evidence in validation order, or the established reading order."""
    handlers = certificate_handlers()
    if reading:
        handlers = sorted(handlers, key=lambda handler: handler.reading_order)
    for handler in handlers:
        certificate = getattr(node, handler.field)
        if certificate is not None:
            yield handler, certificate
