# SysDeSim XML/XMI 样例结构分析

## 版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| 0.3.1 | 2026-03-27 | 结合 TIMELINE 设计重写当前样例的转换方案，明确这是 timeline 真实输入样本，应优先抽取 `step`、`event_map`、`input_map`、`SetInput` 所需语义，而非追求类属性全量导入 | Codex |
| 0.3.0 | 2026-03-27 | 增补面向当前样例的转换修改方案，明确变量忽略策略、`ChangeEvent/guard` 的统一事件化策略，以及与顺序图变量变化的联动方向 | Codex |
| 0.2.0 | 2026-03-27 | 补充状态机触发与顺序图消息之间的关联层级分析，以及变量定义与表达式文本之间是否存在 `id` 级绑定的结论 | Codex |
| 0.1.0 | 2026-03-27 | 初始版本，整理样例 XMI 的整体结构、模型层/图层/stereotype 层关系，以及状态机图与顺序图在 XMI 中的组织方式 | Codex |

---

## 1. 分析范围

本文分析的是一个典型的 SysDeSim XML/XMI 样例，以及与之对应的外部导出图。

本文前半部分的目标不是讨论转换策略，而是先回答一个更基础的问题：

- 这个 XML 文件到底是不是“纯状态机文件”
- 它内部有哪些层次
- 状态机、顺序图、活动图、信号、事件、枚举、端口、stereotype 和图形表示信息分别放在哪里
- 后续如果要写解析器，哪些信息是业务结构，哪些信息只是绘图元数据

在这些结构结论的基础上，本文第 16 节再补充一个面向当前真实样例的收敛式转换方案。

本文基于当前这个样例文件做结论，因此：

- 文中提到的元素数量和对象树是这个样例的实际观测结果
- 文中抽出的通用规律适用于“这一类 SysDeSim 导出 XMI”，但不应在没有更多样例验证的前提下断言覆盖所有导出变体

---

## 2. 总体结论

当前样例不是一个“只包含状态机定义”的简单 XML，而是一个典型的：

- `XMI 20131001`
- `UML 2.5`
- 携带 `SysML` stereotype 扩展
- 携带工具私有 `SDSDiagram` / `DiagramRepresentation` 图表示元数据

的复合导出文件。

它至少同时承载了三层数据：

- **模型层**
  - UML/SysML 语义对象本身，例如 `uml:Class`、`uml:StateMachine`、`uml:Interaction`、`uml:Signal`、`uml:Transition`
- **图表示层**
  - 图种类、图上下文、图对象集合、notation id、binary stream identity 等工具元数据
- **stereotype / profile 层**
  - `profileApplication`、`Blocks:Block`、`PortsAndFlows:ProxyPort`、`Blocks:ValueType` 等扩展应用

因此，如果后续要做解析，不能把这个文件当成“状态节点 + 转移边 + 属性”的轻量私有格式，而应当当成：

```text
一个 UML/SysML XMI 容器
  + 工具私有 diagram annotation
  + stereotype application
  + 具体模型内容
```

---

## 3. 根结构

当前样例的最外层结构可以先抽象为：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<xmi:XMI ...>
  <uml:Model xmi:id="..." name="model">
    <eAnnotations .../>
    <ownedComment .../>
    <packagedElement xmi:type="uml:Package" ...>
      ...
    </packagedElement>
    <profileApplication .../>
    <profileApplication .../>
    ...
  </uml:Model>

  <Blocks:Block .../>
  <Blocks:ValueType .../>
  <Blocks:ValueType .../>
  <PortsAndFlows:ProxyPort .../>
  <PortsAndFlows:ProxyPort .../>
  ...
</xmi:XMI>
```

根层的重要特点是：

- 最外层是 `xmi:XMI`
- 真正的 UML 模型根对象是 `uml:Model`
- `uml:Model` 内部既有 `packagedElement`，也有一大串 `profileApplication`
- `uml:Model` 结束后，文件尾部还有一批“脱离 `uml:Model` 的 stereotype application 元素”，例如 `Blocks:Block`、`PortsAndFlows:ProxyPort`

换句话说，**文件尾部那些 `Blocks:*` / `PortsAndFlows:*` 也属于模型的一部分**，只是它们不以内嵌方式出现，而是通过 `base_Class` / `base_Port` 这类属性回指前面定义的 UML 元素。

---

## 4. 命名空间与扩展来源

当前样例头部声明了以下关键命名空间：

| 前缀 | 含义 |
|------|------|
| `xmi` | XMI 基础命名空间 |
| `xsi` | XML Schema Instance |
| `uml` | UML 2.5 元模型 |
| `ecore` | Eclipse EMF / Ecore 注解体系 |
| `Blocks` | SysML Blocks 扩展 |
| `PortsAndFlows` | SysML Ports and Flows 扩展 |
| `Diagrams` | 工具私有图对象元数据 |
| `DiagramRepresentation` | 工具私有图表示数据 |
| `domain` | 工具私有 stereotype instance 承载 |

其中最值得注意的是下面几组：

### 4.1 `uml`

这是主语义层。
状态机、顺序图、信号、事件、枚举、属性、端口、活动、约束等都在这个命名空间里。

### 4.2 `Diagrams` / `DiagramRepresentation`

这是图表示层。
图的名字、上下文、图类型、notation id、used objects、binary stream identity 都在这里。

这层信息不是“业务语义”，更接近“建模工具画布如何组织图对象”的信息。

### 4.3 `Blocks` / `PortsAndFlows`

这是 SysML stereotype application 层。
例如：

- `Blocks:Block` 表示某个 `uml:Class` 被施加了 Block stereotype
- `PortsAndFlows:ProxyPort` 表示某个 `uml:Port` 被施加了 ProxyPort stereotype

### 4.4 `domain`

这个命名空间主要出现在：

- `domain:StereotypeInstance`

它用来把某个注解对象、图对象、profileApplication 对象和具体 stereotype 类型绑定起来。

---

## 5. 当前样例的顶层对象清单

以下统计来自当前样例文件本身，仅用于帮助理解其“对象谱系”，不应被当成格式硬规则。

### 5.1 `packagedElement` 的样例分布

当前样例中，`uml:Package(name="测试用例")` 下至少包含：

| `packagedElement` 类型 | 数量 | 说明 |
|------|------:|------|
| `uml:Package` | 1 | 顶层包，名为 `测试用例` |
| `uml:Class` | 2 | 一个是顺序图承载类 `测试用例`，一个是状态机承载类 `StateMachine` |
| `uml:Signal` | 18 | 信号定义，部分带 payload 属性 |
| `uml:SignalEvent` | 11 | 信号事件，引用 `uml:Signal` |
| `uml:ChangeEvent` | 3 | 变化事件，内部携带表达式 |
| `uml:TimeObservation` | 4 | 时间观测 |
| `uml:TimeEvent` | 22 | 时间事件 |
| `uml:DurationObservation` | 18 | 持续时间观测 |

### 5.2 重要的顶层业务对象

当前样例最重要的业务对象是：

- `uml:Package(name="测试用例")`
- `uml:Class(name="测试用例")`
- `uml:Interaction(name="测试用例")`
- `uml:Class(name="StateMachine")`
- `uml:StateMachine(name="StateMachine")`

也就是说，这个文件里至少同时包含：

- 一个顺序图模型
- 一个状态机模型
- 多个活动图模型

因此它是一个“项目级”建模文件，不是单图单文件格式。

---

## 6. 一个更接近真实内容的骨架图

把当前样例压缩成骨架结构，大致是：

```xml
<xmi:XMI>
  <uml:Model name="model">
    <ownedComment>...</ownedComment>

    <packagedElement xmi:type="uml:Package" name="测试用例">
      <eAnnotations>包级图信息</eAnnotations>

      <packagedElement xmi:type="uml:Signal" name="Sig1"/>
      <packagedElement xmi:type="uml:Signal" name="Sig2"/>
      ...

      <packagedElement xmi:type="uml:Class" name="测试用例" classifierBehavior="interaction_id">
        <ownedBehavior xmi:type="uml:Interaction" xmi:id="interaction_id">
          <lifeline .../>
          <fragment .../>
          <message .../>
          <ownedRule .../>
        </ownedBehavior>
      </packagedElement>

      <packagedElement xmi:type="uml:Class" name="StateMachine" classifierBehavior="stm_id">
        <ownedAttribute .../>   <!-- 变量 -->
        <ownedAttribute .../>   <!-- 端口 -->
        <ownedBehavior xmi:type="uml:StateMachine" xmi:id="stm_id">
          <region>
            <subvertex .../>
            <transition .../>
            <subvertex xmi:type="uml:State" name="Control">
              <region>...</region>
              <region>...</region>
              <region>...</region>
              <region>...</region>
            </subvertex>
          </region>
        </ownedBehavior>
        <ownedOperation .../>
        <nestedClassifier xmi:type="uml:Enumeration" .../>
      </packagedElement>

      <packagedElement xmi:type="uml:SignalEvent" .../>
      <packagedElement xmi:type="uml:ChangeEvent" .../>
      <packagedElement xmi:type="uml:TimeObservation" .../>
      <packagedElement xmi:type="uml:TimeEvent" .../>
      <packagedElement xmi:type="uml:DurationObservation" .../>
    </packagedElement>

    <profileApplication .../>
    <profileApplication .../>
    ...
  </uml:Model>

  <Blocks:Block base_Class="..."/>
  <Blocks:ValueType base_DataType="..."/>
  <PortsAndFlows:ProxyPort base_Port="..."/>
</xmi:XMI>
```

这个骨架最重要的含义是：

- `uml:Class` 是很多业务子图的宿主
- 真正的状态机不直接挂在包上，而是挂在 `uml:Class` 的 `ownedBehavior`
- 真正的顺序图也不直接挂在包上，而是挂在另一个 `uml:Class` 的 `ownedBehavior`
- 多个辅助动作图又继续挂在 `entry` / `doActivity` / `effect` 对应的 `uml:Activity` 上

---

## 7. 模型层、图层、stereotype 层的分工

### 7.1 模型层

模型层回答“系统是什么”：

- 有哪些类
- 有哪些状态
- 状态之间如何转移
- 有哪些信号与事件
- 有哪些顺序图消息
- 有哪些变量、端口、枚举

这层主要由 `uml:*` 元素承载。

### 7.2 图表示层

图表示层回答“工具里画了什么图、图引用了哪些对象、图的表示流是什么”。

典型模式是：

```xml
<eAnnotations source="SDSDiagram">
  <contents xmi:type="Diagrams:SDSDiagram"
            name="..."
            context="..."
            ownerOfDiagram="..."
            notationId="..."
            kindId="...">
    <eAnnotations source="SDSDiagram">
      <contents xmi:type="DiagramRepresentation:DiagramRepresentation"
                type="..."
                usedObjects="...">
        <binaryObject xmi:type="DiagramRepresentation:StreamIdentityBinaryObject"
                      streamContentID="..."/>
      </contents>
    </eAnnotations>
  </contents>
</eAnnotations>
```

这层非常重要，但它的重要性不是“状态机语义”，而是：

- 知道某个 UML 元素有哪些图
- 知道图类型，例如状态机图、顺序图、活动图
- 知道图上下文对象是谁
- 知道图中使用了哪些业务对象

### 7.3 stereotype / profile 层

这层回答“某个 UML 元素被施加了哪些 profile/stereotype”。

例如：

- `Blocks:Block base_Class="..."`
- `PortsAndFlows:ProxyPort base_Port="..."`
- `profileApplication -> appliedProfile`

这层对于做“纯状态机结构转换”通常不是第一优先级，但如果后续要：

- 识别 Block / ProxyPort
- 用端口 stereotype 做更强的语义推断
- 保留 SysML 语义

那么这一层不能完全忽略。

---

## 8. 图表示层的具体组织方式

### 8.1 `SDSDiagram` 注解是总入口

在当前样例里，很多模型对象上都挂了：

- `eAnnotations source="SDSDiagram"`

然后在 `contents` 里再放一个：

- `Diagrams:SDSDiagram`

这说明图并不是独立的顶层 XML 文档，而是“挂在模型对象上的注解”。

### 8.2 `context` / `ownerOfDiagram`

`Diagrams:SDSDiagram` 上常见字段有：

- `context`
- `ownerOfDiagram`

在当前样例里，这两个值通常都回指当前图所属的 UML 业务对象，例如：

- 包级块定义图的 `context` 指向那个 `uml:Package`
- 状态机图的 `context` 指向那个 `uml:StateMachine`
- 活动图的 `context` 指向对应的 `uml:Activity`

这意味着，后续如果做“从业务对象反查所有图”，这两个字段很有价值。

### 8.3 `kindId` 是图类型

当前样例里观测到的 `kindId` 包括：

- `BlockDefinationDiagram`
- `SysML Sequence Diagram`
- `SysML State Machine Diagram`
- `Sysml Activity Diagram`

其中 `BlockDefinationDiagram` 这个拼写本身就带工具特征，后续解析时应按原始字面值处理，不要想当然更正为其他拼写。

### 8.4 `notationId`

每个图通常都有一个：

- `notationId="..."`

这说明图的画布信息至少有一个对应的 notation / diagram stream 概念。

### 8.5 `usedObjects`

很多 `DiagramRepresentation:DiagramRepresentation` 上还带有：

- `usedObjects="id1 id2 id3 ..."`

这个字段的意义很直接：

- 当前图中用了哪些模型对象

它非常适合做：

- 图内对象筛选
- 图与模型对象之间的反向索引
- 局部图导出

### 8.6 `binaryObject` 只是流标识，不是完整绘图内容

在当前样例里，图表示层继续下挂：

- `binaryObject xmi:type="DiagramRepresentation:StreamIdentityBinaryObject"`
- `streamContentID="..."`

这里暴露出来的是 **stream identity**，不是完整展开后的几何坐标数据。

因此，根据当前样例能得出的安全结论是：

- XML 本身包含图的身份引用
- 但图的低层画布数据并没有以“可直接阅读的明文几何 XML”形式完整展开在当前文件里

这也解释了一个现象：

- 外部可以存在导出的状态机图或顺序图图片
- 但 XML 里并没有直接引用这些导出图片的文件名
- XML 里关联的是图对象本身的 notation / stream identity

因此：

- 外部图片更像是工具导出的可视化产物
- `XML/XMI` 里存的是建模与图表示元数据
- 导出图片文件名与 `notationId` 之间在当前样例中看不到直接显式映射

---

## 9. 当前样例中的顺序图结构

### 9.1 顺序图宿主对象

顺序图不是直接顶层出现，而是挂在：

- `uml:Class(name="测试用例")`

之下的：

- `ownedBehavior xmi:type="uml:Interaction" name="测试用例"`

这个类还带有：

- `classifierBehavior="_tx-U4CQGEfGBBP-2kAbLRg"`

它回指该 `Interaction`。

### 9.2 顺序图与外部导出图的对应关系

当前样例中的顺序图与一张外部导出的顺序图在内容上是对应的。

图中可以直观看到：

- 两条 lifeline：`控制`、`模块`
- 多条消息
- 多段时间约束、持续时间约束

而这些对象都能在 `uml:Interaction` 下找到对应元素。

### 9.3 主要子元素

顺序图中最核心的元素包括：

- `lifeline`
- `fragment`
- `message`
- `ownedRule`

其中：

- `lifeline` 对应生命线
- `message` 对应消息
- `fragment` 里装有 `MessageOccurrenceSpecification`、`BehaviorExecutionSpecification`、`StateInvariant`
- `ownedRule` 里装有 `TimeConstraint`、`DurationConstraint`

### 9.4 消息的组织方式

顺序图消息不是一个单独标签就结束，而是通过多层对象协同表达：

- `message`
- `sendEvent`
- `receiveEvent`
- `MessageOccurrenceSpecification`

典型关系是：

- `message.sendEvent` 指向某个 `fragment`
- `message.receiveEvent` 指向另一个 `fragment`
- 这两个 `fragment` 分别落在不同 lifeline 上

### 9.5 顺序图中的时间与持续时间元素

当前样例顺序图含有完整的时间相关建模：

- `ownedRule xmi:type="uml:TimeConstraint"`
- `ownedRule xmi:type="uml:DurationConstraint"`
- `packagedElement xmi:type="uml:TimeObservation"`
- `packagedElement xmi:type="uml:DurationObservation"`
- `packagedElement xmi:type="uml:TimeEvent"`

而约束值本身又通过更深层的 `expr` 挂上去，例如：

- `0s`
- `1s`
- `10s`
- `15s`
- `20s-30s`
- `30s`

这说明这个 XML 样例不只有“状态图”，也不只有“消息线”，它还显式建模了时间约束语义。

### 9.6 顺序图中的 `StateInvariant`

样例中还出现多处：

- `fragment xmi:type="uml:StateInvariant"`

其内部 `body` 里有类似：

- `y=2300`
- `y=2099`
- `y=1300`
- `Rmt=4999`

这类内容提醒我们两件事：

- `OpaqueExpression.body` 不一定总是“可执行业务逻辑”
- 同样是 `body` 字段，可能只是图中某种约束说明或状态标注文本

解析时不能一见 `body` 就直接当代码。

---

## 10. 当前样例中的状态机结构

### 10.1 状态机宿主对象

状态机宿主是：

- `uml:Class(name="StateMachine")`

这个类有：

- `classifierBehavior="_6t5EAIMsEfC7Audqg6Dubw"`

它回指其 `ownedBehavior xmi:type="uml:StateMachine" name="StateMachine"`。

此外，这个类还被施加了：

- `Blocks:Block`

即它不仅是 UML 类，同时也是 SysML Block。

### 10.2 状态机与外部导出图的对应关系

这部分模型与一张外部导出的状态机图是对应的。

图片中可以观察到：

- 顶层 `Idle`
- 顶层复合状态 `Control`
- `Control` 内部存在多个并行 region
- 某些子状态内还有嵌套 region，例如 `H`
- 多个 entry / do / effect 动作被标成 `P1`、`P2`、`P3`、`P4`、`ABC`、`DEF`、`L`、`R`、`N`、`Q`、`T`、`Z`、`U`、`Y`、`I`、`X`

这些都能在 XML 中一一找到。

### 10.3 状态机类中除了状态机本体，还有很多别的业务信息

`uml:Class(name="StateMachine")` 本身并不只是一个“壳”。
它至少还包含：

- `ownedAttribute` 普通属性
- `ownedAttribute xmi:type="uml:Port"` 端口
- `ownedOperation` 操作
- `nestedClassifier xmi:type="uml:Enumeration"` 枚举

也就是说，如果后续转换只盯着 `ownedBehavior` 而忽略这个类本体，就会丢掉：

- 变量信息
- 端口信息
- 枚举类型信息

### 10.4 状态机类上的普通属性

当前样例里，`StateMachine` 类上有一批 `ownedAttribute`，例如：

- `current_stage`
- `next_stage`
- `seeker_state_`
- `DeltQz`
- `DeltQy`
- `Path_Point_Number`
- `DDNUM`
- `Hd`
- `H`
- `Zeta0`
- `Path_Psi`
- `Qy`
- `Qz`
- `rmt`
- `Longitude`
- `Latitude`
- `A`
- `atc`

这些属性的特点是：

- 有些带 `type`，指向枚举或 primitive type
- 有些带 `defaultValue`
- 有些带 `lowerValue` / `upperValue`
- 很多还挂了 stereotype instance 注解

这说明变量定义不一定只靠简单 `name + primitive type + init` 三元组表达。

### 10.5 状态机类上的端口

当前样例里，`StateMachine` 类上还定义了一批 `uml:Port`：

- `p_time`
- `p_cmd_start`
- `p_cmd_attack`
- `p_cmd_routefly`
- `p_seeker`
- `p_cmd_engine_ig`
- `p_guidance`
- `p_ins`
- `p_ev_t0`
- `p_info`
- `p_load`
- `p_seeker_in`
- `p_ev_engine_stable`

文件末尾对应还有多条：

- `PortsAndFlows:ProxyPort base_Port="..."`

所以端口不是普通属性的简单别名，而是带 stereotype 的 SysML 端口对象。

### 10.6 状态机类上的枚举

当前样例里可以看到两个 `nestedClassifier xmi:type="uml:Enumeration"`：

- `Stage`
- `SeekerState`

它们各自带有 `ownedLiteral`：

- `Stage` 包含 `None`、`LoadData`、`Idle`、`EngineIgnition`、`RouteFly`、`Attack`
- `SeekerState` 包含 `Off`、`On`、`Stable`

文件尾部又通过：

- `Blocks:ValueType base_DataType="..."`

把这些枚举进一步施加了 SysML value type 语义。

### 10.7 状态机本体的总体层级

状态机本体是：

```xml
<ownedBehavior xmi:type="uml:StateMachine" ...>
  <region>
    <transition .../>
    <subvertex xmi:type="uml:Pseudostate" .../>
    <subvertex xmi:type="uml:State" name="Idle"/>
    <subvertex xmi:type="uml:State" name="Control">
      <region>...</region>
      <region>...</region>
      <region>...</region>
      <region>...</region>
    </subvertex>
  </region>
</ownedBehavior>
```

由此可见：

- 顶层只有一个根 region
- 根 region 下有一个初始伪状态
- 顶层状态至少有 `Idle` 和 `Control`
- `Control` 是复合状态，并且带多个子 `region`

### 10.8 `Control` 是多 region 并行复合状态

这是当前样例对后续转换最关键的结构事实之一。

`Control` 下不是一个 region，而是 **四个** region。
这意味着：

- 该状态不是普通串行复合状态
- 它是 UML 中的 orthogonal / parallel composite state

这和外部导出的状态机图中的布局是一致的：

- `Control` 内部被水平虚线分成多个区域

因此，单从这个样例就已经足以证明：

- 如果后续要把 SysDeSim 状态机转换到 FCSTM，不能假设输入只包含单 region 状态机

### 10.9 样例状态机中的具体状态层次

从 XML 和图片交叉看，当前状态机至少包含以下层次：

- 顶层
  - `Idle`
  - `Control`
- `Control` 的第 1 个 region
  - `A`
  - `B`
  - `C`
  - `D`
  - `E`
- `Control` 的第 2 个 region
  - `F`
  - `W`
  - `H`
  - `G`
  - `H` 内还有子 region
    - `L`
    - `M`
- `Control` 的第 3 个 region
  - `J`
  - `K`
  - `S`
  - `X`
  - `O`
- `Control` 的第 4 个 region
  - `V`

这说明：

- 样例同时存在并行 region
- 样例同时存在多层嵌套
- 样例同时存在 entry / do / effect 行为

### 10.10 transition 的表达方式

状态机中的转移使用：

- `transition xmi:type="uml:Transition"`

典型字段包括：

- `source`
- `target`
- `trigger`
- `guard`
- `effect`

这几种组合在样例里都能观察到。

例如：

- 仅有 `source/target` 的初始转移
- 带 `trigger` 的信号触发转移
- 带 `guard` 的条件转移
- 带 `effect` 的转移

### 10.11 trigger 可能指向不同事件类型

`trigger.event` 在当前样例里可能指向：

- `uml:SignalEvent`
- `uml:ChangeEvent`

也就是说，“转移标签里看上去像事件触发”的东西，底层不一定都是 signal。

### 10.12 guard 与 change event 是两种不同来源

当前样例里既有：

- `transition.guard -> ownedRule -> specification -> body`

也有：

- `trigger.event -> uml:ChangeEvent -> changeExpression -> body`

这两类结构都可能让图上出现“条件式”效果，但语义上不是一回事：

- `guard` 是转移守卫
- `ChangeEvent` 是事件

解析器不能把这两者混为一谈。

### 10.13 entry / doActivity / effect 都是活动对象

当前样例中的状态动作和转移动作不是简单字符串，而是：

- `entry xmi:type="uml:Activity"`
- `doActivity xmi:type="uml:Activity"`
- `effect xmi:type="uml:Activity"`

这意味着：

- 动作标签 `P1` / `P2` / `P3` / `P4` / `ABC` / `DEF` 只是活动对象的名字
- 真正的动作体可能在对应 `uml:Activity` 里展开

### 10.14 有些活动只是名字，有些活动包含自己的内部活动图

例如：

- 某些 `entry` 只表现为一个命名活动，并附带图注解
- 某些 `effect` 会进一步内嵌 `node`、`edge`、`CallBehaviorAction`
- 某些活动还会继续调用另一个 `behavior`

因此，**“动作 = 字符串名字” 只是一种表面现象，不是通用结构规律**。

---

## 11. 活动对象的两种常见形态

### 11.1 仅命名活动

像 `P1`、`P2`、`P3`、`P4` 这类动作，在当前样例的 XML 里通常表现为：

- 一个 `uml:Activity`
- 有 `name`
- 有自己的 `SDSDiagram` 注解

但其具体执行节点没有像更复杂活动那样直接展开很多节点边。

### 11.2 内嵌活动图

像 `ABC`、`DEF` 等动作，在 XML 中会继续包含：

- `edge xmi:type="uml:ControlFlow"`
- `node xmi:type="uml:InitialNode"`
- `node xmi:type="uml:CallBehaviorAction"`
- `node xmi:type="uml:ActivityFinalNode"`

其中 `CallBehaviorAction` 还能继续指向另一个 `behavior`。

这说明动作层本身就是可递归的。

### 11.3 `OpaqueAction` 体内可能是真正的语句文本

样例中还有活动图内部出现：

- `node xmi:type="uml:OpaqueAction"`

这类节点下的 `body` 更像是执行语句，例如示例里能看到：

- `Mode=1;`

这意味着：

- 真正“接近代码”的文本，未必挂在 `entry` / `effect` 顶层
- 也可能藏在更深一层活动节点里

---

## 12. 信号、事件与消息的关系

### 12.1 `Signal` 和 `SignalEvent` 是分开的

当前样例中：

- `uml:Signal` 定义信号实体
- `uml:SignalEvent` 通过 `signal="..."` 引用信号

这和很多 UML XMI 的组织方式一致。

### 12.2 信号本身还可能带 payload 属性

例如当前样例中的部分 `uml:Signal` 具有：

- `ownedAttribute`
- `type`
- `defaultValue`

这说明信号不只是“一个名字”，还可以带参数结构。

### 12.3 顺序图消息也可绑定到 signal

在顺序图里，`uml:Message.signature` 也可能指向某个 `uml:Signal`。

因此：

- 状态机层的 signal/event
- 顺序图层的 message/signature

在样例中实际上共享了一部分底层对象体系。

### 12.4 状态机触发与顺序图消息共享的是 `Signal`，不是同一个 `Event`

这是当前样例里最容易混淆、但也最重要的结构事实之一。

状态机中的触发链通常是：

```xml
<transition ...>
  <trigger ... event="EVENT_ID"/>
</transition>

<packagedElement xmi:type="uml:SignalEvent"
                 xmi:id="EVENT_ID"
                 signal="SIGNAL_ID"/>
```

也就是说，状态机侧的引用链是：

```text
Transition
  -> Trigger.event
  -> SignalEvent
  -> Signal
```

而顺序图中的消息通常是：

```xml
<message ...
         sendEvent="SEND_OCCURRENCE_ID"
         receiveEvent="RECV_OCCURRENCE_ID"
         signature="SIGNAL_ID"/>
```

也就是说，顺序图侧的引用链是：

```text
Message
  -> sendEvent / receiveEvent
  -> MessageOccurrenceSpecification

Message
  -> signature
  -> Signal
```

因此需要明确区分：

- 状态机里的 `Trigger.event` 指向的是 `SignalEvent` 或 `ChangeEvent`
- 顺序图里的 `sendEvent` / `receiveEvent` 指向的是消息发生点 `MessageOccurrenceSpecification`
- 两边真正共享的对象层通常是 `Signal`

结论是：

- **状态机触发事件对象** 与 **顺序图消息发生点对象** 不是同一类对象
- 当前样例中没有看到“状态机 `Trigger.event` 和顺序图某个 occurrence 使用同一 `xmi:id`”这种直接强绑定
- 当前样例中能观察到的强关联，是“状态机 `SignalEvent.signal` 与顺序图 `Message.signature` 共享同一个 `Signal` 的 `xmi:id`”

### 12.5 这种共享是部分共享，不是全覆盖

当前样例进一步说明：

- 一部分状态机 trigger 最终落到 `Signal`
- 一部分状态机 trigger 最终落到 `ChangeEvent`
- 顺序图消息大多通过 `signature` 绑定到 `Signal`

因此：

- 能和顺序图形成稳定交叉引用的，主要是 `Signal` 路径
- `ChangeEvent` 不会天然在顺序图里找到一个同构的对象层

也就是说：

- **不是所有状态机 trigger 都能在顺序图里找到对应对象**
- **但有一批状态机 trigger 和顺序图 message 会共享同一批底层 signal id**

### 12.6 `ChangeEvent` 是独立事件源，不应强行与顺序图消息对齐

当前样例中可见如下结构：

```xml
<packagedElement xmi:type="uml:ChangeEvent" xmi:id="...">
  <changeExpression xmi:type="uml:OpaqueExpression" ...>
    <body>a&lt;b</body>
  </changeExpression>
</packagedElement>
```

以及：

```xml
<packagedElement xmi:type="uml:ChangeEvent" xmi:id="...">
  <changeExpression xmi:type="uml:OpaqueExpression" ...>
    <body>R_mt&lt;5000</body>
  </changeExpression>
</packagedElement>
```

这种对象的关键特点是：

- 它本身就是事件
- 它不是通过 `SignalEvent -> Signal` 这一层转接出来的
- 它更像“条件变化事件”或“表达式为真触发的事件源”

因此在统一建模时，需要把两类触发分开：

- `SignalEvent` 型 trigger
- `ChangeEvent` 型 trigger

如果后续实现只捕获 `SignalEvent -> Signal` 这一条链，那么会漏掉状态机中的一部分真实触发条件。

### 12.7 变量定义与表达式使用之间，不能假设存在 `id` 级强绑定

和 `Signal` 不同，变量在当前样例里的关系要松很多。

状态机类中的正式变量定义通常是：

```xml
<ownedAttribute xmi:type="uml:Property"
                xmi:id="PROPERTY_ID"
                name="rmt"
                .../>
```

这说明：

- `ownedAttribute` / `uml:Property` 是正式建模的变量定义对象

但在 guard、change expression、状态不变量、动作体里，变量使用通常表现为：

```xml
<body>R_mt&lt;5000</body>
```

或：

```xml
<body>Mode=1;</body>
```

或：

```xml
<body>y=2300</body>
```

这里的关键问题是：

- 这些表达式体是普通文本
- 文本内部并没有“引用某个 `Property` 的 `xmi:id`”这一层结构
- 名字甚至可能和属性定义的名字不完全一致

因此和 signal 不同，当前样例中的变量关系更接近：

```text
Property 定义层：结构化对象
Expression 使用层：自由文本
```

这意味着：

- 不能假设“表达式里出现的名字”一定能直接回链到某个 `ownedAttribute` 的 `xmi:id`
- 变量关联往往需要额外的文本解析、命名归一化或启发式匹配
- 这一点比 signal/event 的关系要弱得多

### 12.8 `y` 不是当前样例里的正式状态机变量

当前样例中，`y` 出现的位置是顺序图的 `StateInvariant` 文本，例如：

```xml
<fragment xmi:type="uml:StateInvariant" ...>
  <invariant ...>
    <specification xmi:type="uml:OpaqueExpression" ...>
      <body>y=2300</body>
    </specification>
  </invariant>
</fragment>
```

并且还会出现：

- `y=2099`
- `y=1300`
- `y=1199`

从当前样例能得出的稳妥结论是：

- `y` 在这里是顺序图状态不变量中的文本内容
- 它不是当前样例中以 `ownedAttribute name="y"` 形式出现的正式状态机属性
- 因此也看不到它和某个模型变量之间的 `id` 级关联

换句话说：

- `y` 更像“图上的约束/说明文本”
- 不像“宿主类上的结构化变量定义”

### 12.9 `rmt` 说明变量定义层和表达式层可能存在命名漂移

当前样例中可以同时观察到：

- 类属性里有 `ownedAttribute name="rmt"`
- 顺序图文本里出现 `Rmt=4999`
- `ChangeEvent` 表达式里出现 `R_mt&lt;5000`

这至少说明两件事：

- 文本层变量名和结构化属性名不一定大小写一致
- 文本层变量名甚至可能带下划线变体

因此在这类 XMI 上做变量关联时，至少要防备：

- 大小写漂移
- 下划线风格漂移
- “图上文本名”与“模型属性名”不完全一致

这也是为什么本文不建议对变量做“天然存在稳定 `id` 绑定”的假设。

---

## 13. `xmi:id` 与引用机制

当前样例最核心的组织机制是：

- 所有对象先定义 `xmi:id`
- 各种关系通过 id 回指

因此，解析器的第一基本动作应当是：

- 构建全局 `xmi:id -> element/object` 索引

### 13.1 当前样例中的典型引用关系

| 引用位置 | 指向对象 | 含义 |
|------|------|------|
| `classifierBehavior` | `ownedBehavior` | 类的主行为 |
| `transition.source` | `subvertex` | 转移源状态 |
| `transition.target` | `subvertex` | 转移目标状态 |
| `trigger.event` | `SignalEvent` / `ChangeEvent` | 转移触发事件 |
| `SignalEvent.signal` | `Signal` | 事件绑定信号 |
| `message.sendEvent` | `fragment` | 消息发送端 |
| `message.receiveEvent` | `fragment` | 消息接收端 |
| `lifeline.represents` | `ownedAttribute` | lifeline 所表示的属性 |
| `base_Class` | `uml:Class` | stereotype 施加到哪个类 |
| `base_Port` | `uml:Port` | stereotype 施加到哪个端口 |
| `context` | 某 UML 元素 | 图属于哪个模型对象 |
| `usedObjects` | 多个 UML 元素 | 图中使用了哪些对象 |

### 13.2 为什么必须先索引再解析

如果不先建索引，后续几乎所有解析都会变得脆弱：

- 读状态机转移时找不到 state
- 读 trigger 时找不到 event
- 读 `SignalEvent` 时找不到 signal
- 读图注解时找不到 context
- 读 stereotype application 时找不到 base 元素

因此，对于这种格式，**两阶段解析** 几乎是必需的：

1. 第一阶段收集元素与原始属性，建立全局 id 表
2. 第二阶段再做关系链接和语义归一化

---

## 14. 与外部导出图的对应关系

### 14.1 状态机图

这张图对应：

- `uml:Class(name="StateMachine")` 下的
- `ownedBehavior xmi:type="uml:StateMachine" name="StateMachine"`

它对应的图表示注解里可以看到：

- `kindId="SysML State Machine Diagram"`
- `name="StateMachine"`

### 14.2 顺序图

这张图对应：

- `uml:Class(name="测试用例")` 下的
- `ownedBehavior xmi:type="uml:Interaction" name="测试用例"`

它对应的图表示注解里可以看到：

- `kindId="SysML Sequence Diagram"`
- `name="测试用例1"`

### 14.3 外部导出图与 XML 内部图 id 的关系

当前样例里没有看到下面这种直接关系：

- XML 显式写出外部导出图的文件名

XML 里实际出现的是：

- `notationId`
- `streamContentID`

所以从当前样例能得到的稳妥结论是：

- 外部图片是导出产物
- XML 里关联的是图对象和 notation/binary stream identity
- 外部图片文件名并不是 XML 中的一等引用对象

---

## 15. 对后续解析器实现的直接启示

### 15.1 不要把它当成“状态机专用 XML”

至少对当前样例而言，这个文件是：

- 多图
- 多模型
- 多 profile
- 多层注解

的综合容器。

### 15.2 先区分“要解析的层”

对状态机转换而言，建议优先级如下：

1. 先抓模型层
2. 再按需抓少量图层元数据
3. 最后决定是否保留 stereotype 层

### 15.3 图层元数据不应和业务结构混洗

对于 `SDSDiagram`、`DiagramRepresentation`、`binaryObject`：

- 解析器应能识别
- 但不应让它们污染核心状态机 IR

合理做法是：

- 作为可选 metadata 单独挂载
- 或在 phase 0 直接忽略

### 15.4 不能假设 action 只有名字

样例已经证明：

- action 可能只是命名引用
- action 也可能有完整活动图
- action 中还可能包含 `OpaqueAction.body`

因此，如果后续需要做动作转换，必须先明确支持范围。

### 15.5 不能假设复合状态只有单 region

样例中的 `Control` 明确是多 region 并行复合状态。

所以任何“先把 SysDeSim 状态机转换成 FCSTM”的实现，如果默认：

- 一个复合状态只有一个子 region

那它在这个样例上就已经不成立。

### 15.6 不能把 `ChangeEvent` 误当 `guard`

这两者在图面上都可能显示为条件式标签，但底层不是一个概念。

### 15.7 顺序图和状态机可能共享同一批底层信号对象

这意味着项目级建模文件中，不同图之间不是完全隔离的。

### 15.8 `Signal` 适合做跨图关联，变量文本不适合直接做强绑定

如果后续要做跨图追踪，当前样例给出的最稳妥策略是：

- 优先使用 `Signal` / `SignalEvent` 这条显式 `id` 链
- 对变量只做“定义层”和“文本层”的弱关联，不要默认存在正式回指

换句话说：

- `signal` 关系更像“结构化引用”
- `变量名` 关系更像“需要额外解析的文本约定”

---

## 16. 面向当前样例的转换修改方案

本节不讨论“理想的一般 UML/XMI 全支持方案”，而是讨论一个更聚焦、也更适合当前样例的实现方向。

这里需要先把目标说清楚：

- 当前样例不是一个普通演示样例
- 它就是 TIMELINE 计划的真实输入样本
- 因此后续转换目标不应再是“尽量完整地把 XML 全部翻译成 FCSTM”
- 而应优先抽取 **TIMELINE 真正需要的状态机语义与场景语义**

下文提到的 `step`、`SetInput`、`TimelineMachineBinding`、`event_map`、`input_map`、只读外部输入、单步闭包求值等术语，均以《TIMELINE_DESIGN.md》中的设计为准。

换句话说，当前样例的合理主线应从：

```text
尽量完整导入类属性
  -> 再尝试生成 FCSTM
```

改成：

```text
提取状态机主干
  -> 统一整理 signal / change / guard 触发
  -> 提取顺序图中的输入变化与事件线索
  -> 对接 TIMELINE 的 event_map / input_map / step / SetInput
```

### 16.1 当前样例应按“timeline-first”而不是“fcstm-first”处理

参考《TIMELINE_DESIGN.md》的核心约束，当前样例更适合被拆成四类信息：

- **状态机结构**
  - 叶状态、复合状态、初始伪状态、转移声明顺序
- **机器内事件语义**
  - `SignalEvent` 对应的机器内 event path
- **条件触发语义**
  - `ChangeEvent` 与 `guard` 统一后的条件边
- **场景观测语义**
  - 顺序图中的消息、赋值、状态不变量与出现顺序

其中前两类主要服务于 `TimelineMachineBinding.event_map`，后两类主要服务于 `input_map`、`SetInput`、以及 step 上的 guard 求值。

因此，当前样例的首要产物不应只是一个“尽力导出的 `.fcstm` 文件”，而应至少包括下面这些抽象结果：

- 可导出为 FCSTM 的状态机主干
- 可映射到 `event_map` 的机器内事件路径
- 可映射到 `input_map` 的条件变量名集合
- 可映射到 `SetInput` 的顺序图赋值观测流

纯 FCSTM 导出仍然有价值，但在这个样例里，它更适合作为兼容产物，而不是唯一主目标。

### 16.2 变量导入范围应主动收缩

对当前样例而言，宿主类上的 `ownedAttribute` 数量明显多于真正参与状态跳转语义的量。

因此推荐把变量分成三类：

#### A. 主动忽略的属性

默认直接忽略以下属性，不进入 FCSTM `def` 定义：

- 仅作为宿主类数据成员存在，但未出现在任何状态机条件、动作文本、顺序图观测文本中的属性
- 枚举型属性，尤其是当前转换器根本不支持的非 `int/float` 类型属性
- 明显偏设计时结构信息的属性，例如仅用于类建模、端口绑定、说明展示的字段

对当前样例中的这类属性，推荐默认忽略，而不是视为错误。

#### B. 条件参与型名字

仅当某个名字实际出现在以下位置时，才把它加入“候选语义变量集”：

- `ChangeEvent.changeExpression.body`
- `guard` 的 `OpaqueExpression.body`
- 动作体里的 `OpaqueAction.body`
- 顺序图中的 `StateInvariant.body`

这类名字不要求先在 `ownedAttribute` 里有完美对应，只要求它们在文本层具有稳定可识别的名字。

更重要的是，对于 TIMELINE 来说，这类名字默认更像：

- `input_map` 里的机器内 guard 变量名
- 也就是由场景提供、状态机只读的 external input 名字

而不是必须先把它们视为“机器内部可写变量”。

#### C. 真正需要落到 FCSTM 的变量

只有当某个名字满足下面任一条件时，才真正为其发出 FCSTM `def`：

- 纯状态机兼容导出时，需要它作为 guard 里的自由变量保留
- TIMELINE 绑定阶段，需要它作为 `input_map` 中的机器内局部名保留
- 后续动作体转换确实需要读写它

这意味着：

- 不应为了“完整导入”而发出几十个无用 `def`
- 只需要发出状态机主干真正依赖的那几个量
- 对于只出现在条件里的量，应优先按“外部输入名字”理解，而不是按“内部状态变量”理解

### 16.3 枚举型或非数值型 property 不应阻塞转换

当前实现把非 `int/float` 的显式 property 当成硬错误，这对于当前样例并不合适。

更合理的策略是：

- 对未被状态机主干使用的枚举型 property，直接忽略
- 对被条件或动作文本引用到、但当前又无法安全表达的枚举型 property，生成 warning，而不是立刻中止整个转换

这条策略的本质是：

- **“能不能完整导入类属性”** 不应凌驾于 **“能不能抽取 TIMELINE 所需状态机主干”** 之上

### 16.4 应引入统一的“条件触发”抽象层

当前样例说明，状态机里的触发来源至少有三种：

- `SignalEvent`
- `ChangeEvent`
- 文本型 `guard`

当前实现把它们拆得太开，会导致：

- `SignalEvent` 可以继续走
- `ChangeEvent` 被判成不支持
- `guard` 只被当普通 guard 处理，无法和 `ChangeEvent` 合流

对当前样例更合适的导入抽象应当是：

```text
TriggerSignal
TriggerCondition
TriggerNone
```

其中：

- `TriggerSignal` 对应 `SignalEvent`
- `TriggerCondition` 统一承载 `ChangeEvent` 和文本型 `guard`
- `TriggerNone` 对应无显式触发的转移

这里的关键不是立刻改 FCSTM 语法，而是先改 **导入 IR 的触发抽象**。

对 TIMELINE 而言，这个抽象的意义在于：

- `TriggerSignal` 更自然地进入 `event_map`
- `TriggerCondition` 更自然地进入“guard over inputs”的单步求值框架
- `TriggerNone` 对应没有外部 `emit` 时仍可能在 step 中被评估的边

### 16.5 `ChangeEvent` 和 `guard` 应统一视为同类条件触发

对于当前样例，建议采用下面的规则：

- `ChangeEvent.changeExpression.body` 归一化后，生成一个 `ConditionTrigger`
- `guard` 的 `OpaqueExpression.body` 归一化后，也生成一个 `ConditionTrigger`
- 归一化后表达式相同的两者，应视为同一类触发源

也就是说：

- 不再把 `ChangeEvent` 当成“特殊不支持项”
- 也不再把 `guard` 仅仅视为转移附属条件
- 而是先在导入层把它们统一成“条件型事件”或“条件型触发”

这是“把 change event 一概当作特殊 event，guard 也一并合流”的核心落点。

### 16.6 同源同宿同条件的 `ChangeEvent` / `guard` 应合并

这条规则对当前样例尤其重要。

建议在 IR 层引入一个稳定键：

```text
(source_state_id, target_state_id, normalized_condition_expr)
```

然后按这个键做去重。

如果出现以下情况：

- 同一个 `source`
- 同一个 `target`
- 一个转移来自 `ChangeEvent(expr)`
- 另一个转移来自 `guard(expr)`
- 且两个 `expr` 归一化后相同

那么应当把它们视为 **同一个 condition-event transition**，而不是两个独立转移。

这样处理的收益是：

- 避免重复边
- 避免同一语义条件在后续顺序图联动时重复触发
- 更贴近“这其实是同一触发语义被工具放在了不同槽位里”这一现实

若一个转移同时有：

- `ChangeEvent(expr_a)`
- `guard(expr_b)`

并且两者归一化后不相同，那么建议把它统一成：

```text
ConditionTrigger(expr_a AND expr_b)
```

也就是在 IR 层视为一个复合条件触发，而不是两条割裂的判断路径。

### 16.7 条件名字应优先进入 `input_map` 语义，而不是内部可写变量语义

这一点是把当前样例真正接到 TIMELINE 上的关键。

根据《TIMELINE_DESIGN.md》的约束，第一阶段的 guard 应优先读取：

- 外部输入快照

而不是机器内部可写状态。

因此，对于像 `y` 这类名字，若它们满足：

- 出现在 `ChangeEvent` / `guard` / 状态不变量文本里
- 能在顺序图中观察到 `name=value` 形式的变化
- 但没有明确、可靠、必须保留的内部写入语义

那么更合理的解释是：

- 它们首先是 TIMELINE 的场景输入
- 在 binding 上表现为 `scenario_name -> machine_local_name`
- 即 `TimelineMachineBinding.input_map`

而不是先急着把它们解释成状态机内部持久变量。

只有当某个名字明确出现在机器动作的赋值左侧，并且这种写语义对状态机主干不可忽略时，才应把它回收为“内部可写状态变量”。

### 16.8 顺序图应被视为场景来源，而不是附属说明图

你提到的核心点是正确的：

- 当前样例里的很多“变量意义”并不来自类属性定义
- 而是来自顺序图中那些值变化、状态不变量和消息上下文

因此推荐的方向是：

- 不把顺序图仅仅当作附属说明图
- 而是把它当作 **TIMELINE 场景的候选来源**

更具体地说：

- 顺序图中的消息，可作为 `emit(...)` 的候选来源
- 顺序图中的 `name=value` 文本，可作为 `SetInput(...)` 的候选来源
- 顺序图中的出现顺序，可作为 `step_0, step_1, ...` 的候选顺序

也就是说，这个样例的顺序图不只是“给状态机做注释”，而是在为 TIMELINE 提供场景层骨架。

### 16.9 顺序图联动的最小实现应以“赋值观测流 -> SetInput 候选”开始

顺序图并不一定能完整还原可执行语义，因此初始实现不应过度承诺。

建议先只做一个很小、但稳定的子集：

- 从 `StateInvariant.body`
- 从活动体 `OpaqueAction.body`
- 从其他类似 `name=value` 的简单文本

中提取出：

```text
变量名
赋值值
出现顺序
所属图上下文
```

把这类信息建成一个独立的“赋值观测流”。

对 TIMELINE 来说，这个观测流最自然的落点不是“直接改写机器内部变量”，而是：

- 作为 `SetInput(name=value)` 的候选集合
- 或作为初始输入快照的候选来源

这一步不需要先解决完整求值问题，只要能建立：

- `y` 被更新过
- `Rmt` 被更新过
- 更新发生在顺序图的哪个阶段附近

就已经足够支撑下一步联动。

### 16.10 条件触发与赋值观测的联动，应遵守 TIMELINE 的 step 语义

在当前样例上，建议先采用一个保守且可实现的规则：

- 如果某个 `ConditionTrigger` 依赖变量 `y`
- 而顺序图赋值观测流里出现了 `y = ...`
- 则把这次赋值视为该条件触发的一次候选激活时机

然后再做：

- 条件表达式求值
- 若由 false 变 true，则认为该 condition-event 被触发

例如：

```text
ConditionTrigger: y < 2100
Observation stream: y=2300 -> y=2099
```

则可在 `y=2099` 这一时刻把该条件触发视为命中。

但这里不应停留在“命中”这个抽象说法，而应进一步对齐《TIMELINE_DESIGN.md》的 step 语义：

- 同一步中的 `SetInput` 先更新输入快照
- 该 step 上的 guard 与条件触发读取这个更新后的快照
- 若该 step 还有外部事件，则事件也在这个快照上参与选择
- 即使该 step 没有事件，guard-only / condition-only 转移仍应被评估

因此，顺序图联动后的最低落地形式应接近：

```text
step_k:
  SetInput(y = 2099)
  EmitEvent(...)
  evaluate TriggerCondition(y < 2100) on updated snapshot
```

或者在没有显式消息时：

```text
step_k:
  SetInput(y = 2099)
  evaluate guard-only / condition-only transitions
```

这和 TIMELINE 中“输入更新对当前 step 立即可见”的语义是一致的。

### 16.11 名字归一化必须早于 `input_map` 与条件联动

由于当前样例里已经观察到：

- `rmt`
- `Rmt`
- `R_mt`

这类命名漂移，所以条件联动之前必须做一层名字归一化。

推荐最小规则：

- 忽略大小写
- 去除下划线
- 做统一 token 化后再比较

也就是说，在联动层面应把：

- `rmt`
- `Rmt`
- `R_mt`

视为同一候选变量名。

否则：

- 顺序图的赋值观测无法稳定映射到 `SetInput`
- 状态机条件里的自由变量也无法稳定进入 `input_map`

### 16.12 FCSTM 导出应作为兼容模式，TIMELINE 抽取应作为主模式

这里需要区分两个层次：

#### A. TIMELINE 主模式

在主模式下，导入结果应优先服务：

- 状态机主干抽取
- `event_map` 候选生成
- `input_map` 候选生成
- `SetInput` / `emit` / `step` 候选生成

此时，`TriggerCondition` 的主要作用是进入 TIMELINE 的“guard over inputs + 单步闭包求值”框架。

#### B. FCSTM 兼容导出模式

在兼容模式下：

- 条件触发仍可回落成 FCSTM guard transition
- 这样不必立即改造 FCSTM runtime

也就是说：

- 导入 IR 先统一按 timeline-friendly 的方式抽象
- 最终再根据输出目标，决定是“导出 FCSTM”，还是“导出 timeline 所需绑定/场景信息”

### 16.13 推荐实现顺序

如果按当前样例优先来推进，推荐的实现顺序是：

1. 取消“所有 property 必须可导入”的假设，只保留状态机主干相关变量。
2. 把 `ChangeEvent` 和 `guard` 都统一读成 `ConditionTrigger`。
3. 对 `(source, target, normalized_expr)` 做去重，合并同语义的 `ChangeEvent/guard`。
4. 把条件变量优先标记为 `input_map` 候选，而不是内部变量。
5. 增加顺序图侧的“赋值观测流”与“消息观测流”提取。
6. 先把赋值观测流落成 `SetInput` 候选，把消息落成 `emit` 候选，并保留出现顺序形成 step 骨架。
7. 在 TIMELINE 模式下，让条件触发在更新后的输入快照上求值。
8. 最后再补一个纯状态机兼容导出，把 `ConditionTrigger` 回落成 FCSTM guard transition。

这个顺序的好处是：

- 前三步就能先解决当前 XML 转不出来的问题
- 第四到第七步能把这个真实样例真正接到 TIMELINE 计划上
- 第八步再把纯 FCSTM 导出作为兼容能力补齐

### 16.14 本方案的边界

这套方案是针对当前样例的务实收缩，不是通用 UML 语义的完整结论。

它默认接受以下取舍：

- 允许忽略大量与状态机主干无关的 property
- 允许把 `guard` 事件化或条件触发化建模
- 允许把顺序图文本当作 TIMELINE 场景线索，而不是严格可执行规范
- 允许先抽取 `step` / `emit` / `SetInput` 候选，而不是一次性恢复完整时序仿真
- 允许把很多条件名字优先解释为只读 environment input，而不是内部持久状态

如果目标是“先让当前这个真实样例能稳定接入 TIMELINE，再逐步增强泛化能力”，那么这个取舍是合理的。

---

## 17. 当前样例中仍然不确定的部分

基于当前文件本身，仍有一些信息不能被过度推断：

### 17.1 `binaryObject` 对应的底层画布内容格式

当前样例只暴露了：

- `StreamIdentityBinaryObject`
- `streamContentID`

但没有把低层绘图数据明文展开出来。

因此还不能仅凭这个样例断言：

- 所有几何信息都内嵌在同一 XML 中
- 或者几何信息一定可直接从同文件明文恢复

### 17.2 工具导出变体是否总是同样布局

当前样例来自一个具体版本和具体工具链。
其他版本是否：

- 使用相同 `kindId`
- 使用相同 annotation 树
- 使用相同 `domain:StereotypeInstance` 挂法

仍需更多样例验证。

### 17.3 活动图动作体的“可执行语义”范围

当前样例里有：

- 命名活动
- `CallBehaviorAction`
- `OpaqueAction`

但不能仅凭这一个样例断言：

- 所有 SysDeSim 动作都能稳定降到统一语句子集

---

## 18. 总结

当前样例的最重要结构事实可以归纳为：

- 它是 **UML/SysML XMI + 工具私有图元数据 + stereotype application** 的综合文件
- 文件里同时包含 **状态机、顺序图、活动图、信号、事件、枚举、端口、约束**
- 业务模型和图表示信息没有分成不同文件，而是通过 `eAnnotations` 和 `SDSDiagram` 挂接在同一个 XMI 里
- 大量关系通过 `xmi:id` 回指，因此解析必须先建全局索引
- 外部导出的状态机图和顺序图分别对应 XML 里的状态机图和顺序图对象，但 XML 里引用的是 notation/stream identity，而不是导出图片文件名
- 状态机 trigger 与顺序图 message 的**直接共享层通常是 `Signal`**，而不是同一个 `Event` 对象
- 变量定义通常是 `ownedAttribute`，但变量使用常常只出现在 `OpaqueExpression.body` 这类文本字段里，因此**不能默认存在 `id` 级变量绑定**
- 对当前样例更可行的工程路线是：**忽略大部分与状态机主干无关的 property，把 `ChangeEvent` 和 `guard` 统一提升为条件事件，再与顺序图中的赋值观测做联动**
- 对后续状态机转换最关键的两个输入事实是：
  - 当前样例存在 **多 region 并行复合状态**
  - 当前样例中的 `entry` / `doActivity` / `effect` 是 **活动对象**，不是简单字符串

因此，后续如果继续做 SysDeSim 到 FCSTM 的转换，正确的出发点应当是：

- 先把这个 XML 当成标准 UML/XMI 项目容器来拆
- 再在其上提取“状态机相关子图”
- 最后再讨论 lowering 和转换策略
