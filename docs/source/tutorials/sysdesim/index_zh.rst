SysDeSim FinalState 维护说明
================================

本文记录 ``dev/damnx`` 支线里的 SysDeSim ``uml:FinalState`` 兼容契约。这是
SysDeSim XML/XMI 导入路径的维护说明，不是 FCSTM 语言的新特性。

范围
----

SysDeSim 状态机图中，UML final state 通常画成靶心终止点。在 XML/XMI 中，
这些顶点表现为 ``uml:FinalState``。converter 不会把它们输出成普通 FCSTM
状态，而是把已支持的 FinalState target 转换成 FCSTM 退出语义。

当前只支持经过真实样本确认的窄范围形态：

* 同一 region 内，leaf state 指向 FinalState 时，降级为 ``State -> [*]``。
* 嵌套 leaf state 指向祖先 region 拥有的 FinalState 时，降级为 route flag 退出链。
* FinalState 作为 source、FinalState outgoing transition、无关 region 跳转、
  ``exitPoint`` 和 ``terminate`` 等变体仍是显式非目标；只有拿到真实样本并确认语义后，
  才能另开扩展项。

转换契约
--------

同层 FinalState transition 直接渲染为 FCSTM 退出：

.. code-block:: fcstm

   SS -> [*];

跨层 FinalState transition 使用一个保留 route flag。第一跳退出 source composite
并设置 flag；祖先层级在 flag 激活时继续退出；最后一跳清理 flag：

.. code-block:: fcstm

   def int __sysdesim_flag_route_control_e__tx_dqgyfg = 0;

   state StateMachine {
       state Control {
           state EState;
           EState -> [*] effect {
               __sysdesim_flag_route_control_e__tx_dqgyfg = 1;
           }
       }

       Control -> [*] : if [__sysdesim_flag_route_control_e__tx_dqgyfg > 0] effect {
           __sysdesim_flag_route_control_e__tx_dqgyfg = 0;
       };
   }

route flag 是变量，不是状态。它不能出现在状态节点、右侧状态泳道 cell 或其它状态可视化位置。

Timeline 与 report 契约
-----------------------------

runtime 通过 ``[*]`` 退出后，timeline validation 使用字符串 ``"[*]"`` 作为 ended sentinel。
这个 sentinel 不是普通模型状态路径，不应交给普通 state lookup 解析。

导入报告通过固定字段 ``report["phase10"]["termination"]`` 保留 XML 来源信息。
每一行必须精确包含这些 key：

.. code-block:: python

   {
       "machine_alias": "...",
       "source_path": ["..."],
       "target_id": "...",
       "target_path": [],
       "target_vertex_type": "final",
       "transition_ids": ["..."],
       "reached": True,
       "ended_step_ids": ["s27"],
   }

下游代码必须保留这些字段名。未来如果需要扩展 schema，必须同步更新本文档和 FS-5 回归测试，
不能 silent rename。

可视化契约
----------

用户可见视图应把已结束机器显示为 ``已终止`` 或等价的人类可读文本。不得把
``__sysdesim_final_*`` 显示成普通状态、pseudo state、lifeline 状态 cell、SVG label
或 PNG label。

SVG/PNG overlay 和 CLI summary 的终止文案，应来自 JSON report 使用的同一份 termination summary。
这样 report、CLI 和可视化输出不会产生三套互相漂移的逻辑。

回归证据
--------

仓库内固定使用以下 fixture：

* ``test/testfile/sysdesim/final_state_same_level_model2.xml``：覆盖同层 FinalState 降级。
* ``test/testfile/sysdesim/final_state_cross_level_model0608.xml``：覆盖跨层 route flag、
  ended timeline row 和可见终止来源。

FS-5 的集中回归入口是 ``test/convert/sysdesim/test_final_state_regression.py``。单元测试只能使用
checked-in fixture。``/data/sync/work`` 下的外部真实文件只能作为本地 smoke 证据，不能作为 pytest 依赖。
