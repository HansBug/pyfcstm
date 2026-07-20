# Python Diagram 运行资产

此目录保存 Python 侧离线图形渲染运行时需要的资源。`pyfcstm.diagram`
会在受限的 MiniRacer 环境中加载 JavaScript 渲染器、resvg WebAssembly
模块以及内置字体，从而在不依赖 Node.js、浏览器或系统字体的情况下生成
ELK 布局、SVG、PNG 和展开后的矢量 SVG。

## 维护纪律

- 只能在仓库根目录执行 `make build_assets` 生成资源；禁止手工编辑生成文件，
  也不要从其他构建目录复制资源。
- 官方 `@resvg/resvg-wasm@2.6.2` 由锁定的
  `editors/jsfcstm/package-lock.json` 恢复。来源、提交、许可证、大小限制和
  校验信息以 `tools/diagram_assets/asset-lock.json` 为准。
- 修改来源或构建规则后，依次运行 `make build_assets`、
  `make diagram_assets_check`，再使用冻结的 custom 0.37 reference bundle
  运行 `make DIAGRAM_REFERENCE=/abs/path/reference.json diagram_assets_verify`。
  reference 缺失时门禁必须失败，不能跳过 parity。
- 生成文件由本目录的 `.gitignore` 忽略。`README.md`、`__init__.py`、
  `.gitignore`、`NOTICE.txt` 以及许可证文件属于受控元数据，构建器不会删除。
- 不要添加临时文件、缓存、未登记字体或额外运行时依赖；资产检查器会拒绝
  未登记文件。

## 预期文件清单

### 源码树中的受控元数据

- `README.md`：本目录用途、维护规则和文件清单。
- `__init__.py`：Python 包标记。
- `.gitignore`：生成资源边界标记；不会进入 wheel 或源码包。
- `NOTICE.txt`：第三方来源和许可证说明。
- `LICENSE-MPL-2.0.txt`、`LICENSE-EPL-2.0.txt`、`LICENSE-OFL-1.1.txt`：
  随包分发的许可证正文。

### Python 包中分发的生成资源

- `renderer.js`：目标为 ES2017 的 IIFE，包含 ELK、SVG 绘制和 Python 入口。
- `resvg-binding.js`：官方 `@resvg/resvg-wasm` 2.6.2 binding。
- `resvg-bridge.js`：受限 MiniRacer bridge 和字体注册入口。
- `host-shim.js`：MiniRacer 所需的最小宿主环境补丁。
- `resvg.wasm`：锁定的 resvg WebAssembly 后端。
- `manifest.json`：生成文件路径、字节数、摘要和来源元数据。
- `fonts/JetBrainsMono-Regular.ttf`、`fonts/JetBrainsMono-Medium.ttf`、
  `fonts/JetBrainsMono-Bold.ttf`：拉丁字符常规、中等和粗体。
- `fonts/NotoSansSC-Regular.otf`、`fonts/NotoSansSC-Bold.otf`：简体中文。
- `fonts/NotoSansTC-Regular.otf`、`fonts/NotoSansTC-Bold.otf`：繁体中文。
- `fonts/NotoSansHK-Regular.otf`、`fonts/NotoSansHK-Bold.otf`：香港中文。
- `fonts/NotoSansJP-Regular.otf`、`fonts/NotoSansJP-Bold.otf`：日文。
- `fonts/NotoSansKR-Regular.otf`、`fonts/NotoSansKR-Bold.otf`：韩文。

CJK 字体按地区拆分为独立 OTF，而不是一个多字体 TTC。运行时只注册 SVG
选择的地区字体，以限制 MiniRacer 内存占用并保持确定的字形覆盖。

resvg binding 和 WASM 按 MPL 2.0 分发；所有字体按 SIL Open Font License
1.1 分发。确切的 npm 包、来源提交、源码归档、许可证和大小限制均以
`tools/diagram_assets/asset-lock.json` 为权威记录。

维护用的箭头语料和回放工具位于 `tools/diagram_assets/`，不属于运行资源目录：

- `corpus/canonical-arrows.json`：15 个真实视觉 fixture、130 条转换箭头。
- `corpus/shared-layouts.json`：20 个 LR/TB 布局、176 条渲染箭头。
- `tools/check_diagram_rendering.py`：端点、PNG/expanded SVG、CJK、parity 和内存维护门禁。
- `tools/check_diagram_engine_floor.py`：按 Python 版本选择 MiniRacer 的 smoke 门禁。
- `tools/check_diagram_provenance.py`：npm 和源码归档来源回读门禁。
- `tools/fetch_diagram_reference.py`：按 `reference-lock.json` 恢复并校验 CI 用的
  custom reference bundle；`python tools/fetch_diagram_reference.py --check`
  在无网络条件下验证有界重试和永久 HTTP 错误行为。
- `tools/diagram_assets/reference-lock.json`：每个 Python major.minor 对应的
  Gist archive URL、编码方式和 tarball SHA-256。

PNG 和展开 SVG 入口只接受 DiagramData 请求，或由共享渲染器返回的内部
canonical 对象；任意 raw SVG 文本都会被拒绝。

reference bundle 必须在 source swap 前由 custom resvg 0.37 资产生成，并带有
`reference.json`、sidecar、`SHA256SUMS` 和 `custom-resvg-0.37` provenance；
禁止在 official backend 上重新 capture 后冒充 custom baseline。
