pyfcstm.verify.inspect\_adapter
========================================================

.. currentmodule:: pyfcstm.verify.inspect_adapter

.. automodule:: pyfcstm.verify.inspect_adapter


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


InspectRunResult
-----------------------------------------------------

.. autoclass:: InspectRunResult
    :members: algorithm_name,complexity_tier,smt_logic,verification_scope,diagnostic_codes,result_kind,diagnostics,reason,raw_result


InspectEligibility
-----------------------------------------------------

.. autoclass:: InspectEligibility
    :members: meta,eligible,not_run_reason_code


InspectAccessForbiddenError
-----------------------------------------------------

.. autoclass:: InspectAccessForbiddenError


eligible\_for\_inspect
-----------------------------------------------------

.. autofunction:: eligible_for_inspect


project\_inspect\_eligibility
-----------------------------------------------------

.. autofunction:: project_inspect_eligibility


iter\_inspect\_eligible
-----------------------------------------------------

.. autofunction:: iter_inspect_eligible


run\_inspect\_algorithms
-----------------------------------------------------

.. autofunction:: run_inspect_algorithms
