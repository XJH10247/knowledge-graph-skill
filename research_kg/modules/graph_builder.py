import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

import networkx as nx

from .entity_extractor import Entity
from .relation_extractor import Relation

logger = logging.getLogger(__name__)


class GraphBuilder:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.metadata = {
            'created_at': datetime.now().isoformat(),
            'version': '1.0',
            'entity_count': 0,
            'relation_count': 0,
            'entity_types': {},
            'relation_types': {}
        }

    def _reset_graph(self):
        self.graph = nx.DiGraph()

    def build_graph(self, entities: list[Entity], relations: list[Relation]) -> nx.DiGraph:
        self._reset_graph()
        self._add_entity_nodes(entities)
        self._add_relation_edges(relations)
        self._update_metadata()
        return self.graph

    def _add_entity_nodes(self, entities: list[Entity]):
        seen = set()
        for entity in entities:
            if entity.entity_id in seen:
                continue
            seen.add(entity.entity_id)
            self.graph.add_node(
                entity.entity_id,
                text=entity.text,
                type=entity.type,
                confidence=entity.confidence,
                source_document=entity.source_document,
                synonyms=entity.synonyms,
                attributes=entity.attributes
            )

    def _add_relation_edges(self, relations: list[Relation]):
        seen = set()
        for relation in relations:
            key = (relation.source_entity_id, relation.target_entity_id, relation.relation_type)
            if key in seen:
                continue
            seen.add(key)
            # Validate that both nodes exist before adding edge
            if self.graph.has_node(relation.source_entity_id) and self.graph.has_node(relation.target_entity_id):
                self.graph.add_edge(
                    relation.source_entity_id,
                    relation.target_entity_id,
                    entity_id=relation.entity_id,
                    relation_type=relation.relation_type,
                    confidence=relation.confidence,
                    context=relation.context,
                    source_document=relation.source_document,
                    attributes=relation.attributes
                )
            else:
                logger.debug(f"Skipping relation due to missing nodes: {relation.source_entity_id} -> {relation.target_entity_id}")

    def add_nodes(self, entities: list[Entity]) -> nx.DiGraph:
        self._add_entity_nodes(entities)
        self._update_metadata()
        return self.graph

    def add_edges(self, relations: list[Relation]) -> nx.DiGraph:
        self._add_relation_edges(relations)
        self._update_metadata()
        return self.graph

    def _update_metadata(self):
        self.metadata['entity_count'] = self.graph.number_of_nodes()
        self.metadata['relation_count'] = self.graph.number_of_edges()
        self.metadata['entity_types'] = self._count_entity_types()
        self.metadata['relation_types'] = self._count_relation_types()
        self.metadata['updated_at'] = datetime.now().isoformat()

    def _count_entity_types(self) -> dict[str, int]:
        counts = defaultdict(int)
        for _, data in self.graph.nodes(data=True):
            counts[data.get('type', 'unknown')] += 1
        return dict(counts)

    def _count_relation_types(self) -> dict[str, int]:
        counts = defaultdict(int)
        for _, _, data in self.graph.edges(data=True):
            counts[data.get('relation_type', 'unknown')] += 1
        return dict(counts)

    def export_graph(self, file_format: str = 'json') -> Any:
        if file_format == 'json':
            return self._to_json()
        elif file_format == 'graphml':
            import io
            buf = io.StringIO()
            nx.write_graphml(self.graph, buf)
            return buf.getvalue()
        elif file_format == 'gexf':
            import io
            buf = io.StringIO()
            nx.write_gexf(self.graph, buf)
            return buf.getvalue()
        return self.graph

    def _to_json(self) -> str:
        data = {
            'metadata': self.metadata,
            'nodes': [
                {
                    'entity_id': nid,
                    'text': d.get('text', ''),
                    'type': d.get('type', ''),
                    'confidence': d.get('confidence', 0.0),
                    'source_document': d.get('source_document', ''),
                    'synonyms': d.get('synonyms', []),
                    'attributes': d.get('attributes', {})
                }
                for nid, d in self.graph.nodes(data=True)
            ],
            'edges': [
                {
                    'source': u,
                    'target': v,
                    'relation_type': d.get('relation_type', ''),
                    'confidence': d.get('confidence', 0.0),
                    'context': d.get('context', ''),
                    'source_document': d.get('source_document', '')
                }
                for u, v, d in self.graph.edges(data=True)
            ]
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def save_to_file(self, filepath: str, file_format: str = 'json') -> str:
        try:
            if file_format == 'json':
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(self._to_json())
            elif file_format == 'graphml':
                nx.write_graphml(self.graph, filepath)
            elif file_format == 'gexf':
                nx.write_gexf(self.graph, filepath)
            else:
                raise ValueError(f"Unsupported format: {file_format}")
        except (OSError, ValueError) as e:
            logger.error(f"Failed to save graph to {filepath}: {e}")
            raise OSError(f"Failed to save graph to {filepath}: {e}") from e
        return filepath

    def load_from_file(self, filepath: str, file_format: str = 'json') -> nx.DiGraph:
        try:
            if file_format == 'json':
                with open(filepath, encoding='utf-8') as f:
                    data = json.load(f)
                self._reset_graph()
                for node_data in data.get('nodes', []):
                    self.graph.add_node(
                        node_data.get('entity_id', node_data.get('id')),
                        text=node_data.get('text', ''),
                        type=node_data.get('type', ''),
                        confidence=node_data.get('confidence', 0.0),
                        source_document=node_data.get('source_document', ''),
                        synonyms=node_data.get('synonyms', []),
                        attributes=node_data.get('attributes', {})
                    )
                for edge_data in data.get('edges', []):
                    self.graph.add_edge(
                        edge_data['source'],
                        edge_data['target'],
                        relation_type=edge_data.get('relation_type', ''),
                        confidence=edge_data.get('confidence', 0.0),
                        context=edge_data.get('context', ''),
                        source_document=edge_data.get('source_document', '')
                    )
                self.metadata = data.get('metadata', {})
            elif file_format == 'graphml':
                self.graph = nx.read_graphml(filepath)
            elif file_format == 'gexf':
                self.graph = nx.read_gexf(filepath)
            else:
                raise ValueError(f"Unsupported format: {file_format}")
        except (OSError, ValueError, json.JSONDecodeError, nx.NetworkXError) as e:
            logger.error(f"Failed to load graph from {filepath}: {e}")
            raise OSError(f"Failed to load graph from {filepath}: {e}") from e
        return self.graph

    def get_graph_statistics(self) -> dict:
        if self.graph.number_of_nodes() == 0:
            return {'status': 'empty'}

        n = self.graph.number_of_nodes()
        degree_values = [d for _, d in self.graph.degree()]
        avg_degree = sum(degree_values) / n if n > 0 else 0.0

        stats = {
            'num_nodes': n,
            'num_edges': self.graph.number_of_edges(),
            'density': nx.density(self.graph),
            'entity_types': self.metadata.get('entity_types', self._count_entity_types()),
            'relation_types': self.metadata.get('relation_types', self._count_relation_types()),
            'connected_components': nx.number_weakly_connected_components(self.graph),
            'avg_degree': avg_degree,
            'is_directed': self.graph.is_directed(),
            'is_multigraph': self.graph.is_multigraph()
        }

        try:
            stats['avg_clustering'] = nx.average_clustering(self.graph.to_undirected())
        except Exception:
            stats['avg_clustering'] = 0.0

        # Additional statistics
        if n > 0:
            try:
                stats['diameter'] = nx.diameter(self.graph.to_undirected())
            except Exception:
                stats['diameter'] = -1

            try:
                stats['radius'] = nx.radius(self.graph.to_undirected())
            except Exception:
                stats['radius'] = -1

        return stats

    def validate_graph(self) -> dict:
        """Validate the integrity of the graph."""
        validation = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        # Check for isolated nodes
        isolated_nodes = list(nx.isolates(self.graph))
        if isolated_nodes:
            validation['warnings'].append(f"Found {len(isolated_nodes)} isolated nodes")

        # Check for self-loops
        self_loops = list(nx.selfloop_edges(self.graph))
        if self_loops:
            validation['errors'].append(f"Found {len(self_loops)} self-loops")

        # Check for duplicate edges
        edge_list = list(self.graph.edges())
        unique_edges = set(edge_list)
        if len(edge_list) != len(unique_edges):
            validation['warnings'].append(f"Detected {len(edge_list) - len(unique_edges)} duplicate edges")

        # Check graph properties
        if not self.graph.is_directed():
            validation['errors'].append("Graph should be directed for knowledge graph")

        # Check node consistency
        nodes = list(self.graph.nodes())
        for node_id in nodes:
            if not self.graph.has_node(node_id):
                validation['errors'].append(f"Node {node_id} exists in node list but not in graph")

        if validation['errors']:
            validation['valid'] = False

        return validation

    def filter_subgraph(self, entity_ids: list[str] = None, entity_types: list[str] = None,
                        relation_types: list[str] = None) -> nx.DiGraph:
        nodes_to_remove = set()

        if entity_ids:
            keep = set(entity_ids)
            nodes_to_remove.update(n for n in self.graph.nodes() if n not in keep)

        if entity_types:
            keep = {n for n, d in self.graph.nodes(data=True) if d.get('type') in entity_types}
            nodes_to_remove.update(n for n in self.graph.nodes() if n not in keep and n not in nodes_to_remove)

        subgraph = self.graph.copy()
        subgraph.remove_nodes_from(nodes_to_remove)

        if relation_types:
            edges_to_remove = [
                (u, v) for u, v, d in subgraph.edges(data=True)
                if d.get('relation_type') not in relation_types
            ]
            subgraph.remove_edges_from(edges_to_remove)

        return subgraph

    def merge_graphs(self, other_graph: nx.DiGraph) -> nx.DiGraph:
        try:
            merged = nx.compose(self.graph, other_graph)
            self.graph = merged
            self._update_metadata()
            return self.graph
        except Exception as e:
            logger.error(f"Error merging graphs: {e}")
            raise

    def find_central_entities(self, top_k: int = 10, method: str = 'degree') -> list[dict]:
        if self.graph.number_of_nodes() == 0:
            return []

        try:
            if method == 'degree':
                centrality = nx.degree_centrality(self.graph)
            elif method == 'betweenness':
                centrality = nx.betweenness_centrality(self.graph)
            elif method == 'closeness':
                centrality = nx.closeness_centrality(self.graph)
            elif method == 'pagerank':
                centrality = nx.pagerank(self.graph)
            else:
                centrality = nx.degree_centrality(self.graph)

            sorted_entities = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:top_k]

            return [
                {
                    'entity_id': eid,
                    'text': self.graph.nodes[eid].get('text', ''),
                    'type': self.graph.nodes[eid].get('type', ''),
                    'centrality_score': score,
                    'centrality_method': method
                }
                for eid, score in sorted_entities
            ]
        except Exception as e:
            logger.error(f"Error computing central entities: {e}")
            return []

    def find_entity_neighbors(self, entity_id: str, depth: int = 1) -> dict:
        if not self.graph.has_node(entity_id):
            return {'entity_id': entity_id, 'found': False}

        result = {
            'entity_id': entity_id,
            'entity_text': self.graph.nodes[entity_id].get('text', ''),
            'found': True,
            'neighbors': []
        }

        if depth == 1:
            for _, target, data in self.graph.out_edges(entity_id, data=True):
                nd = self.graph.nodes[target]
                result['neighbors'].append({
                    'entity_id': target,
                    'text': nd.get('text', ''),
                    'type': nd.get('type', ''),
                    'relation': data.get('relation_type', ''),
                    'direction': 'outgoing',
                    'confidence': data.get('confidence', 0.0)
                })

            for source, _, data in self.graph.in_edges(entity_id, data=True):
                nd = self.graph.nodes[source]
                result['neighbors'].append({
                    'entity_id': source,
                    'text': nd.get('text', ''),
                    'type': nd.get('type', ''),
                    'relation': data.get('relation_type', ''),
                    'direction': 'incoming',
                    'confidence': data.get('confidence', 0.0)
                })
        elif depth > 1:
            # Recursive neighbor search for greater depth
            visited = set()
            queue = [(entity_id, 0)]
            neighbors = []

            while queue:
                current_id, current_depth = queue.pop(0)
                if current_depth >= depth or current_id in visited:
                    continue

                visited.add(current_id)

                # Get neighbors
                for _, target, data in self.graph.out_edges(current_id, data=True):
                    if target not in visited:
                        nd = self.graph.nodes[target]
                        neighbors.append({
                            'entity_id': target,
                            'text': nd.get('text', ''),
                            'type': nd.get('type', ''),
                            'relation': data.get('relation_type', ''),
                            'direction': 'outgoing',
                            'depth': current_depth + 1,
                            'confidence': data.get('confidence', 0.0)
                        })
                        queue.append((target, current_depth + 1))

                for source, _, data in self.graph.in_edges(current_id, data=True):
                    if source not in visited:
                        nd = self.graph.nodes[source]
                        neighbors.append({
                            'entity_id': source,
                            'text': nd.get('text', ''),
                            'type': nd.get('type', ''),
                            'relation': data.get('relation_type', ''),
                            'direction': 'incoming',
                            'depth': current_depth + 1,
                            'confidence': data.get('confidence', 0.0)
                        })
                        queue.append((source, current_depth + 1))

            result['neighbors'] = neighbors

        return result

    def get_entity_relations(self, entity_id: str) -> dict:
        """Get all relations for a specific entity."""
        if not self.graph.has_node(entity_id):
            return {'entity_id': entity_id, 'found': False}

        entity_text = self.graph.nodes[entity_id].get('text', '')
        relations = {
            'entity_id': entity_id,
            'entity_text': entity_text,
            'found': True,
            'outgoing': [],
            'incoming': []
        }

        # Get outgoing relations
        for target, data in self.graph.succ[entity_id].items():
            target_text = self.graph.nodes[target].get('text', '')
            relations['outgoing'].append({
                'target_entity_id': target,
                'target_entity_text': target_text,
                'relation_type': data.get('relation_type', ''),
                'confidence': data.get('confidence', 0.0)
            })

        # Get incoming relations
        for source, data in self.graph.pred[entity_id].items():
            source_text = self.graph.nodes[source].get('text', '')
            relations['incoming'].append({
                'source_entity_id': source,
                'source_entity_text': source_text,
                'relation_type': data.get('relation_type', ''),
                'confidence': data.get('confidence', 0.0)
            })

        return relations
