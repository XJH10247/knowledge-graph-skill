"""科研知识图谱的五大核心模块。

各模块可独立使用，也可通过 :class:`research_kg.KnowledgeGraphPipeline` 串联。
"""

from .entity_extractor import Entity, EntityExtractor, EntityType
from .graph_builder import GraphBuilder
from .relation_extractor import Relation, RelationExtractor, RelationType
from .trajectory_analyzer import (
    EvolutionPath,
    ImpactAnalysis,
    ResearchGap,
    TrajectoryAnalyzer,
    Trend,
)

# visualizer 依赖 matplotlib / pyvis，按需导入以免拖累纯抽取流程。
_LAZY_EXPORTS = {'GraphVisualizer'}

__all__ = [
    'Entity', 'EntityExtractor', 'EntityType',
    'Relation', 'RelationExtractor', 'RelationType',
    'GraphBuilder',
    'TrajectoryAnalyzer', 'Trend', 'ResearchGap', 'EvolutionPath', 'ImpactAnalysis',
    'GraphVisualizer',
]


def __getattr__(name):
    if name in _LAZY_EXPORTS:
        from .visualizer import GraphVisualizer
        return GraphVisualizer
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
