# API 参考

本文件是 `research_kg` 的详细 API 契约，供需要精确签名与常量表时查阅。
快速上手与调用流程见 [SKILL.md](../SKILL.md)。

## 1. 实体抽取 EntityExtractor

```python
class EntityExtractor:
    def __init__(model_name: str = "en_core_web_sm"): ...

    def extract_entities(text, entity_types=None, min_confidence=0.5) -> List[Entity]: ...
    def extract_from_documents(documents, entity_types=None, min_confidence=0.5) -> List[List[Entity]]: ...
    def get_entity_statistics(entities) -> Dict: ...
    def build_entity_vocabulary(entities) -> Dict[str, List[str]]: ...
    def add_custom_entity_type(entity_type, keywords, patterns=None) -> None: ...
```

支持的实体类型（`EntityType` 枚举，12 种）：

| 类型 | 含义 |
|---|---|
| method | 算法、技术、流程 |
| dataset | 语料库、基准数据集 |
| model | 网络架构、模型框架 |
| task | 研究问题、挑战、应用场景 |
| metric | 评价指标、性能度量 |
| material | 实验材料、样本 |
| tool | 软件工具、平台、库 |
| theory | 理论、假说、原理 |
| measurement | 测量方法、参数 |
| software | 专用软件、平台 |
| author | 研究者姓名 |
| institution | 研究机构、大学 |

### 置信度常量（类属性，可覆写）

| 常量 | 值 | 说明 |
|------|-----|------|
| `CONFIDENCE_SPACY` | 0.80 | spaCy 模型识别 |
| `CONFIDENCE_NAME` | 0.75 | 姓名模式（需命中 model / method 等词） |
| `CONFIDENCE_AUTHOR` | 0.70 | 作者引用格式，形如 `Devlin, J.` |
| `CONFIDENCE_PATTERN` | 0.70 | 正则模式 |
| `CONFIDENCE_ACRONYM` | 0.65 | 缩略语（有上下文线索） |
| `CONFIDENCE_KEYWORD` | 0.60 | 关键词匹配 |
| `CONFIDENCE_REGEX` | 0.55 | 自定义类型 |
| `CONFIDENCE_NOUN_PHRASE` | 0.50 | 名词短语 |
| `CONFIDENCE_ACRONYM_DEFAULT` | 0.45 | 缩略语（无上下文） |

核心能力：

- 多策略融合抽取；中英文双语（中文按字符子串匹配，规避词边界问题）
- 置信度评分与 `min_confidence` 过滤
- 批量处理时自动回填 `source_document`
- 按「文本小写 + 类型」去重，保留最高置信度
- 运行时可注册自定义实体类型与模式

## 2. 关系抽取 RelationExtractor

```python
class RelationExtractor:
    def __init__(model_name: str = "en_core_web_sm"): ...

    def extract_relations(text, entities, min_confidence=0.5) -> List[Relation]: ...
    def extract_from_documents(documents, entities_list) -> List[List[Relation]]: ...
    def get_relation_statistics(relations) -> Dict: ...
    def build_relation_vocabulary(relations) -> Dict[str, List[Tuple[str, str]]]: ...
    def add_custom_relation_type(relation_type, patterns) -> None: ...
```

### 已实现抽取模式的关系类型（14 种）

| 关系类型 | 含义 | 关系类型 | 含义 |
|---|---|---|---|
| uses | A 使用了 B | improves | A 改进了 B |
| compares | A 与 B 比较 | achieves | A 达到了某性能 |
| evaluates | A 在 B 上评估 | introduces | A 引入了 B |
| extends | A 扩展了 B | develops | A 开发了 B |
| proposes | A 提出了 B | trains | A 训练了 B |
| combines | A 结合了 B | tests | A 测试了 B |
| replaces | A 替代了 B | enables | A 使 B 成为可能 |

`RelationType` 另含预留类型：`assigns`、`predicts`、`analyzes`、`optimizes`（无内置模式，
需通过 `add_custom_relation_type()` 注册）。

### 置信度常量

| 常量 | 值 | 说明 |
|------|-----|------|
| `CONFIDENCE_PATTERN` | 0.70 | 正则模式匹配 |
| `CONFIDENCE_SYNTACTIC` | 0.65 | 语法结构启发式 |
| `CONFIDENCE_DEPENDENCY` | 0.60 | 依存句法分析 |
| `CONFIDENCE_CONTEXT` | 0.55 | 上下文推断 |
| `CONFIDENCE_AUTO_ENTITY` | 0.30 | 自动补全的实体 |

自定义关系模式需包含两个捕获组：第 1 组源实体、第 2 组目标实体。

## 3. 图谱构建 GraphBuilder

```python
class GraphBuilder:
    def build_graph(entities, relations) -> nx.DiGraph: ...
    def add_nodes(entities) -> nx.DiGraph: ...
    def add_edges(relations) -> nx.DiGraph: ...
    def export_graph(file_format='json') -> Any: ...
    def save_to_file(filepath, file_format='json') -> str: ...
    def load_from_file(filepath, file_format='json') -> nx.DiGraph: ...
    def get_graph_statistics() -> Dict: ...
    def validate_graph() -> Dict: ...
    def filter_subgraph(entity_ids=None, entity_types=None, relation_types=None) -> nx.DiGraph: ...
    def merge_graphs(other_graph) -> nx.DiGraph: ...
    def find_central_entities(top_k=10, method='degree') -> List[Dict]: ...
    def find_entity_neighbors(entity_id, depth=1) -> Dict: ...
    def get_entity_relations(entity_id) -> Dict: ...
```

要点：

- 基于 NetworkX `DiGraph`；节点 / 边均带完整属性
- 导出格式：JSON、GraphML、GEXF
- 中心性：degree / betweenness / pagerank
- `validate_graph()` 返回 `valid` / `errors` / `warnings`
- 空图时 `get_graph_statistics()` 返回 `status: empty`

## 4. 可视化 GraphVisualizer

```python
class GraphVisualizer:
    def __init__(figsize=(16, 12), dpi=150): ...

    def visualize_interactive(graph, output_path='knowledge_graph.html',
                              cdn_resources='in_line'): ...
    def visualize_static(graph, output_path='knowledge_graph.png',
                         title='Research Knowledge Graph', layout_type='spring'): ...
    def visualize_timeline(graph, publications, output_path='timeline.html',
                           cdn_resources='in_line'): ...
    def visualize_entity_distribution(graph, output_path='entity_distribution.png'): ...
    def visualize_relation_network(graph, entity_type=None, output_path='relation_network.png'): ...
    def visualize_subgraph(graph, node_ids, output_path='subgraph.png',
                           title='Subgraph Visualization'): ...
    def visualize_graph_summary(graph, output_path='graph_summary.png'): ...

    def set_custom_colors(entity_colors=None, relation_colors=None) -> None: ...
    def set_custom_layout(layout_type='spring') -> None: ...
```

所有 `visualize_*` 返回写入的 `output_path`。

### cdn_resources

| 取值 | 表现 | 适用场景 |
|---|---|---|
| `in_line`（默认） | JS/CSS 内联，约 700 KB | 离线打开、归档、随论文附件分发 |
| `remote` | 引用 CDN，文件最小 | 读者有网络且在意体积 |
| `local` | 复制资源到工作目录 `lib/` | 需离线且不想增大 HTML；移动后相对引用失效，不建议 |

### 其他说明

- 实体类型 12 类各有默认配色；未知类型回退灰色
- 关系类型 14 类各有默认颜色与线型
- 节点大小映射重要度；边宽映射关系置信度
- 中文字体回退链覆盖 Windows / macOS / Linux 常见字体
- 布局算法：spring / circular / shell / kamada_kawai
- 本模块 import 时需要 matplotlib / pyvis；顶层与 `research_kg.modules` 对其惰性加载
- 无显示环境设置 `MPLBACKEND=Agg`

## 5. 研究脉络分析 TrajectoryAnalyzer

```python
class TrajectoryAnalyzer:
    def __init__(graph=None): ...

    def analyze_evolution(publications, max_methods=20, max_results=10) -> List[EvolutionPath]: ...
    def detect_trends(time_window=5, entity_types=None, max_results=15) -> List[Trend]: ...
    def find_research_gaps(max_results=20, min_common_neighbors=1) -> List[ResearchGap]: ...
    def generate_research_summary() -> Dict: ...
    def analyze_temporal_evolution(publications) -> Dict: ...
    def analyze_impact_strength(entity_id) -> Dict: ...
    def identify_key_contributors(top_k=10) -> List[Dict]: ...
```

默认分析范围：

- `DEFAULT_TREND_ENTITY_TYPES = ['method', 'model', 'task']`
- `DEFAULT_GAP_ENTITY_TYPES = ['method', 'model', 'dataset', 'task']`

### generate_research_summary() 返回结构

```python
{
    'graph_statistics': {
        'total_entities', 'total_relations', 'entity_types', 'relation_types',
        'density', 'connected_components', 'avg_clustering_coefficient'
    },
    'key_findings': {'central_entities': [...], 'entity_type_distribution': {...}},
    'suggestions': [str, ...]
}
```

图谱为空时返回 `{'status': 'empty', 'message': ...}`；
实体不存在时返回 `{'status': 'error', ...}`。

## 6. 数据类完整定义

```python
@dataclass
class Entity:
    entity_id: str           # 实体唯一标识（uuid4）
    text: str                # 实体文本
    type: str                # 实体类型
    start_pos: int           # 在原文中的起始位置
    end_pos: int             # 在原文中的结束位置
    confidence: float        # 抽取置信度
    source_document: str     # 来源文档标识（如 doc_0）
    synonyms: List[str]      # 同义词列表
    attributes: Dict         # 扩展属性（含 'source' 标注抽取来源）

@dataclass
class Relation:
    entity_id: str           # 关系唯一标识
    source_entity_id: str    # 源实体 ID
    target_entity_id: str    # 目标实体 ID
    relation_type: str       # 关系类型
    confidence: float        # 抽取置信度
    context: str             # 命中的上下文文本
    source_document: str     # 来源文档标识
    attributes: Dict         # 扩展属性

@dataclass
class Trend:
    name: str
    growth_rate: float
    current_momentum: float
    key_entities: List[str]
    time_range: Tuple[int, int]
    description: str

@dataclass
class ResearchGap:
    source_entity: str
    target_entity: str
    gap_type: str
    potential: float
    related_entities: List[str]
    description: str

@dataclass
class EvolutionPath:
    path: List[str]
    confidence: float
    time_span: Tuple[int, int]
    key_methods: List[str]
    summary: str

@dataclass
class ImpactAnalysis:
    entity_id: str
    entity_text: str
    impact_score: float
    influence_sources: List[str]
    influenced_targets: List[str]
    total_connections: int
    description: str
```

所有数据类均实现 `to_dict()`；`Entity` 与 `Relation` 额外提供 `from_dict()`。

## 7. 配置与扩展

### 实体类型

默认 12 种：method、dataset、model、task、metric、material、tool、theory、
measurement、software、author、institution

定制：

- 传入 `entity_types` 筛选
- 扩展 `entity_keywords` / `entity_patterns`
- 调用 `add_custom_entity_type()`

### 关系类型

默认已实现 14 种。定制：扩展 `relation_patterns` 或调用 `add_custom_relation_type()`。

### 可视化样式

```python
from research_kg.modules.visualizer import GraphVisualizer

viz = GraphVisualizer(figsize=(20, 15), dpi=200)
viz.set_custom_colors(
    entity_colors={'model': '#FF6B6B'},
    relation_colors={'uses': '#2C3E50'},
)
viz.set_custom_layout('kamada_kawai')
```

### 置信度阈值

实体与关系默认置信度见上文常量表，可通过类属性覆写，或在调用时用 `min_confidence` 过滤。

## 8. 性能与扩展性

- 批量处理按文档逐个抽取，控制内存峰值
- spaCy 按需加载；`KnowledgeGraphPipeline(lazy_visualizer=True)` 延迟加载可视化
- 正则在 `__init__` 预编译；实体 / 关系基于哈希去重
- 支持自定义实体 / 关系类型；JSON / GraphML / GEXF 多格式互通
- 易于封装为 RESTful 服务或 CLI
