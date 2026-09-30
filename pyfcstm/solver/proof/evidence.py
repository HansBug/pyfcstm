"""Explicit certificate families shared by reconstruction and offline replay.

The catalog contains no native solver objects and performs no proof search.
It is internal: callers extend native interpretation and domain readings through
``ProofExtensions``, rather than modifying a process-global registry.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable


@dataclass(frozen=True)
class CertificateHandler:
    """Associate one existing node field with its typed, independent checker."""

    field: str
    kind: str
    payload_type: type
    check: Callable

    def replay(self, node, graph, certificate, budget=None):
        """Check detached evidence using the optional shared live deadline."""
        return self.check(node, graph, certificate, budget=budget)


@lru_cache(maxsize=1)
def certificate_handlers():
    """Return the immutable catalog in the established offline validation order."""
    from .core import (ArithmeticCertificate, LinearEqualityCertificate,
                       DivisibilityCertificate, PolynomialCertificate,
                       IntervalCertificate, CardinalityCertificate)
    from .rules import (check_arithmetic_certificate, check_linear_equality_certificate,
                        check_cardinality_certificate)
    from .integer import check_divisibility_certificate
    from .polynomial import check_polynomial_certificate
    from .interval import check_interval_certificate

    return (
        CertificateHandler('certificate', 'arithmetic', ArithmeticCertificate, check_arithmetic_certificate),
        CertificateHandler('linear_equality', 'linear_equality', LinearEqualityCertificate,
                           check_linear_equality_certificate),
        CertificateHandler('divisibility', 'divisibility', DivisibilityCertificate, check_divisibility_certificate),
        CertificateHandler('polynomial', 'polynomial', PolynomialCertificate, check_polynomial_certificate),
        CertificateHandler('interval', 'interval', IntervalCertificate, check_interval_certificate),
        CertificateHandler('cardinality', 'cardinality', CardinalityCertificate, check_cardinality_certificate),
    )


def iter_evidence(node):
    """Yield attached certificate families without inventing absent evidence."""
    for handler in certificate_handlers():
        certificate = getattr(node, handler.field)
        if certificate is not None:
            yield handler, certificate
