版本说明
========

DSL 表达式运算符
----------------

本版本为 ``cond_expression`` 增加三组可用于守卫条件和其他布尔表达式位置的
布尔运算符：

- ``A => B`` 和 ``A implies B`` 表示蕴含。规范化 DSL 写法是 ``=>``。
  蕴含是右结合，因此 ``A => B => C`` 表示 ``A => (B => C)``。
- ``A xor B`` 表示布尔异或。链式 ``xor`` 是左结合的布尔奇偶异或链，
  不是多个输入中恰好一个为真的 exactly-one 运算。
- ``A iff B`` 表示布尔等价，是布尔相等关系的可读写法。

兼容性说明
----------

``implies``、``xor`` 和 ``iff`` 现在是 DSL 保留关键字。已有状态机如果把这些
名字用作变量、状态或事件名，需要在使用本版本前先重命名。

``->`` 仍然是状态转换箭头，不是守卫条件中的蕴含运算符。请使用 ``=>`` 或
``implies``。

``^`` 仍然是数值位异或运算符。它可以出现在守卫中被比较的算术表达式里，例如：

.. code-block:: fcstm

   StateA -> StateB : if [(flags ^ 0xFF) == 0];

它不是布尔异或写法：

.. code-block:: fcstm

   StateA -> StateB : if [a > 0 xor b > 0];   // 有效
   StateA -> StateB : if [(a > 0) ^ (b > 0)]; // 无效
   StateA -> StateB : if [true ^ false];      // 无效
