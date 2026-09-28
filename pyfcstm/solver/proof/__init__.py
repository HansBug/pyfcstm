"""Public interfaces for portable UNSAT proofs and their readable explanations.

Import evidence, analysis, and extension interfaces from this package.
Native Z3 capture is loaded only when a proof is requested.
"""

from .core import (
    SourceDescription,
    SourceLink,
    SourceBinding,
    ProofSource,
    SourceAdapter,
    ProofExtensions,
    ProofParameter,
    ProofTerm,
    ProofInput,
    ProofNode,
    TermEquality,
    IntervalStep,
    IntervalCertificate,
    CountContribution,
    CardinalityCertificate,
    LinearBound,
    ArithmeticCertificate,
    ProofGap,
    ProofGraph,
    UnsatReport,
    CoreEvidence,
    explain_unsat,
)
from .rules import (
    RuleAnalysis,
    ProofRuleHandler,
    ProofAnalysis,
    analyze_proof,
)
from .text import (
    FoldProposal,
    ReadingFolder,
    ReadingBlock,
    ProofReading,
)

__all__ = [
    'SourceDescription',
    'SourceLink',
    'SourceBinding',
    'ProofSource',
    'SourceAdapter',
    'ProofExtensions',
    'ProofParameter',
    'ProofTerm',
    'ProofInput',
    'ProofNode',
    'TermEquality',
    'IntervalStep',
    'IntervalCertificate',
    'CountContribution',
    'CardinalityCertificate',
    'LinearBound',
    'ArithmeticCertificate',
    'ProofGap',
    'ProofGraph',
    'UnsatReport',
    'CoreEvidence',
    'explain_unsat',
    'RuleAnalysis',
    'ProofRuleHandler',
    'ProofAnalysis',
    'analyze_proof',
    'FoldProposal',
    'ReadingFolder',
    'ReadingBlock',
    'ProofReading',
]
