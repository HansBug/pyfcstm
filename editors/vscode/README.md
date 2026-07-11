# FCSTM VS Code 扩展验收版

本 VSIX 用于项目验收分支交付；不是 pyfcstm 的通用发行渠道，也不作为正式发布版本。

## 离线安装

```bash
code --install-extension fcstm-language-support-0.1.0.vsix --force
code --list-extensions --show-versions | grep '^hansbug.fcstm-language-support@0.1.0$'
```

建议验收时使用临时 `--user-data-dir` 和 `--extensions-dir`，避免污染个人 VS Code 配置。

## 已打包能力

- 自动识别 `.fcstm` 文件并启用 FCSTM 语法高亮。
- 提供语法与结构诊断，并在 Problems 面板显示源码位置。
- 提供补全、悬停说明、定义跳转、引用/高亮、文档符号、格式化和可用修复建议。
- 提供 FCSTM Preview 命令：
  - `FCSTM: Open Preview to the Side`
  - `FCSTM: Open Preview (Diagram Only)`
  - `FCSTM: Toggle Preview Layout`
- Preview 可以展示层次状态图，并支持导出 SVG、PNG 和 PDF。

## 使用步骤

1. 安装 VSIX。
2. 打开 `.fcstm` 文件。
3. 查看 Problems、Outline、补全、悬停和跳转结果。
4. 通过编辑器标题栏或命令面板打开 FCSTM Preview。
5. 在 Preview 中检查图形并按需导出图片或报告文件。

## 离线边界

扩展运行时 bundle、语言服务、语法文件、片段、图标和预览资源均包含在 VSIX 内。安装后不需要访问本仓库源码或在线服务。Python 包、命令行程序和验收 PDF 是独立交付物，不包含在此 VSIX 中。

## 已知限制

此扩展只提供编辑器集成与预览能力；Python 代码生成、命令行仿真和安装包验收由其他交付物覆盖。

## 卸载

```bash
code --uninstall-extension hansbug.fcstm-language-support
```
