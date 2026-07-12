"""
Packaged LLM prompt resources for FCSTM models and FBMCQ queries.

This package exports integrity-checked prompt-resource APIs. It deliberately
does not construct provider prompts or import parsing, model, verification, or
provider modules: callers compose the returned text with their own task input.

Public resource map:

.. list-table::
   :header-rows: 1

   * - Resource
     - Text API
     - Purpose
   * - FCSTM grammar guide
     - :func:`get_grammar_guide_prompt_for_llm`
     - Generate FCSTM model source from natural-language requirements.
   * - FBMCQ language guide
     - :func:`get_fbmcq_language_guide_prompt_for_llm`
     - Author, repair, review, or explain an FBMCQ query from known model facts.

Example::

    >>> from pyfcstm.llm import get_fbmcq_language_guide_prompt_for_llm
    >>> get_fbmcq_language_guide_prompt_for_llm().startswith("# FBMCQ")
    True
"""

from .error import (
    GrammarGuidePromptIntegrityError,
    GrammarGuidePromptPathUnavailableError,
)
from .fbmcq import (
    get_fbmcq_language_guide_prompt_for_llm,
    get_fbmcq_language_guide_prompt_metadata_for_llm,
    get_fbmcq_language_guide_prompt_path_for_llm,
)
from .fcstm import (
    get_grammar_guide_prompt_for_llm,
    get_grammar_guide_prompt_metadata_for_llm,
    get_grammar_guide_prompt_path_for_llm,
)

__all__ = [
    "GrammarGuidePromptIntegrityError",
    "GrammarGuidePromptPathUnavailableError",
    "get_grammar_guide_prompt_for_llm",
    "get_grammar_guide_prompt_path_for_llm",
    "get_grammar_guide_prompt_metadata_for_llm",
    "get_fbmcq_language_guide_prompt_for_llm",
    "get_fbmcq_language_guide_prompt_path_for_llm",
    "get_fbmcq_language_guide_prompt_metadata_for_llm",
]
