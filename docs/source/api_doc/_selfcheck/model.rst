pyfcstm.\_selfcheck.model
========================================================

.. currentmodule:: pyfcstm._selfcheck.model

.. automodule:: pyfcstm._selfcheck.model


CHECK\_OUTCOME\_STATUSES
-----------------------------------------------------

.. autodata:: CHECK_OUTCOME_STATUSES


TERMINAL\_STATUSES
-----------------------------------------------------

.. autodata:: TERMINAL_STATUSES


ArtifactContext
-----------------------------------------------------

.. autoclass:: ArtifactContext
    :members: __post_init__,kind,root,allowed_roots,allow_site_packages


CheckSpec
-----------------------------------------------------

.. autoclass:: CheckSpec
    :members: __post_init__,check_id,worker_key,title,required,prerequisites,execution,timeout_seconds,safety,prerequisite_policy,explicit_skip


CheckOutcome
-----------------------------------------------------

.. autoclass:: CheckOutcome
    :members: __post_init__,status,summary,reason,expected,observed,evidence,remediation,exception


CheckResult
-----------------------------------------------------

.. autoclass:: CheckResult
    :members: __post_init__,from_outcome,to_dict,check_id,status,required,summary,title,prerequisites,reason,expected,observed,evidence,remediation,exception,return_code,transport,truncated_bytes,duration_ms,pid,signal,ntstatus,stdout,stderr,encoding,timeout


ReportSnapshot
-----------------------------------------------------

.. autoclass:: ReportSnapshot
    :members: __post_init__,to_dict,checks,metadata,counts


Ledger
-----------------------------------------------------

.. autoclass:: Ledger
    :members: __init__,reserve,ensure_reserved,mark_running,commit,get_state,get_result,freeze
