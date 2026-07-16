pyfcstm.\_selfcheck.protocol
========================================================

.. currentmodule:: pyfcstm._selfcheck.protocol

.. automodule:: pyfcstm._selfcheck.protocol


FRAME\_PREFIX
-----------------------------------------------------

.. autodata:: FRAME_PREFIX


WORKER\_SCHEMA
-----------------------------------------------------

.. autodata:: WORKER_SCHEMA


MAX\_ENVELOPE\_BYTES
-----------------------------------------------------

.. autodata:: MAX_ENVELOPE_BYTES


MAX\_RESULT\_FILE\_BYTES
-----------------------------------------------------

.. autodata:: MAX_RESULT_FILE_BYTES


MAX\_PROTOCOL\_DIAGNOSTIC\_BYTES
-----------------------------------------------------

.. autodata:: MAX_PROTOCOL_DIAGNOSTIC_BYTES


FrameReadOutcome
-----------------------------------------------------

.. autoclass:: FrameReadOutcome
    :members: envelope,error_code,frame_count,diagnostic


make\_nonce
-----------------------------------------------------

.. autofunction:: make_nonce


is\_valid\_nonce
-----------------------------------------------------

.. autofunction:: is_valid_nonce


build\_start\_gate
-----------------------------------------------------

.. autofunction:: build_start_gate


encode\_result\_frame
-----------------------------------------------------

.. autofunction:: encode_result_frame


read\_result\_file
-----------------------------------------------------

.. autofunction:: read_result_file


read\_stdout\_frames
-----------------------------------------------------

.. autofunction:: read_stdout_frames
