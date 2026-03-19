# 内置模板源码目录

这里存放 `pyfcstm` 仓库维护的内置模板源码。

约定：

- `templates/` 下每一个一级子目录都表示一个内置模板源码目录。
- 每个模板子目录都应包含自己的 `README.md`。
- 打包后的内置模板会被输出到 `pyfcstm/template/`，以 zip 资源形式随包分发。

当前模板源码：

- `python_native`：用于打通内置模板链路的 Python 原生模板脚手架
