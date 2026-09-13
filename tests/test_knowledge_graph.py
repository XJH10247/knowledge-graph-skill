import json
import os
import sys
import tempfile

import pytest

# 允许在未安装本包的情况下直接运行 `pytest tests/`
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from research_kg import KnowledgeGraphPipeline  # noqa: E402
from research_kg.modules.entity_extractor import Entity, EntityExtractor  # noqa: E402
from research_kg.modules.graph_builder import GraphBuilder  # noqa: E402
from research_kg.modules.relation_extractor import Relation, RelationExtractor  # noqa: E402
from research_kg.modules.trajectory_analyzer import TrajectoryAnalyzer  # noqa: E402


def _make_entity(text, etype='model', confidence=0.9, eid=None):
    return Entity(
        entity_id=eid or text, text=text, type=etype,
        start_pos=0, end_pos=len(text), confidence=confidence,
        source_document='doc_0'
    )


def _make_relation(src, tgt, rtype='uses', confidence=0.8, rid=None):
    return Relation(
        entity_id=rid or f"{src}_{tgt}", source_entity_id=src,
        target_entity_id=tgt, relation_type=rtype, confidence=confidence,
        context='', source_document='doc_0'
    )


class TestEntityExtractor:
    def setup_method(self):
        self.extractor = EntityExtractor()

    def test_extract_entities(self):
        text = "BERT model uses attention mechanism for NLP tasks."
        entities = self.extractor.extract_entities(text, min_confidence=0.0)
        assert len(entities) > 0
        texts = [e.text.lower() for e in entities]
        assert 'bert' in texts or 'model' in texts

    def test_extract_empty(self):
        assert len(self.extractor.extract_entities("")) == 0

    def test_extract_from_documents(self):
        results = self.extractor.extract_from_documents(
            ["CNN for image classification.", "LSTM for text generation."],
            min_confidence=0.0
        )
        assert len(results) == 2

    def test_statistics(self):
        entities = [
            _make_entity('BERT', 'model', 0.9, '1'),
            _make_entity('ImageNet', 'dataset', 0.85, '2'),
            _make_entity('classification', 'task', 0.7, '3'),
        ]
        stats = self.extractor.get_entity_statistics(entities)
        assert stats['total_entities'] == 3
        assert stats['by_type']['model'] == 1
        assert stats['by_type']['task'] == 1

    def test_deduplicate(self):
        entities = [
            _make_entity('BERT', 'model', 0.9, '1'),
            _make_entity('BERT', 'model', 0.7, '2'),
            _make_entity('NLP', 'task', 0.8, '3'),
        ]
        deduped = self.extractor._deduplicate_entities(entities)
        assert len(deduped) == 2
        bert = [e for e in deduped if e.text == 'BERT'][0]
        assert bert.confidence == 0.9

    def test_build_vocabulary(self):
        entities = [
            _make_entity('BERT', 'model', 0.9, '1'),
            _make_entity('GPT', 'model', 0.8, '2'),
            _make_entity('NLP', 'task', 0.8, '3'),
        ]
        vocab = self.extractor.build_entity_vocabulary(entities)
        assert 'model' in vocab
        assert len(vocab['model']) == 2


class TestRelationExtractor:
    def setup_method(self):
        self.extractor = RelationExtractor()

    def test_extract_relations(self):
        entities = [
            _make_entity('BERT', 'model', 0.9, '1'),
            _make_entity('NLP', 'task', 0.8, '2'),
        ]
        text = "BERT model uses attention for NLP tasks."
        relations = self.extractor.extract_relations(text, entities)
        assert isinstance(relations, list)

    def test_extract_empty(self):
        assert len(self.extractor.extract_relations("No entities.", [])) == 0

    def test_deduplicate(self):
        relations = [
            _make_relation('1', '2', 'uses', 0.9, 'r1'),
            _make_relation('1', '2', 'uses', 0.7, 'r2'),
            _make_relation('2', '3', 'extends', 0.8, 'r3'),
        ]
        deduped = self.extractor._deduplicate_relations(relations)
        assert len(deduped) == 2

    def test_statistics(self):
        relations = [
            _make_relation('1', '2', 'uses', 0.9, 'r1'),
            _make_relation('2', '3', 'evaluates', 0.7, 'r2'),
        ]
        stats = self.extractor.get_relation_statistics(relations)
        assert stats['total_relations'] == 2
        assert stats['by_type']['uses'] == 1


class TestGraphBuilder:
    def setup_method(self):
        self.builder = GraphBuilder()

    def test_build_graph(self):
        entities = [
            _make_entity('BERT', 'model', 0.9, '1'),
            _make_entity('NLP', 'task', 0.8, '2'),
        ]
        relations = [_make_relation('1', '2', 'uses', 0.7, 'r1')]
        graph = self.builder.build_graph(entities, relations)
        assert graph.number_of_nodes() == 2
        assert graph.number_of_edges() == 1

    def test_empty_build(self):
        graph = self.builder.build_graph([], [])
        assert graph.number_of_nodes() == 0

    def test_statistics(self):
        entities = [
            _make_entity('BERT', 'model', 0.9, '1'),
            _make_entity('NLP', 'task', 0.8, '2'),
        ]
        relations = [_make_relation('1', '2', 'uses', 0.7, 'r1')]
        self.builder.build_graph(entities, relations)
        stats = self.builder.get_graph_statistics()
        assert stats['num_nodes'] == 2
        assert stats['num_edges'] == 1

    def test_export_import_json(self):
        entities = [
            _make_entity('BERT', 'model', 0.9, '1'),
            _make_entity('NLP', 'task', 0.8, '2'),
        ]
        relations = [_make_relation('1', '2', 'uses', 0.7, 'r1')]
        self.builder.build_graph(entities, relations)
        exported = self.builder.export_graph('json')
        data = json.loads(exported)
        assert len(data['nodes']) == 2
        assert len(data['edges']) == 1

    def test_save_load(self):
        entities = [
            _make_entity('BERT', 'model', 0.9, '1'),
            _make_entity('NLP', 'task', 0.8, '2'),
        ]
        relations = [_make_relation('1', '2', 'uses', 0.7, 'r1')]
        self.builder.build_graph(entities, relations)

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as f:
            path = f.name
            self.builder.save_to_file(path, 'json')

        new_builder = GraphBuilder()
        loaded = new_builder.load_from_file(path, 'json')
        assert loaded.number_of_nodes() == 2
        assert loaded.number_of_edges() == 1
        os.unlink(path)

    def test_filter_subgraph(self):
        entities = [
            _make_entity('BERT', 'model', 0.9, '1'),
            _make_entity('GPT', 'model', 0.8, '2'),
            _make_entity('NLP', 'task', 0.8, '3'),
        ]
        relations = [
            _make_relation('1', '3', 'uses', 0.7, 'r1'),
            _make_relation('2', '3', 'uses', 0.6, 'r2'),
        ]
        self.builder.build_graph(entities, relations)
        filtered = self.builder.filter_subgraph(entity_ids=['1', '3'])
        assert filtered.number_of_nodes() == 2
        assert filtered.number_of_edges() == 1

    def test_find_central(self):
        entities = [
            _make_entity('BERT', 'model', 0.9, '1'),
            _make_entity('GPT', 'model', 0.8, '2'),
            _make_entity('NLP', 'task', 0.8, '3'),
        ]
        relations = [
            _make_relation('1', '3', 'uses', 0.7, 'r1'),
            _make_relation('2', '3', 'uses', 0.6, 'r2'),
        ]
        self.builder.build_graph(entities, relations)
        central = self.builder.find_central_entities(top_k=2)
        assert len(central) == 2

    def test_entity_neighbors(self):
        entities = [
            _make_entity('BERT', 'model', 0.9, '1'),
            _make_entity('NLP', 'task', 0.8, '2'),
        ]
        relations = [_make_relation('1', '2', 'uses', 0.7, 'r1')]
        self.builder.build_graph(entities, relations)
        neighbors = self.builder.find_entity_neighbors('1')
        assert neighbors['found'] is True
        assert len(neighbors['neighbors']) == 1


class TestTrajectoryAnalyzer:
    def test_empty_analysis(self):
        analyzer = TrajectoryAnalyzer()
        summary = analyzer.generate_research_summary()
        assert summary['status'] == 'empty'

    def test_detect_trends_empty(self):
        analyzer = TrajectoryAnalyzer()
        assert len(analyzer.detect_trends()) == 0

    def test_analyze_with_graph(self):
        analyzer = TrajectoryAnalyzer()
        e1 = _make_entity('BERT', 'model', 0.9, 'm1')
        e2 = _make_entity('GPT', 'model', 0.8, 'm2')
        r = _make_relation('m1', 'm2', 'extends', 0.7, 'r1')
        builder = GraphBuilder()
        analyzer.graph = builder.build_graph([e1, e2], [r])
        trends = analyzer.detect_trends()
        assert len(trends) > 0
        gaps = analyzer.find_research_gaps()
        assert isinstance(gaps, list)
        summary = analyzer.generate_research_summary()
        assert summary['graph_statistics']['total_entities'] == 2


class TestPipeline:
    def test_full_pipeline(self):
        pipeline = KnowledgeGraphPipeline()
        documents = [
            "Transformer-based models have revolutionized NLP. BERT uses attention.",
            "ResNet introduced residual connections for deeper networks.",
        ]
        entities, relations, graph = pipeline.process_documents(documents)
        assert len(entities) > 0
        assert graph.number_of_nodes() > 0

    def test_visualize_static(self):
        pytest.importorskip('matplotlib')
        pytest.importorskip('pyvis')
        pipeline = KnowledgeGraphPipeline()
        documents = ["BERT uses attention for NLP."]
        entities, relations, graph = pipeline.process_documents(documents)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, 'test_graph.png')
            result = pipeline.visualize(graph, output_path, 'static')
            assert result == output_path
            assert os.path.exists(output_path)

    def test_analyze(self):
        pipeline = KnowledgeGraphPipeline()
        documents = ["BERT uses attention for NLP."]
        entities, relations, graph = pipeline.process_documents(documents)
        analysis = pipeline.analyze(graph)
        assert 'summary' in analysis
        assert 'trends' in analysis
        assert 'gaps' in analysis


class TestVisualizer:
    """可视化模块的回归测试。

    重点覆盖两个曾导致崩溃 / 产物失效的行为：
    1. 交互式 HTML 必须是自包含的，且不在工作目录留下 pyvis 的 ``lib/`` 文件夹；
    2. ``visualize_timeline`` 遇到图谱中不存在的实体引用时必须跳过而不是断言失败。
    """

    def setup_method(self):
        # 可视化依赖是可选的，缺失时跳过而非报错
        pytest.importorskip('pyvis')
        pytest.importorskip('matplotlib')
        from research_kg.modules.visualizer import GraphVisualizer
        self.viz = GraphVisualizer()

    @staticmethod
    def _graph():
        builder = GraphBuilder()
        entities = [
            _make_entity('BERT', 'model', 0.9, 'm1'),
            _make_entity('attention', 'method', 0.8, 'k1'),
        ]
        relations = [_make_relation('m1', 'k1', 'uses', 0.7, 'r1')]
        return builder.build_graph(entities, relations)

    def test_interactive_html_is_self_contained(self):
        graph = self._graph()
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                out = os.path.join(tmpdir, 'graph.html')
                assert self.viz.visualize_interactive(graph, out) == out
                assert os.path.exists(out)

                html = open(out, encoding='utf-8').read()
                # vis-network 已内联，不依赖外部资源
                assert 'vis-network' in html
                # 关键回归点：不再产生 lib/ 资源目录
                assert not os.path.isdir(os.path.join(tmpdir, 'lib'))
            finally:
                os.chdir(cwd)

    def test_timeline_resolves_entity_text(self):
        """publications 里的 entities 用实体文本而非节点 ID 时也应能正常连边。"""
        graph = self._graph()
        publications = [
            {'id': 1, 'title': 'Attention is All You Need', 'year': 2017,
             'entities': ['BERT', 'attention']},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, 'timeline.html')
            assert self.viz.visualize_timeline(graph, publications, out) == out
            assert os.path.exists(out)

    def test_timeline_skips_unknown_entities(self):
        """未知实体引用必须被跳过，而不是让 pyvis 断言失败。"""
        graph = self._graph()
        publications = [
            {'id': 1, 'title': 'A Paper', 'year': 2020,
             'entities': ['not-in-graph', 'also-missing']},
            {'id': 2, 'title': 'Another Paper', 'year': 2021, 'entities': []},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, 'timeline.html')
            assert self.viz.visualize_timeline(graph, publications, out) == out
            assert os.path.exists(out)


class TestWritePyvisHtmlUtf8:
    """回归：Windows CI 上默认 cp1252 写 HTML 会 UnicodeEncodeError。"""

    def test_writes_utf8_not_platform_default(self):
        from research_kg.modules.html_io import write_pyvis_html

        class FakeNet:
            def generate_html(self):
                # 模拟内联 vis-network 中超出 cp1252 的字符
                return "<html><body>研究趋势·BERT — “注意力”</body></html>"

            def write_html(self, *args, **kwargs):
                raise AssertionError("should use generate_html + UTF-8 write")

        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, 'sub', 'graph.html')
            assert write_pyvis_html(FakeNet(), out) == out
            with open(out, encoding='utf-8') as f:
                html = f.read()
            assert '研究趋势' in html
            assert 'BERT' in html
