# python

`python` 是内置的 Python 原生运行时模板。

该模板会在目标目录中生成可直接使用的状态机运行时代码，以及面向当前状态机实例的使用说明文档。

模板源码内容：

- `machine.py.j2`：生成运行时模块
- `README.md.j2`：在目标目录中生成英文使用说明
- `README_zh.md.j2`：在目标目录中生成中文使用说明
- `README.md` / `README_zh.md`：模板维护者阅读的模板说明

当前特性：

- 已完成首版运行时模板实现
- 生成单文件可导入 Python 状态机模块
- 默认输出 `machine.py`、`README.md`、`README_zh.md`
- 内置状态元数据、cycle 逻辑、hot start、abstract hook 扩展点与抽象处理器注册
- 仅依赖 Python 标准库
- 生成代码默认风格尽量贴近 `ruff format`
- abstract hook 的命名有利于 DSL 用户借助 IDE 补全快速定位
