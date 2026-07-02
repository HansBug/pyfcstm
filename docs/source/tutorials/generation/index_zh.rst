内置模板生成
============

本页是独立生成教程的临时入口，后续文档更新会把这里扩展成完整的内置模板指南。

对打包内置模板使用 ``--template``：

.. code-block:: bash

   pyfcstm generate -i machine.fcstm --template python -o generated --clear

当前内置模板包括 ``python``、``c``、``c_poll``、``cpp`` 和 ``cpp_poll``。生成目录包含 README，会说明集成方式。只有自定义模板目录才使用 ``-t/--template-dir``。
