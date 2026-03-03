FCSTM 语法高亮指南
===============================================

pyfcstm 通过多种实现方式为 FCSTM DSL 代码提供原生语法高亮支持，使您能够在文档、编辑器和开发工具中展示格式优美的状态机代码。

概述
---------------------------------------

两种互补的实现方式提供全面的语法高亮支持：

1. **Pygments 词法分析器** - 用于 Python 生态系统工具（Sphinx、Jupyter 等）
2. **TextMate 语法** - 用于支持 TextMate 语法的编辑器和平台（VS Code、GitHub、GitLab 等）

两种实现都基于 ANTLR 语法，支持完整的 FCSTM 语法，包括关键字、运算符、字面量、注释和内置函数。

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

TextMate 语法为支持 TextMate 语法的编辑器和平台提供语法高亮，包括 VS Code、Sublime Text、Atom、GitHub 和 GitLab。

位置
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TextMate 语法文件位于：

.. code-block:: text

   editors/fcstm.tmLanguage.json

VS Code 集成
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**方法 1：创建 VS Code 扩展（推荐）**

1. 为您的扩展创建新目录：

   .. code-block:: bash

      mkdir fcstm-vscode
      cd fcstm-vscode

2. 创建 ``package.json``：

   .. code-block:: json

      {
        "name": "fcstm-language-support",
        "displayName": "FCSTM Language Support",
        "description": "Syntax highlighting for FCSTM state machine DSL",
        "version": "1.0.0",
        "engines": {
          "vscode": "^1.60.0"
        },
        "categories": ["Programming Languages"],
        "contributes": {
          "languages": [{
            "id": "fcstm",
            "aliases": ["FCSTM", "fcstm"],
            "extensions": [".fcstm", ".fcsm"],
            "configuration": "./language-configuration.json"
          }],
          "grammars": [{
            "language": "fcstm",
            "scopeName": "source.fcstm",
            "path": "./syntaxes/fcstm.tmLanguage.json"
          }]
        }
      }

3. 创建 ``language-configuration.json``：

   .. code-block:: json

      {
        "comments": {
          "lineComment": "//",
          "blockComment": ["/*", "*/"]
        },
        "brackets": [
          ["{", "}"],
          ["[", "]"],
          ["(", ")"]
        ],
        "autoClosingPairs": [
          { "open": "{", "close": "}" },
          { "open": "[", "close": "]" },
          { "open": "(", "close": ")" },
          { "open": "\"", "close": "\"" },
          { "open": "'", "close": "'" }
        ],
        "surroundingPairs": [
          ["{", "}"],
          ["[", "]"],
          ["(", ")"],
          ["\"", "\""],
          ["'", "'"]
        ]
      }

4. 创建 syntaxes 目录并复制语法文件：

   .. code-block:: bash

      mkdir syntaxes
      cp /path/to/pyfcstm/editors/fcstm.tmLanguage.json syntaxes/

5. 安装扩展：

   .. code-block:: bash

      # 复制到 VS Code 扩展目录
      cp -r . ~/.vscode/extensions/fcstm-language-support-1.0.0/

      # 或使用 vsce 打包并安装
      npm install -g vsce
      vsce package
      code --install-extension fcstm-language-support-1.0.0.vsix

6. 重启 VS Code。现在 ``.fcstm`` 或 ``.fcsm`` 扩展名的文件将具有语法高亮。

**方法 2：手动配置**

用于快速测试而无需创建扩展：

1. 打开 VS Code 设置（``Ctrl+,`` 或 ``Cmd+,``）
2. 搜索 "files.associations"
3. 将以下内容添加到您的 ``settings.json``：

   .. code-block:: json

      {
        "files.associations": {
          "*.fcstm": "fcstm",
          "*.fcsm": "fcstm"
        }
      }

注意：此方法需要安装方法 1 中的扩展才能使语法生效。

Sublime Text 集成
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. 打开 Sublime Text
2. 导航到 ``Preferences → Browse Packages``
3. 创建新目录：``FCSTM``
4. 将 ``fcstm.tmLanguage.json`` 复制到此目录
5. 重启 Sublime Text
6. 现在 ``.fcstm`` 扩展名的文件将具有语法高亮

GitHub 和 GitLab
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

GitHub 和 GitLab 自动识别 TextMate 语法以在仓库中实现语法高亮。

**对于仓库所有者：**

1. 将语法文件添加到您的仓库：

   .. code-block:: bash

      mkdir -p .github/linguist
      cp editors/fcstm.tmLanguage.json .github/linguist/

2. 创建 ``.gitattributes`` 以关联文件扩展名：

   .. code-block:: text

      *.fcstm linguist-language=FCSTM
      *.fcsm linguist-language=FCSTM

3. 提交并推送。GitHub 现在将对您仓库中的 ``.fcstm`` 文件进行语法高亮。

**注意：** 完整的 GitHub Linguist 集成需要将语法提交到 Linguist 项目。上述方法适用于单个仓库。

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

**整数：** ``123``、``0xFF``（十六进制）、``0b1010``（二进制）

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

**注释：** ``//``（行注释）、``/* */``（块注释）、``#``（Python 风格注释）

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

VS Code 不高亮
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. 检查扩展是否安装在 ``~/.vscode/extensions/`` 中
2. 验证文件扩展名是 ``.fcstm`` 或 ``.fcsm``
3. 重启 VS Code
4. 检查 VS Code 的语言模式（右下角）- 应显示 "FCSTM"

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
- **Pygments 文档：** https://pygments.org/
- **TextMate 语法指南：** https://macromates.com/manual/en/language_grammars
- **VS Code 语言扩展：** https://code.visualstudio.com/api/language-extensions/syntax-highlight-guide
- **GitHub Linguist：** https://github.com/github/linguist

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
   │   └── validate.py                  # 验证脚本
   ├── docs/source/conf.py              # 带词法分析器注册的 Sphinx 配置
   └── setup.py                         # Pygments 入口点注册
