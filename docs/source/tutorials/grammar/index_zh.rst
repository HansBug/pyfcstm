FCSTM 语法高亮指南
===============================================

pyfcstm 通过多种实现方式为 FCSTM DSL 代码提供原生语法高亮支持，使您能够在文档、编辑器和开发工具中展示格式优美的状态机代码。

概述
---------------------------------------

多种互补的实现方式提供全面的语法高亮和语言支持：

1. **Pygments 词法分析器** - 用于 Python 生态系统工具（Sphinx、Jupyter 等）
2. **TextMate 语法** - 用于支持 TextMate 语法的编辑器（Sublime Text 等）
3. **VS Code 扩展** - 具有高级功能的全面语言支持（语法诊断、代码补全、文档符号、悬停文档）

所有实现都基于 ANTLR 语法，支持完整的 FCSTM 语法，包括关键字、运算符、字面量、注释和内置函数。

在 Python 中使用 Pygments
---------------------------------------

安装
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pygments 支持作为核心依赖项包含在内，安装 pyfcstm 时会自动可用：

.. code-block:: bash

   pip install pyfcstm

FCSTM 词法分析器注册为 Pygments 入口点，使其在系统范围内可用。

基本用法
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**在 Python 代码中：**

.. code-block:: python

   from pygments import highlight
   from pygments.formatters import HtmlFormatter, TerminalFormatter
   from pygments.lexers import get_lexer_by_name

   # 加载 FCSTM 词法分析器
   lexer = get_lexer_by_name("fcstm")

   # 您的 FCSTM 代码
   code = """
   def int counter = 0;

   state MyState {
       enter {
           counter = 0;
       }

       during {
           counter = counter + 1;
       }
   }
   """

   # 生成带语法高亮的 HTML
   html = highlight(code, lexer, HtmlFormatter())
   print(html)

   # 或在终端中显示彩色输出
   terminal_output = highlight(code, lexer, TerminalFormatter())
   print(terminal_output)

**在 Jupyter Notebook 中：**

.. code-block:: python

   from IPython.display import HTML
   from pygments import highlight
   from pygments.formatters import HtmlFormatter
   from pygments.lexers import get_lexer_by_name

   lexer = get_lexer_by_name("fcstm")
   formatter = HtmlFormatter(style='monokai')

   code = """state Active { enter { counter = 0; } }"""

   # 显示带语法高亮的代码
   HTML(f"<style>{formatter.get_style_defs()}</style>{highlight(code, lexer, formatter)}")

在 Sphinx 文档中使用
---------------------------------------

配置
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

安装 pyfcstm 后，FCSTM 词法分析器会自动在 Sphinx 中注册。在您的 ``conf.py`` 中添加以下内容：

.. code-block:: python

   # 注册 FCSTM Pygments 词法分析器以支持语法高亮
   from pyfcstm.highlight.pygments_lexer import FcstmLexer
   from sphinx.highlighting import lexers

   # 在 Sphinx 中注册词法分析器
   lexers['fcstm'] = FcstmLexer()
   lexers['fcsm'] = FcstmLexer()  # 备用别名

   print("✓ FCSTM Pygments 词法分析器注册成功")

此注册应放在导入项目元数据之后、Sphinx 配置变量之前。

在 RST 文件中使用
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

配置完成后，您可以在任何 RST 文件中使用 ``code-block`` 指令来实现 FCSTM 语法高亮：

.. code-block:: rst

   .. code-block:: fcstm

      def int counter = 0;
      def float temperature = 25.5;

      state TrafficLight {
          >> during before {
              counter = counter + 1;
          }

          state Red {
              enter {
                  counter = 0;
              }
          }

          state Yellow;
          state Green;

          [*] -> Red;
          Red -> Green : if [counter >= 10];
          Green -> Yellow :: Change;
          Yellow -> Red;
      }

结果将是格式优美的 FCSTM 代码，关键字、运算符、字面量和注释都有适当的着色。

**示例输出：**

.. code-block:: fcstm

   def int counter = 0;
   def float temperature = 25.5;

   state TrafficLight {
       >> during before {
           counter = counter + 1;
       }

       state Red {
           enter {
               counter = 0;
           }
       }

       state Yellow;
       state Green;

       [*] -> Red;
       Red -> Green : if [counter >= 10];
       Green -> Yellow :: Change;
       Yellow -> Red;
   }

使用 TextMate 语法
---------------------------------------

TextMate 语法为支持 TextMate 语法的编辑器提供语法高亮，包括 VS Code 和 Sublime Text。

位置
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TextMate 语法文件位于：

.. code-block:: text

   editors/fcstm.tmLanguage.json

该语法文件作为编辑器集成的基础，并与 ANTLR 语法定义保持同步。

Sublime Text 集成
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. 打开 Sublime Text
2. 导航到 ``Preferences → Browse Packages``
3. 创建新目录：``FCSTM``
4. 将 ``fcstm.tmLanguage.json`` 复制到此目录
5. 重启 Sublime Text
6. 现在 ``.fcstm`` 扩展名的文件将具有语法高亮

VS Code 扩展
---------------------------------------

pyfcstm 项目包含了一个全面的 VS Code 扩展，提供超越基本语法高亮的高级语言支持。

概述
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

VS Code 扩展是一个轻量级、可离线使用的 FCSTM 编写工具，遵循以下设计原则：

- 运行时语言中立（无 Python 或 Java 依赖）
- 兼容广泛的 VS Code 版本（1.60.0+）
- 核心编辑器功能完全离线
- 使用 ANTLR 作为真实来源的语法驱动开发

功能特性
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

扩展提供全面的语言支持：

**基础功能：**

- 所有 FCSTM 语言元素的语法高亮
- 注释切换（``Ctrl+/`` 或 ``Cmd+/`` 用于行注释）
- 块注释支持（``Shift+Alt+A`` 或 ``Shift+Option+A``）
- 自动关闭括号、引号和注释块
- 使用区域标记进行代码折叠
- FCSTM 感知的标记选择，支持标识符、事件和字面量

**高级功能：**

- **语法诊断** - 在问题面板中实时错误检测和清晰的错误消息
- **文档符号** - 通过大纲视图导航状态机结构

  - 变量（``def int``、``def float``）
  - 状态（叶状态和复合状态）
  - 伪状态
  - 事件
  - 嵌套状态层次结构

- **代码补全** - IntelliSense 支持：

  - 关键字（``state``、``def``、``event``、``enter``、``during``、``exit`` 等）
  - 内置常量（``pi``、``E``、``tau``、``true``、``false``）
  - 内置函数（``sin``、``cos``、``sqrt``、``abs``、``log`` 等）
  - 文档本地符号（变量、状态、事件）

- **悬停文档** - 上下文帮助：

  - 事件作用域运算符（``::``、``:``、``/``）
  - 伪状态标记（``[*]``）
  - 关键字（``pseudo``、``effect``、``abstract``、``ref``、``named`` 等）
  - 生命周期切面（``during before/after``、``>> during before/after``）

- **代码片段** - 常见 FCSTM 模式的快速模板：

  - 变量定义（``defi``、``deff``）
  - 状态声明（``state``、``stateb``、``pstate``、``staten``）
  - 事件定义（``event``、``eventn``）
  - 转换（``init``、``trans``、``transe``、``transg``、``transeff``、``transfull``）
  - 生命周期动作（``enter``、``during``、``exit``、``dbefore``、``dafter``）
  - 切面动作（``globalbefore``、``globalafter``）
  - 动作修饰符（``eabstract``、``eref``）

安装
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**从 VSIX 包安装**

从 `GitHub releases 页面 <https://github.com/hansbug/pyfcstm/releases>`_ 下载 ``.vsix`` 文件并安装：

.. code-block:: bash

   code --install-extension fcstm-language-support-0.1.0.vsix

或通过 VS Code UI 安装：

1. 打开 VS Code
2. 进入扩展视图（``Ctrl+Shift+X`` 或 ``Cmd+Shift+X``）
3. 点击扩展视图顶部的 ``...`` 菜单
4. 选择 "Install from VSIX..."
5. 选择下载的 ``.vsix`` 文件
6. 重新加载 VS Code

**从源代码构建**

前置要求：

- Node.js（v20 或更高版本）和 npm
- Java（JDK 11 或更高版本）- ANTLR 解析器生成所需
- Python（3.8 或更高版本）- ANTLR 设置所需
- Git

构建步骤：

1. 克隆仓库：

   .. code-block:: bash

      git clone https://github.com/hansbug/pyfcstm.git
      cd pyfcstm

2. 下载 ANTLR（首次设置）：

   .. code-block:: bash

      make antlr

3. 使用根 Makefile 构建扩展：

   .. code-block:: bash

      make vscode

   此命令将：

   - 安装 npm 依赖
   - 复制 TextMate 语法文件
   - 从 ANTLR 语法生成 JavaScript 解析器
   - 使用 esbuild 打包扩展
   - 将扩展打包为 ``.vsix``

   构建的扩展将位于 ``editors/vscode/build/fcstm-language-support-0.1.0.vsix``

4. 安装生成的 ``.vsix`` 文件：

   .. code-block:: bash

      code --install-extension editors/vscode/build/fcstm-language-support-0.1.0.vsix

验证安装
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

安装后：

1. 在 VS Code 中打开一个 ``.fcstm`` 文件
2. 检查右下角的语言模式 - 应显示 "FCSTM"
3. 验证关键字、运算符和其他语法元素是否高亮显示
4. 打开大纲视图（``Ctrl+Shift+O`` 或 ``Cmd+Shift+O``）查看文档符号
5. 尝试输入 ``state`` 并验证代码补全是否出现
6. 将鼠标悬停在 ``pseudo`` 或 ``effect`` 等关键字上查看文档

扩展架构
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

扩展使用从规范 FCSTM 语法生成的纯 JavaScript ANTLR 解析器：

- **语法源**：``pyfcstm/dsl/grammar/Grammar.g4``\ （单一真实来源）
- **生成的产物**：``editors/vscode/parser/``\ （GrammarLexer.js、GrammarParser.js、GrammarVisitor.js）
- **解析器适配器**：``src/parser.ts``\ （加载生成的产物并规范化诊断）
- **运行时**：antlr4 版本 4.9.3（与生成工具链完全匹配）

扩展使用 esbuild 打包成单个 ``dist/extension.js`` 文件（246KB），包括：

- ANTLR 生成的解析器（~104KB）
- antlr4 运行时（~80KB）
- 扩展源代码（~20KB）

这种一体化打包确保：

- 无运行时依赖加载问题
- 更快的扩展激活
- 完全离线操作
- 无 Python 或外部运行时依赖

开发工作流
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

对于活跃开发：

.. code-block:: bash

   cd editors/vscode

   # 开发监视模式（带源映射）
   npm run watch

   # 或手动构建
   make build-dev

   # 在另一个终端中验证功能
   make verify

当 ANTLR 语法更改时：

1. 从项目根目录重新生成 Python 解析器：

   .. code-block:: bash

      make antlr_build

2. 验证 Python 测试通过：

   .. code-block:: bash

      make unittest

3. 为 VS Code 重新生成 JavaScript 解析器：

   .. code-block:: bash

      cd editors/vscode
      make parser

4. 重新构建并验证：

   .. code-block:: bash

      make build
      make verify

测试和验证
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

扩展包含全面的测试套件：

.. code-block:: bash

   cd editors/vscode

   # 验证 P0.2 - 解析器集成（32 个测试）
   make verify-p0.2

   # 验证 P0.3 - 语法诊断（35 个测试）
   make verify-p0.3

   # 验证 P0.4 - 文档符号（35 个测试）
   make verify-p0.4

   # 验证 P0.5 - 代码补全（30 个测试）
   make verify-p0.5

   # 验证 P0.6 - 悬停文档（35 个测试）
   make verify-p0.6

   # 运行所有验证测试
   make verify

所有测试使用真实的 FCSTM 代码，并提供详细的错误报告以便于调试。

支持的语法元素
---------------------------------------

Pygments 和 TextMate 实现都支持完整的 FCSTM 语法：

关键字
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**声明关键字：** ``state``、``pseudo``、``named``、``def``、``event``

**生命周期关键字：** ``enter``、``during``、``exit``、``before``、``after``

**动作关键字：** ``abstract``、``ref``、``effect``

**条件关键字：** ``if``、``and``、``or``、``not``

类型
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``int``、``float``

运算符
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**转换运算符：** ``->``、``>>``、``::``、``:``、``/``、``!``

**算术运算符：** ``+``、``-``、``*``、``/``、``%``、``**``

**位运算符：** ``&``、``|``、``^``、``~``、``<<``、``>>``

**比较运算符：** ``<``、``>``、``<=``、``>=``、``==``、``!=``

**逻辑运算符：** ``&&``、``||``、``!``

**三元运算符：** ``?``、``:``

字面量
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**整数：** ``123``、``0xFF``\ （十六进制）、``0b1010``\ （二进制）

**浮点数：** ``3.14``、``1e-5``、``2.5e10``

**布尔值：** ``True``、``False``

**字符串：** ``"text"``、``'text'``

**数学常量：** ``pi``、``E``、``tau``

内置函数
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**三角函数：** ``sin``、``cos``、``tan``、``asin``、``acos``、``atan``、``sinh``、``cosh``、``tanh``、``asinh``、``acosh``、``atanh``

**数学函数：** ``sqrt``、``cbrt``、``exp``、``log``、``log10``、``log2``、``log1p``、``abs``、``ceil``、``floor``、``round``、``trunc``、``sign``

特殊符号
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**伪状态：** ``[*]``

**注释：** ``//``\ （行注释）、``/* */``\ （块注释）、``#``\ （Python 风格注释）

完整示例
---------------------------------------

以下是演示所有语法元素的综合示例：

.. code-block:: fcstm

   // 带错误处理的交通灯控制器
   def int counter = 0;
   def int error_count = 0;
   def float temperature = 25.5;
   def int flags = 0xFF;

   state TrafficLight {
       // 用于监控的全局切面动作
       >> during before {
           counter = counter + 1;
           temperature = temperature + 0.1;
       }

       >> during before abstract GlobalMonitor /*
           监控所有状态的系统健康状况
           TODO: 实现硬件监控
       */

       state InService {
           enter {
               counter = 0;
               error_count = 0;
               flags = flags | 0x01;
           }

           enter abstract InitHardware /*
               初始化交通灯硬件
               - 设置 GPIO 引脚
               - 测试 LED 功能
               - 校准传感器
           */

           during before {
               // 所有子状态的预处理
               flags = flags & 0xFE;
           }

           state Red {
               during {
                   counter = (counter < 100) ? counter + 1 : 0;
                   flags = 0x1 << 2;
               }

               exit {
                   counter = 0;
               }
           }

           state Yellow {
               enter {
                   counter = 0;
               }
           }

           state Green {
               during {
                   // 使用位运算
                   flags = flags ^ 0x10;
               }
           }

           [*] -> Red :: Start effect {
               counter = 0;
               flags = 0x01;
           }

           Red -> Green : if [counter >= 10 && temperature < 50.0];
           Green -> Yellow :: Change effect {
               counter = 0;
           }
           Yellow -> Red : if [counter >= 3];
       }

       state Maintenance {
           enter {
               flags = 0xFF;
           }

           enter ref /GlobalCleanup;
       }

       state Error {
           enter {
               error_count = error_count + 1;
           }
       }

       // 用于紧急处理的强制转换
       !* -> Error :: CriticalError;
       !InService -> Maintenance :: Emergency;

       [*] -> InService;
       InService -> Maintenance :: Maintain;
       Maintenance -> InService : if [error_count == 0];
       Error -> [*] : if [error_count > 5];
   }

验证和测试
---------------------------------------

验证 Pygments 词法分析器
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

测试 Pygments 词法分析器安装：

.. code-block:: bash

   # 验证词法分析器已注册
   python -c "from pygments.lexers import get_lexer_by_name; print(get_lexer_by_name('fcstm'))"

   # 运行验证脚本
   cd editors
   python validate.py

验证脚本执行全面测试，包含 20 多个检查点，涵盖所有 ANTLR 语法规则。

故障排除
---------------------------------------

Pygments 在 Sphinx 中不工作
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # 验证 Pygments 已安装
   pip list | grep -i pygments

   # 如需要则重新安装
   pip install -r requirements.txt

   # 验证词法分析器注册
   python -c "from pygments.lexers import get_lexer_by_name; print(get_lexer_by_name('fcstm'))"

VS Code 扩展不工作
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. 检查扩展是否已安装：

   - 打开扩展视图（``Ctrl+Shift+X`` 或 ``Cmd+Shift+X``）
   - 搜索 "FCSTM" 或检查 ``~/.vscode/extensions/``

2. 验证文件扩展名是 ``.fcstm``
3. 检查 VS Code 的语言模式（右下角）- 应显示 "FCSTM"
4. 重新加载 VS Code 窗口（``Ctrl+Shift+P`` → "Reload Window"）
5. 检查输出面板（视图 → 输出）并选择 "FCSTM Language Support" 查看诊断消息

VS Code 语法诊断未显示
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. 确保文件已保存（诊断在保存时更新）
2. 检查问题面板（视图 → 问题 或 ``Ctrl+Shift+M``）
3. 验证扩展已激活（检查输出面板）
4. 尝试打开一个已知无效的 FCSTM 文件以测试错误检测

VS Code 代码补全不工作
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. 确保在 VS Code 设置中启用了 IntelliSense
2. 尝试手动触发补全（``Ctrl+Space``）
3. 检查您是否不在注释或字符串上下文中
4. 验证扩展已激活

TextMate 语法不工作
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. 验证语法文件在正确位置
2. 检查语法中的 ``scopeName`` 是否与您的配置匹配
3. 安装语法后重启编辑器

开发和自定义
---------------------------------------

添加新关键字
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

使用新关键字扩展 FCSTM 语法时：

1. 更新 ``pyfcstm/dsl/grammar/Grammar.g4``
2. 重新生成解析器：``make antlr_build``
3. 更新 ``pyfcstm/highlight/pygments_lexer.py``：

   .. code-block:: python

      # 添加到适当的 words() 组
      (words(('state', 'pseudo', 'named', 'your_new_keyword'), suffix=r'\b'), Keyword.Declaration),

4. 更新 ``editors/fcstm.tmLanguage.json``：

   .. code-block:: json

      {
        "name": "keyword.declaration.fcstm",
        "match": "\\b(state|pseudo|named|your_new_keyword)\\b"
      }

5. 运行验证：``python editors/validate.py``

自定义颜色
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**对于 Pygments（Sphinx）：**

在您的 Sphinx ``conf.py`` 中选择不同的 Pygments 样式：

.. code-block:: python

   pygments_style = 'monokai'  # 或 'github'、'vim'、'vs' 等

**对于 VS Code：**

颜色由您的 VS Code 主题控制。TextMate 语法分配作用域（例如 ``keyword.declaration.fcstm``），您的主题决定每个作用域的颜色。

要自定义，创建自定义主题或修改您的 ``settings.json``：

.. code-block:: json

   {
     "editor.tokenColorCustomizations": {
       "textMateRules": [
         {
           "scope": "keyword.declaration.fcstm",
           "settings": {
             "foreground": "#FF6B6B",
             "fontStyle": "bold"
           }
         }
       ]
     }
   }

相关资源
---------------------------------------

- **FCSTM DSL 参考：** 查看 DSL 教程了解完整的语言语法
- **VS Code 扩展：** 查看 ``editors/vscode/README.md`` 了解详细的扩展文档
- **Pygments 文档：** https://pygments.org/
- **TextMate 语法指南：** https://macromates.com/manual/en/language_grammars
- **VS Code 语言扩展：** https://code.visualstudio.com/api/language-extensions/syntax-highlight-guide
- **ANTLR 文档：** https://www.antlr.org/

文件位置
---------------------------------------

.. code-block:: text

   pyfcstm/
   ├── pyfcstm/
   │   └── highlight/
   │       ├── __init__.py              # 导出 FcstmLexer
   │       └── pygments_lexer.py        # Pygments 词法分析器实现
   ├── editors/
   │   ├── README.md                    # 详细实现说明
   │   ├── fcstm.tmLanguage.json        # TextMate 语法
   │   ├── validate.py                  # 验证脚本
   │   └── vscode/                      # VS Code 扩展
   │       ├── package.json             # 扩展清单
   │       ├── language-configuration.json  # 语言配置
   │       ├── README.md                # 扩展文档
   │       ├── src/                     # 扩展源代码
   │       │   ├── extension.ts         # 扩展入口点
   │       │   ├── parser.ts            # 解析器适配器
   │       │   ├── diagnostics.ts       # 语法诊断提供程序
   │       │   ├── symbols.ts           # 文档符号提供程序
   │       │   ├── completion.ts        # 代码补全提供程序
   │       │   └── hover.ts             # 悬停文档提供程序
   │       ├── parser/                  # 生成的 ANTLR 解析器
   │       │   ├── GrammarLexer.js      # 生成的词法分析器
   │       │   ├── GrammarParser.js     # 生成的解析器
   │       │   └── GrammarVisitor.js    # 生成的访问器
   │       ├── syntaxes/
   │       │   └── fcstm.tmLanguage.json    # TextMate 语法（副本）
   │       ├── snippets/
   │       │   └── fcstm.code-snippets  # 代码片段
   │       ├── scripts/                 # 验证脚本
   │       │   ├── verify-p0.2.js       # 解析器验证
   │       │   ├── verify-p0.3.js       # 诊断验证
   │       │   ├── verify-p0.4.js       # 符号验证
   │       │   ├── verify-p0.5.js       # 补全验证
   │       │   └── verify-p0.6.js       # 悬停验证
   │       ├── dist/                    # 打包的扩展
   │       │   └── extension.js         # 单个打包文件（246KB）
   │       └── build/                   # VSIX 包
   │           └── fcstm-language-support-0.1.0.vsix
   ├── docs/source/conf.py              # 带词法分析器注册的 Sphinx 配置
   └── setup.py                         # Pygments 入口点注册
