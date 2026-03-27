pyfcstm.convert.sysdesim.convert
========================================================

.. currentmodule:: pyfcstm.convert.sysdesim.convert

.. automodule:: pyfcstm.convert.sysdesim.convert


SysDeSimPreparedMachine
-----------------------------------------------------

.. autoclass:: SysDeSimPreparedMachine
    :members: output_name,machine,semantic_note


SysDeSimOutputValidationReport
-----------------------------------------------------

.. autoclass:: SysDeSimOutputValidationReport
    :members: to_dict,output_name,parser_roundtrip_ok,model_build_ok,guard_variables_defined,event_paths_valid,composite_states_have_init,dsl_line_count,semantic_note,diagnostics


SysDeSimConversionReport
-----------------------------------------------------

.. autoclass:: SysDeSimConversionReport
    :members: output_count,to_dict,source_xml_path,requested_machine_name,requested_machine_id,selected_machine_name,selected_machine_id,tick_duration_ms,outputs


load\_sysdesim\_xml
-----------------------------------------------------

.. autofunction:: load_sysdesim_xml


load\_sysdesim\_machine
-----------------------------------------------------

.. autofunction:: load_sysdesim_machine


make\_internal\_name
-----------------------------------------------------

.. autofunction:: make_internal_name


normalize\_machine
-----------------------------------------------------

.. autofunction:: normalize_machine


build\_machine\_ast
-----------------------------------------------------

.. autofunction:: build_machine_ast


emit\_program
-----------------------------------------------------

.. autofunction:: emit_program


validate\_program\_roundtrip
-----------------------------------------------------

.. autofunction:: validate_program_roundtrip


prepare\_sysdesim\_output\_machines
-----------------------------------------------------

.. autofunction:: prepare_sysdesim_output_machines


convert\_sysdesim\_xml\_to\_asts
-----------------------------------------------------

.. autofunction:: convert_sysdesim_xml_to_asts


convert\_sysdesim\_xml\_to\_dsls
-----------------------------------------------------

.. autofunction:: convert_sysdesim_xml_to_dsls


build\_sysdesim\_conversion\_report
-----------------------------------------------------

.. autofunction:: build_sysdesim_conversion_report


convert\_sysdesim\_xml\_to\_ast
-----------------------------------------------------

.. autofunction:: convert_sysdesim_xml_to_ast


convert\_sysdesim\_xml\_to\_dsl
-----------------------------------------------------

.. autofunction:: convert_sysdesim_xml_to_dsl


