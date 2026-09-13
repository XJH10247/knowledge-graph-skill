"""research_kg —— 从科研文献自动构建领域知识图谱。

顶层导出五大模块及其数据结构，并提供统一入口 :class:`KnowledgeGraphPipeline`。

快速开始::

    from research_kg import KnowledgeGraphPipeline

    pipeline = KnowledgeGraphPipeline()
    entities, relations, graph = pipeline.process_documents(["BERT uses attention."])
"""

from .modules.entity_extractor import Entity, EntityExtractor, EntityType
from .modules.graph_builder import GraphBuilder
from .modules.relation_extractor import Relation, RelationExtractor, RelationType
from .modules.trajectory_analyzer import (
    EvolutionPath,
    ImpactAnalysis,
    ResearchGap,
    TrajectoryAnalyzer,
    Trend,
)

__version__ = '1.0.0'


class KnowledgeGraphPipeline:
    def __init__(self, lazy_visualizer: bool = True):
        self.entity_extractor = EntityExtractor()
        self.relation_extractor = RelationExtractor()
        self.graph_builder = GraphBuilder()
        self.trajectory_analyzer = TrajectoryAnalyzer()
        # 延迟导入 visualizer：避免 process_documents 等纯抽取流程
        # 依赖 matplotlib / pyvis（本地环境可能缺少这些库）
        self._visualizer = None
        if not lazy_visualizer:
            self._load_visualizer()

    def _load_visualizer(self):
        if self._visualizer is None:
            from .modules.visualizer import GraphVisualizer
            self._visualizer = GraphVisualizer()

    @property
    def visualizer(self):
        self._load_visualizer()
        return self._visualizer

    def process_documents(self, documents, entity_types=None, min_confidence=0.5):
        all_entities = self.entity_extractor.extract_from_documents(
            documents, entity_types, min_confidence
        )
        all_relations = self.relation_extractor.extract_from_documents(
            documents, all_entities
        )
        flat_entities = [e for entity_list in all_entities for e in entity_list]
        flat_relations = [r for rel_list in all_relations for r in rel_list]
        graph = self.graph_builder.build_graph(flat_entities, flat_relations)
        self.trajectory_analyzer.graph = graph
        return flat_entities, flat_relations, graph

    def visualize(self, graph, output_path='knowledge_graph.html', mode='interactive'):
        if mode == 'interactive':
            return self.visualizer.visualize_interactive(graph, output_path)
        return self.visualizer.visualize_static(graph, output_path)

    def analyze(self, graph, publications=None):
        self.trajectory_analyzer.graph = graph
        summary = self.trajectory_analyzer.generate_research_summary()
        trends = self.trajectory_analyzer.detect_trends()
        gaps = self.trajectory_analyzer.find_research_gaps()
        evolutions = []
        if publications:
            evolutions = self.trajectory_analyzer.analyze_evolution(publications)
        return {
            'summary': summary,
            'trends': [t.to_dict() for t in trends],
            'gaps': [g.to_dict() for g in gaps],
            'evolutions': [e.to_dict() for e in evolutions]
        }

    def run_full_pipeline(self, documents, publications=None, output_dir='./output'):
        import os
        os.makedirs(output_dir, exist_ok=True)

        print("[1/5] Extracting entities...")
        entities, relations, graph = self.process_documents(documents)

        print("[2/5] Extracting relations...")
        entity_stats = self.entity_extractor.get_entity_statistics(entities)
        rel_stats = self.relation_extractor.get_relation_statistics(relations)
        print(f"     - Entities: {entity_stats['total_entities']}")
        print(f"     - Relations: {rel_stats['total_relations']}")

        print("[3/5] Building knowledge graph...")
        graph_stats = self.graph_builder.get_graph_statistics()
        print(f"     - Nodes: {graph_stats['num_nodes']}, Edges: {graph_stats['num_edges']}")

        print("[4/5] Generating visualizations...")
        interactive_path = os.path.join(output_dir, 'knowledge_graph.html')
        static_path = os.path.join(output_dir, 'knowledge_graph.png')
        dist_path = os.path.join(output_dir, 'entity_distribution.png')
        self.visualize(graph, interactive_path, 'interactive')
        self.visualize(graph, static_path, 'static')
        self.visualizer.visualize_entity_distribution(graph, dist_path)

        print("[5/5] Analyzing research trajectories...")
        analysis = self.analyze(graph, publications)

        print("\n" + "="*60)
        print("KNOWLEDGE GRAPH CONSTRUCTION COMPLETE")
        print("="*60)
        print("\nGraph Statistics:")
        print(f"  - Entities: {graph_stats['num_nodes']}")
        print(f"  - Relations: {graph_stats['num_edges']}")
        print(f"  - Density: {graph_stats['density']:.4f}")
        print(f"  - Connected Components: {graph_stats['connected_components']}")

        print("\nTop Research Trends:")
        for trend in analysis['trends'][:5]:
            print(f"  - {trend['name']} (growth: {trend['growth_rate']:.2f})")

        print(f"\nResearch Gaps Found: {len(analysis['gaps'])}")
        print(f"Evolution Paths: {len(analysis['evolutions'])}")

        print("\nOutput files:")
        print(f"  - Interactive graph: {interactive_path}")
        print(f"  - Static graph: {static_path}")
        print(f"  - Entity distribution: {dist_path}")

        return {
            'entities': entities,
            'relations': relations,
            'graph': graph,
            'analysis': analysis,
            'output_dir': output_dir
        }

    def get_graph_validation(self, graph):
        """Validate the integrity of the constructed graph."""
        return self.graph_builder.validate_graph()

    def get_entity_relations(self, graph, entity_id):
        """Get all relations for a specific entity."""
        return self.graph_builder.get_entity_relations(entity_id)

    def analyze_impact(self, graph, entity_id):
        """Analyze the impact of a specific entity."""
        self.trajectory_analyzer.graph = graph
        return self.trajectory_analyzer.analyze_impact_strength(entity_id)

    def identify_contributors(self, graph, top_k=10):
        """Identify key contributors in the knowledge graph."""
        self.trajectory_analyzer.graph = graph
        return self.trajectory_analyzer.identify_key_contributors(top_k)


__all__ = [
    'EntityExtractor', 'Entity', 'EntityType',
    'RelationExtractor', 'Relation', 'RelationType',
    'GraphBuilder',
    'TrajectoryAnalyzer', 'Trend', 'ResearchGap', 'EvolutionPath', 'ImpactAnalysis',
    'KnowledgeGraphPipeline'
]
