# 更新日志

本项目的所有重要变更都会记录在此文件中。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 新增

- `locales/zh-CN.json` 与 `locales/en-US.json`：MiMo Desktop 插件页展示名与简介。
- `references/api.md`：从 `SKILL.md` 拆出的完整 API 契约，支持渐进披露。
- `SECURITY.md`：私密漏洞报告渠道与安全边界说明。
- `CODE_OF_CONDUCT.md`：Contributor Covenant 2.1 行为准则。

### 变更

- `SKILL.md` frontmatter 重写：去掉 YAML 块标量中的尖括号，补充英文
  `Use when` / `Do NOT use for` 触发条件、`license`、`compatibility` 与 `metadata`。
- `SKILL.md` 正文精简为 Agent 调用流程与能力摘要，详细签名与常量表移至
  `references/api.md`。
- `README.md` 新增「作为 AI Skill 使用」安装说明（通用 Agent skills 目录约定，
  含 Claude Code / MiMoCode 等示例路径）；目录树同步 `locales/`、
  `references/`、`SECURITY.md`、`CODE_OF_CONDUCT.md`。
- `CONTRIBUTING.md` 补充 Skill 目录约定，并链接行为准则与安全政策。

### 修复

- **修复 Windows CI 上交互/时间线 HTML 写出失败**：`pyvis` 的 `write_html` 在
  默认编码为 cp1252 的 Windows runner 上会因内联 vis-network 中的字符触发
  `UnicodeEncodeError: 'charmap' codec can't encode characters`。抽出
  `research_kg.modules.html_io.write_pyvis_html`，经 `generate_html` 后以显式
  `encoding='utf-8'` 落盘；CI 测试步骤同时设置 `PYTHONUTF8=1`。
- `tests/TestPipeline.test_visualize_static` 在未安装 matplotlib / pyvis 时改为
  `pytest.importorskip` 跳过，与其余可视化用例及项目「优雅降级」约定一致，
  避免在仅装核心依赖的环境中误报失败。
- 新增 `TestWritePyvisHtmlUtf8` 回归用例，锁定非平台默认编码写盘行为。

## [1.0.0] - 2026-09-13

首个公开发布版本。

### 新增

- **实体抽取（`EntityExtractor`）**：12 类科学实体（method / dataset / model / task / metric /
  material / tool / theory / measurement / software / author / institution），
  融合 spaCy 模型、正则模式、关键词、缩略语、姓名与机构识别等多策略抽取，带置信度评分与去重合并。
- **关系抽取（`RelationExtractor`）**：14 类语义关系（uses / compares / evaluates / extends /
  proposes / combines / replaces / enables / improves / achieves / introduces / develops /
  trains / tests），基于模式匹配与依存句法分析，支持自定义关系模式。
- **图谱构建（`GraphBuilder`）**：基于 NetworkX DiGraph，支持 JSON / GraphML / GEXF 导入导出、
  子图筛选、图谱合并、中心性分析、邻居查询与结构校验。
- **可视化（`GraphVisualizer`）**：PyVis 交互图谱、Matplotlib 静态图谱、时间线图谱、
  实体分布图、关系网络图、子图聚焦与图谱摘要。
- **研究脉络分析（`TrajectoryAnalyzer`）**：研究演进路径、趋势检测、研究空白发现、
  研究摘要、时间演化与影响力分析。
- **统一入口（`KnowledgeGraphPipeline`）**：一键完成抽取 → 构建 → 可视化 → 分析全流程。
- 中英文双语支持，spaCy 模型缺失时自动回退到纯规则抽取。
- 完整的单元测试（27 个用例，覆盖五大模块、Pipeline 与可视化回归场景）。

### 变更

- 包目录由 `src/` 重命名为 `research_kg/`（在首次公开发布前调整）。导入路径相应变更为：

  ```python
  from research_kg import KnowledgeGraphPipeline   # 新
  from src import KnowledgeGraphPipeline           # 旧，已废弃
  ```

- `demo_output/` 中的示例产物移至 `docs/images/`（静态图）与 `docs/demo/`（交互式 HTML），
  文件名统一为 kebab-case；`ppt/KG_Skill_Intro_CN.pptx` 移至 `docs/`。
- 依赖清单按「实际 import」校准：移除项目从未导入的 `pandas`、`python-pptx`、`click`、
  `tqdm`、`numpy`；补上实际被导入却遗漏的 `spacy`（列为可选依赖）。
- 依赖按能力拆分为 `viz` / `nlp` / `dev` / `all` 四组 extras。
- `KnowledgeGraphPipeline.visualize` 的 `mode` 语义保持不变，仍为 `'interactive'` / `'static'`。

### 修复

- **修复 `visualize_timeline` 崩溃**：当 `publications[i]['entities']` 引用的实体不在图谱中时，
  原实现仍会调用 `net.add_edge()`，触发 PyVis 的 `assert to in self.get_nodes()` 而中断。
  现在会先解析实体引用（支持节点 ID 与实体文本两种写法），解析不到的引用跳过并记录日志。
- **修复 `examples/demo.py` 单独调用即崩溃**：只有 `__main__` 分支创建了 `output/` 目录，
  直接调用 `run_basic_demo()` 会因为 PyVis 不自动创建父目录而抛 `FileNotFoundError`。
  现由 `_output_dir()` 统一确保目录存在。
- **修复交互式 HTML 无法独立分发**：PyVis 默认 `cdn_resources='local'`，会把 vis-network
  资源复制到当前工作目录的 `lib/`，且生成的 HTML 使用相对引用——文件一旦移动或被单独分发，
  引用即失效。`visualize_interactive` 与 `visualize_timeline` 现默认 `cdn_resources='in_line'`，
  产物自包含、可离线打开，也不再污染工作目录。需要小体积可显式传 `'remote'`。
- 补上缺失的 `research_kg/modules/__init__.py`，避免依赖隐式命名空间包。
- 修正 `SKILL.md` 中陈旧的目录树、错乱的代码块缩进，以及 API 清单与实现不一致之处
  （关系类型数量、`visualize_static` 的 `layout_type` 参数、遗漏的
  `visualize_subgraph` / `visualize_graph_summary` / `get_entity_relations` /
  `build_relation_vocabulary` 等）。
- 标注 `RelationType` 中 `assigns` / `predicts` / `analyzes` / `optimizes` 四者为**预留类型**，
  此前它们在图例与文档中被当作已实现能力，实际没有对应的抽取模式。
- 全量通过 `ruff check`（`E` / `F` / `W` / `I` / `UP` / `B`）：清理未使用的导入与局部变量、
  统一导入排序、将 `typing.List` 等替换为 PEP 585 内置泛型（Python 3.9+ 运行时合法）、
  修正 `B904` 异常链与 `B007` 未使用循环变量。
- 移除硬编码的 `matplotlib.use('Agg')` 位置歧义，明确其必须在导入 `pyplot` 之前执行，
  以保证无显示环境下可用。
- 移除测试文件中未使用的 `pytest` 导入，并新增 `TestVisualizer` 回归测试（3 个用例），
  分别锁定上述 timeline 崩溃、`lib/` 污染与实体文本解析行为。

[Unreleased]: https://github.com/XJH10247/research-knowledge-graph/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/XJH10247/research-knowledge-graph/releases/tag/v1.0.0
