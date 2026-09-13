import os
import sys

# 允许直接 `python examples/demo.py` 运行，无需先 pip install
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from research_kg import KnowledgeGraphPipeline  # noqa: E402

demo_documents = [
    """
    Transformer-based models have revolutionized natural language processing.
    The BERT model uses a bidirectional attention mechanism for pre-training.
    GPT-3 achieves state-of-the-art results on text generation tasks.
    Fine-tuning pre-trained language models has become a standard approach.
    The GLUE benchmark is widely used to evaluate NLP model performance.
    Cross-validation is essential for robust model evaluation.
    """,
    """
    Convolutional Neural Networks (CNNs) are effective for image classification.
    ResNet introduced residual connections enabling deeper network training.
    Transfer learning from pre-trained models significantly improves accuracy.
    The ImageNet dataset contains millions of labeled images.
    Data augmentation techniques like random cropping boost model robustness.
    """,
    """
    Graph Neural Networks extend traditional neural networks to graph data.
    GCN (Graph Convolutional Network) aggregates information from neighbors.
    Attention mechanisms in GAT models enable learning of edge importance.
    Node classification tasks evaluate the effectiveness of GNN architectures.
    The CORA dataset is a benchmark for citation network analysis.

    # 中文示例（也可处理中文文本）：
    # 基于Transformer的模型革新了自然语言处理领域。
    # BERT使用双向注意力机制进行预训练。
    # GCN通过聚合邻居信息来进行节点分类任务。
    """
]


demo_publications = [
    {'id': 1, 'title': 'Attention is All You Need', 'year': 2017, 'authors': 'Vaswani et al.',
     'entities': ['Transformer', 'attention', 'NLP']},
    {'id': 2, 'title': 'BERT: Pre-training of Deep Bidirectional Transformers', 'year': 2018,
     'authors': 'Devlin et al.', 'entities': ['BERT', 'attention', 'NLP', 'pre-training']},
    {'id': 3, 'title': 'Language Models are Few-Shot Learners', 'year': 2020, 'authors': 'Brown et al.',
     'entities': ['GPT-3', 'NLP', 'fine-tuning']},
    {'id': 4, 'title': 'Deep Residual Learning for Image Recognition', 'year': 2015,
     'authors': 'He et al.', 'entities': ['ResNet', 'CNN', 'image classification']},
    {'id': 5, 'title': 'Semi-Supervised Classification with Graph Convolutional Networks', 'year': 2016,
     'authors': 'Kipf & Welling', 'entities': ['GCN', 'GNN', 'node classification']},
]


current_dir = os.path.dirname(os.path.abspath(__file__))


def _output_dir():
    """返回示例产物目录并确保其存在。

    可视化组件（尤其是 PyVis）不会自动创建父目录，缺目录会直接抛 FileNotFoundError。
    """
    path = os.path.join(current_dir, 'output')
    os.makedirs(path, exist_ok=True)
    return path


def run_basic_demo():
    print("=" * 60)
    print("KNOWLEDGE GRAPH CONSTRUCTION SKILL - BASIC DEMO")
    print("=" * 60)

    pipeline = KnowledgeGraphPipeline()

    entities, relations, graph = pipeline.process_documents(demo_documents)

    print(f"\nExtracted {len(entities)} entities:")
    for entity in entities[:10]:
        print(f"  [{entity.type:10s}] {entity.text} (confidence: {entity.confidence:.2f})")

    print(f"\nExtracted {len(relations)} relations:")
    for relation in relations[:10]:
        source_text = graph.nodes[relation.source_entity_id].get('text', '')
        target_text = graph.nodes[relation.target_entity_id].get('text', '')
        print(f"  {source_text} --[{relation.relation_type}]--> {target_text}")

    output_dir = _output_dir()
    pipeline.visualize(graph, os.path.join(output_dir, 'demo_interactive.html'), 'interactive')
    pipeline.visualize(graph, os.path.join(output_dir, 'demo_static.png'), 'static')
    pipeline.visualizer.visualize_entity_distribution(graph, os.path.join(output_dir, 'demo_distribution.png'))

    analysis = pipeline.analyze(graph, demo_publications)

    print("\nTop Research Trends:")
    for trend in analysis['trends'][:5]:
        print(f"  - {trend['name']}")

    print(f"\nResearch Gaps Found: {len(analysis['gaps'])}")
    for gap in analysis['gaps'][:5]:
        print(f"  - {gap['source_entity']} -> {gap['target_entity']} ({gap['gap_type']})")

    # Demonstrate new impact analysis feature
    if entities:
        impact_result = pipeline.analyze_impact(graph, entities[0].entity_id)
        print(f"\nImpact Analysis for {entities[0].text}:")
        if 'impact_score' in impact_result:
            print(f"  - Impact Score: {impact_result['impact_score']}")
            print(f"  - In-degree: {impact_result['in_degree']}")
            print(f"  - Out-degree: {impact_result['out_degree']}")

    # Demonstrate contributor identification
    contributors = pipeline.identify_contributors(graph, top_k=5)
    print("\nTop Contributors:")
    for contrib in contributors[:5]:
        print(f"  - {contrib['entity_text']} ({contrib['entity_type']}): {contrib['combined_score']}")

    return pipeline


def run_advanced_demo():
    print("\n" + "=" * 60)
    print("KNOWLEDGE GRAPH CONSTRUCTION SKILL - ADVANCED FEATURES DEMO")
    print("=" * 60)

    pipeline = KnowledgeGraphPipeline()

    # Test custom entity types
    pipeline.entity_extractor.add_custom_entity_type(
        'domain',
        {'computer science', 'artificial intelligence', 'data science', 'machine learning'},
        [r'\b(computer science|AI|ML|data science)\b']
    )

    # Test custom relation types
    pipeline.relation_extractor.add_custom_relation_type(
        'develops',
        [r'\b(\w+)\s+develops\s+(\w+)\b', r'\b(\w+)\s+creates\s+(\w+)\b']
    )

    entities, relations, graph = pipeline.process_documents(demo_documents)

    print("\nAdvanced Features Demo:")
    print(f"  - Entities extracted: {len(entities)}")
    print(f"  - Relations extracted: {len(relations)}")

    # Show graph validation
    validation = pipeline.get_graph_validation(graph)
    print(f"  - Graph validation: {'Valid' if validation['valid'] else 'Invalid'}")
    if validation['errors']:
        print(f"  - Errors: {len(validation['errors'])}")
    if validation['warnings']:
        print(f"  - Warnings: {len(validation['warnings'])}")

    # Save a subgraph visualization
    if entities:
        subgraph_nodes = [entities[0].entity_id, entities[1].entity_id] if len(entities) >= 2 else [entities[0].entity_id]
        output_dir = _output_dir()
        pipeline.visualizer.visualize_subgraph(
            graph, subgraph_nodes,
            os.path.join(output_dir, 'subgraph.png'),
            'Subgraph Visualization'
        )
        print("  - Subgraph visualization saved")

    return pipeline


def run_full_pipeline_demo():
    print("\n" + "=" * 60)
    print("KNOWLEDGE GRAPH CONSTRUCTION SKILL - FULL PIPELINE")
    print("=" * 60)

    pipeline = KnowledgeGraphPipeline()
    output_dir = _output_dir()
    result = pipeline.run_full_pipeline(demo_documents, demo_publications, output_dir)

    # Show summary visualization
    pipeline.visualizer.visualize_graph_summary(result['graph'], os.path.join(output_dir, 'graph_summary.png'))
    print("  - Graph summary visualization saved")

    return result


def main(argv=None):
    """入口。

    支持两种用法：

    - 交互式：``python examples/demo.py``，按提示输入 1 ~ 4
    - 非交互式：``python examples/demo.py 4``，直接运行指定模式（便于脚本 / CI 调用）
    """
    argv = sys.argv[1:] if argv is None else argv

    if argv and argv[0] in {'1', '2', '3', '4'}:
        choice = argv[0]
    else:
        print("Select demo mode:")
        print("1. Basic Demo (show case entity extraction, relation extraction, visualization)")
        print("2. Advanced Features Demo (custom types, validation, etc.)")
        print("3. Full Pipeline (demonstrate complete workflow)")
        print("4. All Demos")
        choice = input("Enter choice (1-4): ").strip() or '4'

    if choice not in {'1', '2', '3', '4'}:
        print(f"Unknown choice: {choice!r}. Expected 1-4.")
        return 1

    if choice in ['1', '4']:
        run_basic_demo()

    if choice in ['2', '4']:
        run_advanced_demo()

    if choice in ['3', '4']:
        run_full_pipeline_demo()

    print(f"\nDemo completed! Check '{_output_dir()}' for generated files.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
