# Python 可视化运行时资源

本目录是 Python 侧离线可视化运行时使用的资源包。`pyfcstm.diagram` 会在
MiniRacer 中加载这里的 JavaScript、WASM 和字体资源，完成 ELK 布局、SVG
生成以及 PNG/矢量 SVG 处理。资源随 Python 包发布，用户不需要另外安装
Node.js、浏览器或系统字体。

## 维护纪律

- 生成资源只能通过仓库根目录的 `make build_assets` 更新，不能手工修改或从
  其他构建产物复制。
- 资源来源、构建入口和锁定版本由 `tools/diagram_assets/` 管理；修改来源或
  构建逻辑后必须重新构建并运行 `make diagram_assets_check`。
- 生成文件由 `.gitignore` 忽略。提交前应确认资产校验、Python 定向测试以及
  wheel/sdist 打包检查都通过。
- `README.md`、`__init__.py`、`.gitignore`、公告和许可证文件是目录的受控
  元数据，不应被构建脚本删除。
- 不要在这里新增临时文件、缓存、额外字体或未登记的运行时依赖；校验器会
  将未登记文件视为错误。

## 预期文件清单

受控元数据：

- `README.md`
- `__init__.py`
- `.gitignore`
- `NOTICE.txt`
- `LICENSE-MPL-2.0.txt`
- `LICENSE-EPL-2.0.txt`
- `LICENSE-OFL-1.1.txt`

构建生成资源：

- `renderer.js`：ELK、SVG 绘制和渲染入口的合并脚本
- `resvg-binding.js`：resvg WASM 的 JavaScript 绑定
- `resvg-bridge.js`：面向 MiniRacer 的受限资源桥接层
- `host-shim.js`：MiniRacer 所需的最小宿主环境补丁
- `resvg.wasm`：固定版本的 resvg WASM 后端
- `manifest.json`：构建器使用的资源清单和校验信息
- `fonts/JetBrainsMono-Regular.ttf`：离线文本渲染使用的默认字体
