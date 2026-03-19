# c

`c` 是内置的 C99 原生运行时模板。

该模板会在目标目录中生成可直接使用的 C 运行时代码，以及面向当前状态机实例的使用说明文档。

模板源码内容：

- `machine.h.j2`：生成公开运行时头文件
- `machine.c.j2`：生成运行时实现
- `README.md.j2`：在目标目录中生成英文使用说明
- `README_zh.md.j2`：在目标目录中生成中文使用说明
- `README.md` / `README_zh.md`：模板维护者阅读的模板说明

当前特性：

- 目标语言为 C99，仅依赖常见标准库设施
- 默认输出 `machine.h`、`machine.c`、`README.md`、`README_zh.md`
- 内置状态元数据、cycle 逻辑、hot start 和 abstract hook 回调扩展点
- abstract hook 的扩展方式更贴近 C 开发者的回调表使用习惯
- 不生成额外的 handler 注册体系
