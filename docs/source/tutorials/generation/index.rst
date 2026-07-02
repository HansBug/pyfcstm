Built-in Template Generation
============================

This page is a temporary entry point for the dedicated generation tutorial. A
later documentation update will expand it into the complete built-in template
guide.

Use ``--template`` for packaged built-in templates:

.. code-block:: bash

   pyfcstm generate -i machine.fcstm --template python -o generated --clear

Current built-in templates include ``python``, ``c``, ``c_poll``, ``cpp``, and
``cpp_poll``. Generated directories include README files with integration notes.
Use ``-t/--template-dir`` only for a custom template directory.
