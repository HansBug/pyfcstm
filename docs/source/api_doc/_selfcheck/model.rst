pyfcstm.\_selfcheck.model
========================================================

.. currentmodule:: pyfcstm._selfcheck.model

.. automodule:: pyfcstm._selfcheck.model


TERMINAL\_STATUSES
-----------------------------------------------------

.. autodata:: TERMINAL_STATUSES


CheckSpec
-----------------------------------------------------

.. autoclass:: CheckSpec
    :members: check_id,worker_key,required,prerequisites


CheckResult
-----------------------------------------------------

.. autoclass:: CheckResult
    :members: __post_init__,to_dict,check_id,status,required,summary,details,reason,return_code,transport,truncated_bytes,duration_ms


LedgerEvent
-----------------------------------------------------

.. autoclass:: LedgerEvent
    :members: sequence,kind,check_id,payload,timestamp_ns


ReportSnapshot
-----------------------------------------------------

.. autoclass:: ReportSnapshot
    :members: to_dict,checks,metadata,counts


Ledger
-----------------------------------------------------

.. autoclass:: Ledger
    :members: __init__,events,reserve,ensure_reserved,commit,mark_running,get_state,has_result,get_result,freeze
