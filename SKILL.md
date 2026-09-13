---
name: research-knowledge-graph
description: 从科研文献自动构建领域知识图谱：实体抽取、关系识别、图谱构建、交互可视化与研究脉络分析。Use when the user mentions 知识图谱、knowledge graph、文献综述、实体抽取、关系识别、研究趋势、科研文献分析、literature review, or asks to build, visualize, or analyze a knowledge graph from papers. Do NOT use for generic graph drawing unrelated to scientific literature, dashboard charting, or non-scholarly network analysis.
license: MIT
compatibility: Requires Python 3.9+ and networkx; matplotlib and pyvis optional via viz extra; spaCy optional via nlp extra for higher recall.
metadata:
  author: XJH10247
  version: 1.0.0
  category: research
  tags: [knowledge-graph, nlp, scientific-literature, visualization, networkx]
---

# 科研知识图谱构建 Skill

从科研文献中自动构建领域知识图谱：实体抽取 → 关系识别 → 图谱构建 → 可视化 → 研究脉络分析。

面向用户的完整文档见 [README.md](README.md)；贡献约定见 [CONTRIBUTING.md](CONTRIBUTING.md)；
版本变更见 [CHANGELOG.md](CHANGELOG.md)。本文件聚焦 Skill 的能力边界、调用流程与 API 契约。

## 何时使用

| 用户意图 | 动作 |
|---|---|
| 「从这些论文摘要建知识图谱」 | 调用 `KnowledgeGraphPipeline.process_documents` |
| 「抽实体 / 识别方法与数据集」 | 调用 `EntityExtractor.extract_entities` 或 pipeline |
| 「实体之间有什么关系」 | 调用 `RelationExtractor.extract_relations` |
| 「画一张可交互的图谱」 | 调用 `pipeline.visualize(..., mode='interactive')` |
| 「领域研究趋势 / 空白」 | 调用 `TrajectoryAnalyzer` 对应方法 |
| 「导出 JSON / GraphML」 | 调用 `GraphBuilder.save_to_file` |

**不要用于**：与科研文献无关的通用画图、BI 仪表盘图表、非学术社交网络分析。

## 快速调用流程

1. 确认依赖：核心只需 `networkx`；可视化需 `matplotlib` + `pyvis`（extras `viz`）。
2. 导入统一入口并处理文本：

```python
from research_kg import KnowledgeGraphPipeline

pipeline = KnowledgeGraphPipeline(lazy_visualizer=True)
entities, relations, graph = pipeline.process_documents(documents)
```

3. 按需可视化（缺依赖时捕获 `ImportError`，不要因此中断抽取流程）：

```python
pipeline.visualize(graph, "knowledge_graph.html", mode="interactive")
pipeline.visualize(graph, "knowledge_graph.png", mode="static")
```

4. 按需分析：

```python
analysis = pipeline.analyze(graph, publications=publications)
# analysis: summary / trends / gaps / evolutions
```

5. 无显示环境设置 `MPLBACKEND=Agg`。spaCy 缺失时自动回退纯规则抽取。

## 技术架构

```
research-knowledge-graph/
├── research_kg/                     # 可导入的 Python 包
│   ├── __init__.py                  # KnowledgeGraphPipeline、__version__
│   └── modules/
│       ├── entity_extractor.py      # 实体抽取（12 类）
│       ├── relation_extractor.py    # 关系抽取（14 类已实现）
│       ├── graph_builder.py         # 图谱构建与查询
│       ├── visualizer.py            # 交互 / 静态 / 时间线可视化
│       └── trajectory_analyzer.py   # 趋势 / 空白 / 演进 / 影响力
├── references/api.md                # 详细 API 契约（渐进披露）
├── locales/                         # 桌面插件展示元数据
├── examples/demo.py                 # 完整使用示例
├── tests/                           # 单元测试
├── README.md                        # 面向用户的完整文档
└── SKILL.md                         # 本文件（Skill 入口）
```

| 层级 | 依赖 | 缺失时的影响 |
|------|------|-------------|
| 核心 | `networkx>=2.8` | 无法构建图谱 |
| 可视化 `viz` | `matplotlib`、`pyvis` | 仅无法出图，抽取与分析正常 |
| NLP `nlp` | `spacy` + 语言模型 | 回退纯规则抽取，召回率略降 |

设计特点：模块化、Pipeline 统一入口、优雅降级、可自定义实体 / 关系类型。

## 核心能力摘要

### 实体抽取 EntityExtractor

- 12 类实体：method、dataset、model、task、metric、material、tool、theory、measurement、software、author、institution
- 多策略：spaCy + 正则 + 关键词 + 缩略语 + 姓名 / 机构；中英文双语
- 置信度过滤、去重合并、批量处理、自定义类型

```python
from research_kg.modules.entity_extractor import EntityExtractor

extractor = EntityExtractor()  # model_name 默认 en_core_web_sm，可传 zh_core_web_sm
entities = extractor.extract_entities(text, entity_types=None, min_confidence=0.5)
batches = extractor.extract_from_documents(documents)
extractor.add_custom_entity_type("domain", {"machine learning"}, [r"\b(machine learning)\b"])
```

置信度常量（可覆写）：SPACY 0.80、NAME 0.75、AUTHOR 0.70、PATTERN 0.70、
ACRONYM 0.65、KEYWORD 0.60、REGEX 0.55、NOUN_PHRASE 0.50、ACRONYM_DEFAULT 0.45。

### 关系抽取 RelationExtractor

已实现 14 类：uses、compares、evaluates、extends、proposes、combines、replaces、
enables、improves、achieves、introduces、develops、trains、tests。

预留类型（无内置模式，需自行注册）：assigns、predicts、analyzes、optimizes。

```python
from research_kg.modules.relation_extractor import RelationExtractor

rel_extractor = RelationExtractor()
relations = rel_extractor.extract_relations(text, entities, min_confidence=0.5)
rel_extractor.add_custom_relation_type(
    "develops",
    [r"\b(\w+(?:\s+\w+)?)\s+develops?\s+(\w+(?:\s+\w+)?)"],
)
```

置信度：PATTERN 0.70、SYNTACTIC 0.65、DEPENDENCY 0.60、CONTEXT 0.55、AUTO_ENTITY 0.30。

### 图谱构建 GraphBuilder

```python
from research_kg.modules.graph_builder import GraphBuilder

builder = GraphBuilder()
graph = builder.build_graph(entities, relations)
stats = builder.get_graph_statistics()
report = builder.validate_graph()
top = builder.find_central_entities(top_k=10, method="degree")
sub = builder.filter_subgraph(entity_types=["model"], relation_types=["uses"])
builder.save_to_file("graph.json", "json")  # 亦支持 graphml / gexf
```

### 可视化 GraphVisualizer

```python
from research_kg.modules.visualizer import GraphVisualizer

viz = GraphVisualizer(figsize=(16, 12), dpi=150)
viz.visualize_interactive(graph, "knowledge_graph.html")  # 默认 cdn_resources="in_line"
viz.visualize_static(graph, "graph.png", title="Research Knowledge Graph", layout_type="spring")
viz.visualize_timeline(graph, publications, "timeline.html")
viz.visualize_entity_distribution(graph, "entity_distribution.png")
viz.visualize_relation_network(graph, entity_type="model", output_path="models.png")
viz.visualize_subgraph(graph, node_ids=[...], output_path="sub.png")
viz.visualize_graph_summary(graph, "graph_summary.png")
```

`cdn_resources`：`in_line`（默认，自包含可离线）、`remote`（CDN，体积小）、`local`（写 `lib/`，不推荐）。
未安装 matplotlib / pyvis 时，`research_kg` 与 `research_kg.modules` 对 GraphVisualizer 惰性加载。

### 研究脉络分析 TrajectoryAnalyzer

```python
from research_kg.modules.trajectory_analyzer import TrajectoryAnalyzer

analyzer = TrajectoryAnalyzer(graph)
analyzer.detect_trends(time_window=5, entity_types=["method", "model"], max_results=15)
analyzer.find_research_gaps(max_results=20, min_common_neighbors=1)
analyzer.analyze_evolution(publications, max_methods=20, max_results=10)
analyzer.analyze_temporal_evolution(publications)
analyzer.generate_research_summary()
analyzer.analyze_impact_strength(entity_id)
analyzer.identify_key_contributors(top_k=10)
```

`generate_research_summary()` 返回 `graph_statistics` / `key_findings` / `suggestions`；
图谱为空时返回 `status: empty`。

完整 API 签名、数据类字段、置信度表与配置细节见 [references/api.md](references/api.md)。

## Pipeline 方法

| 方法 | 说明 |
|---|---|
| `process_documents(documents, entity_types=None, min_confidence=0.5)` | 抽取 + 建图，返回 `(entities, relations, graph)` |
| `visualize(graph, output_path, mode='interactive')` | `interactive`（HTML）或 `static`（PNG） |
| `analyze(graph, publications=None)` | `summary` / `trends` / `gaps` / `evolutions` |
| `run_full_pipeline(documents, publications=None, output_dir='./output')` | 五阶段全流程 |
| `get_graph_validation(graph)` | 图谱结构校验 |
| `get_entity_relations(graph, entity_id)` | 单实体关联 |
| `analyze_impact(graph, entity_id)` | 影响力分析 |
| `identify_contributors(graph, top_k=10)` | 关键贡献实体排序 |

## 数据结构（摘要）

- `Entity`：entity_id、text、type、start_pos、end_pos、confidence、source_document、synonyms、attributes
- `Relation`：entity_id、source_entity_id、target_entity_id、relation_type、confidence、context、source_document、attributes
- `Trend`：name、growth_rate、current_momentum、key_entities、time_range、description
- `ResearchGap`：source_entity、target_entity、gap_type、potential、related_entities、description
- `EvolutionPath`：path、confidence、time_span、key_methods、summary
- `ImpactAnalysis`：entity_id、entity_text、impact_score、influence_sources、influenced_targets、total_connections、description

均实现 `to_dict()`；`Entity` / `Relation` 另有 `from_dict()`。

## 安装与验证

```bash
pip install -e ".[all]"          # 核心 + viz + nlp
pip install -e ".[nlp]"
python -m spacy download en_core_web_sm
python examples/demo.py
pytest -q
```

趋势 / 空白分析质量依赖图谱规模；玩具输入结果可能为空，属正常现象。

## 故障排查

| 现象 | 处理 |
|---|---|
| 无 spaCy | 自动回退规则抽取，功能可用 |
| matplotlib / pyvis 缺失 | 安装 `viz` extra；无显示设 `MPLBACKEND=Agg` |
| 中文 PNG 方块 | 安装中文字体，或手动设 `plt.rcParams['font.sans-serif']` |
| 抽取过多 / 过少 | 调整 `min_confidence`，或用 `entity_types` 过滤 |
| 时间线论文未连边 | `publications[i]['entities']` 须为图谱节点 ID 或实体文本 |
| 工作目录多出 `lib/` | 仅 `cdn_resources='local'` 时出现；默认 `in_line` 不会 |

## 许可

MIT License，© 2026 XJH10247。引用信息见 [CITATION.cff](CITATION.cff)。
