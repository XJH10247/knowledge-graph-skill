import logging
from collections import defaultdict
from dataclasses import dataclass

import networkx as nx

logger = logging.getLogger(__name__)


@dataclass
class Trend:
    name: str
    growth_rate: float
    current_momentum: float
    key_entities: list[str]
    time_range: tuple[int, int]
    description: str

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'growth_rate': self.growth_rate,
            'current_momentum': self.current_momentum,
            'key_entities': self.key_entities,
            'time_range': list(self.time_range),
            'description': self.description
        }


@dataclass
class ResearchGap:
    source_entity: str
    target_entity: str
    gap_type: str
    potential: float
    related_entities: list[str]
    description: str

    def to_dict(self) -> dict:
        return {
            'source_entity': self.source_entity,
            'target_entity': self.target_entity,
            'gap_type': self.gap_type,
            'potential': self.potential,
            'related_entities': self.related_entities,
            'description': self.description
        }


@dataclass
class EvolutionPath:
    path: list[str]
    confidence: float
    time_span: tuple[int, int]
    key_methods: list[str]
    summary: str

    def to_dict(self) -> dict:
        return {
            'path': self.path,
            'confidence': self.confidence,
            'time_span': list(self.time_span),
            'key_methods': self.key_methods,
            'summary': self.summary
        }


@dataclass
class ImpactAnalysis:
    entity_id: str
    entity_text: str
    impact_score: float
    influence_sources: list[str]
    influenced_targets: list[str]
    total_connections: int
    description: str

    def to_dict(self) -> dict:
        return {
            'entity_id': self.entity_id,
            'entity_text': self.entity_text,
            'impact_score': self.impact_score,
            'influence_sources': self.influence_sources,
            'influenced_targets': self.influenced_targets,
            'total_connections': self.total_connections,
            'description': self.description
        }


class TrajectoryAnalyzer:
    DEFAULT_TREND_ENTITY_TYPES = ['method', 'model', 'task']
    DEFAULT_GAP_ENTITY_TYPES = ['method', 'model', 'dataset', 'task']

    def __init__(self, graph: nx.DiGraph = None):
        self.graph = graph or nx.DiGraph()

    def analyze_evolution(self, publications: list[dict], max_methods: int = 20,
                         max_results: int = 10) -> list[EvolutionPath]:
        if not publications or self.graph.number_of_nodes() == 0:
            return []

        try:
            sorted_pubs = sorted(publications, key=lambda p: p.get('year', 0))
            method_nodes = [
                (n, d) for n, d in self.graph.nodes(data=True)
                if d.get('type') == 'method'
            ]

            if not method_nodes:
                return []

            timeline_nodes = defaultdict(list)
            for pub in sorted_pubs:
                year = pub.get('year', 0)
                for entity_id in (pub.get('entities') or []):
                    if self.graph.has_node(entity_id):
                        timeline_nodes[year].append(entity_id)

            sorted_years = sorted(timeline_nodes.keys())
            if len(sorted_years) < 2:
                return []

            evolution_paths = []
            method_nodes.sort(key=lambda x: self.graph.degree(x[0]), reverse=True)

            for method_id, method_data in method_nodes[:max_methods]:
                path = []
                confidence = 0.0
                method_text = method_data.get('text', '')

                for _i, year in enumerate(sorted_years):
                    if method_id in timeline_nodes[year]:
                        path.append((year, method_text))
                        confidence += 1.0 / len(sorted_years)

                if len(path) >= 2:
                    key_methods = {method_text}
                    for pred_id in self.graph.predecessors(method_id):
                        if self.graph.has_node(pred_id):
                            key_methods.add(self.graph.nodes[pred_id].get('text', ''))
                    for succ_id in self.graph.successors(method_id):
                        if self.graph.has_node(succ_id):
                            key_methods.add(self.graph.nodes[succ_id].get('text', ''))

                    evolution_paths.append(EvolutionPath(
                        path=[p[1] for p in path],
                        confidence=confidence,
                        time_span=(path[0][0], path[-1][0]),
                        key_methods=list(key_methods),
                        summary=f"Evolution of '{method_text}' over {path[-1][0] - path[0][0]} years"
                    ))

            evolution_paths.sort(key=lambda p: p.confidence, reverse=True)
            return evolution_paths[:max_results]
        except Exception as e:
            logger.error(f"Error in analyze_evolution: {e}")
            return []

    def detect_trends(self, time_window: int = 5, entity_types: list[str] = None,
                     max_results: int = 15) -> list[Trend]:
        if self.graph.number_of_nodes() == 0:
            return []

        try:
            entity_types = entity_types or self.DEFAULT_TREND_ENTITY_TYPES
            trends = []

            for entity_id, data in self.graph.nodes(data=True):
                etype = data.get('type', '')
                if etype not in entity_types:
                    continue

                text = data.get('text', '')
                in_degree = self.graph.in_degree(entity_id)
                out_degree = self.graph.out_degree(entity_id)
                degree_score = in_degree + out_degree

                if degree_score > 0:
                    growth_rate = in_degree / degree_score if degree_score > 0 else 0.0
                    trends.append(Trend(
                        name=text,
                        growth_rate=round(growth_rate, 4),
                        current_momentum=degree_score,
                        key_entities=[text],
                        time_range=(0, 0),
                        description=f"'{text}' has {in_degree} incoming and {out_degree} outgoing relations"
                    ))

            trends.sort(key=lambda t: t.growth_rate, reverse=True)
            return trends[:max_results]
        except Exception as e:
            logger.error(f"Error in detect_trends: {e}")
            return []

    def find_research_gaps(self, max_results: int = 20, min_common_neighbors: int = 1) -> list[ResearchGap]:
        n = self.graph.number_of_nodes()
        if n < 3:
            return []

        try:
            existing_edges = {(u, v) for u, v in self.graph.edges()}
            entity_types = {nid: data.get('type', '') for nid, data in self.graph.nodes(data=True)}

            undirected = self.graph.to_undirected()
            candidate_pairs = set()

            for u in self.graph.nodes():
                for v in self.graph.nodes():
                    if u >= v:
                        continue
                    if (u, v) in existing_edges or (v, u) in existing_edges:
                        continue
                    # Skip if entities are of the same type (may not be meaningful)
                    if entity_types.get(u) == entity_types.get(v):
                        continue
                    if nx.has_path(undirected, u, v):
                        candidate_pairs.add((u, v))

            gaps = []
            for u, v in candidate_pairs:
                common = list(nx.common_neighbors(undirected, u, v))
                if len(common) < min_common_neighbors:
                    continue

                potential = min(5, len(common)) / 5.0
                u_text = self.graph.nodes[u].get('text', '')
                v_text = self.graph.nodes[v].get('text', '')

                gaps.append(ResearchGap(
                    source_entity=u_text,
                    target_entity=v_text,
                    gap_type=f"{entity_types.get(u, '?')}-{entity_types.get(v, '?')}",
                    potential=potential,
                    related_entities=[self.graph.nodes[n].get('text', '') for n in common[:5]],
                    description=f"Potential connection between '{u_text}' and '{v_text}' with {len(common)} common neighbors"
                ))

            gaps.sort(key=lambda g: g.potential, reverse=True)
            return gaps[:max_results]
        except Exception as e:
            logger.error(f"Error in find_research_gaps: {e}")
            return []

    def generate_research_summary(self) -> dict:
        if self.graph.number_of_nodes() == 0:
            return {'status': 'empty', 'message': 'No graph data available'}

        try:
            entity_types = defaultdict(list)
            for _, data in self.graph.nodes(data=True):
                entity_types[data.get('type', 'unknown')].append(data.get('text', ''))

            relation_types = defaultdict(list)
            for _, _, data in self.graph.edges(data=True):
                relation_types[data.get('relation_type', 'unknown')].append(True)

            central_entities = self._find_central_entities(top_k=5)
            et_dist = {k: len(v) for k, v in entity_types.items()}
            total_types = len(entity_types)

            summary = {
                'graph_statistics': {
                    'total_entities': self.graph.number_of_nodes(),
                    'total_relations': self.graph.number_of_edges(),
                    'entity_types': et_dist,
                    'relation_types': {k: len(v) for k, v in relation_types.items()},
                    'density': nx.density(self.graph),
                    'connected_components': nx.number_weakly_connected_components(self.graph),
                    'avg_clustering_coefficient': nx.average_clustering(self.graph.to_undirected())
                },
                'key_findings': {
                    'central_entities': central_entities,
                    'entity_type_distribution': et_dist
                },
                'suggestions': []
            }

            density = nx.density(self.graph)
            if density < 0.01:
                summary['suggestions'].append(
                    "Graph is sparse. Consider adding more documents or extracting more relations."
                )

            for etype, entities in entity_types.items():
                if total_types > 0 and len(entities) > total_types * 0.4:
                    summary['suggestions'].append(
                        f"High concentration of '{etype}' entities. Consider diversifying entity types."
                    )

            if nx.number_weakly_connected_components(self.graph) > 5:
                summary['suggestions'].append(
                    "Multiple disconnected components detected. Consider integrating with other sources."
                )

            return summary
        except Exception as e:
            logger.error(f"Error in generate_research_summary: {e}")
            return {'status': 'error', 'message': str(e)}

    def _find_central_entities(self, top_k: int = 5) -> list[dict]:
        try:
            # Try different centrality measures with fallbacks
            try:
                centrality = nx.pagerank(self.graph)
            except Exception:
                try:
                    centrality = nx.degree_centrality(self.graph)
                except Exception:
                    centrality = nx.closeness_centrality(self.graph)

            sorted_entities = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:top_k]

            return [
                {
                    'name': self.graph.nodes[eid].get('text', ''),
                    'type': self.graph.nodes[eid].get('type', ''),
                    'centrality_score': round(score, 4),
                    'degree': self.graph.degree(eid),
                    'in_degree': self.graph.in_degree(eid),
                    'out_degree': self.graph.out_degree(eid)
                }
                for eid, score in sorted_entities
            ]
        except Exception as e:
            logger.error(f"Error in _find_central_entities: {e}")
            return []

    def analyze_temporal_evolution(self, publications: list[dict]) -> dict:
        if not publications:
            return {'status': 'empty'}

        try:
            sorted_pubs = sorted(publications, key=lambda p: p.get('year', 0))
            years = [p.get('year', 0) for p in sorted_pubs]

            year_entity_counts = defaultdict(lambda: defaultdict(int))
            entity_all_time = defaultdict(set)

            for pub in sorted_pubs:
                year = pub.get('year', 0)
                for entity_id in (pub.get('entities') or []):
                    if self.graph.has_node(entity_id):
                        etype = self.graph.nodes[entity_id].get('type', 'unknown')
                        year_entity_counts[year][etype] += 1
                        entity_all_time[entity_id].add(year)

            emerging_entities = []
            for entity_id, pub_years in entity_all_time.items():
                if len(pub_years) >= 2:
                    data = self.graph.nodes[entity_id]
                    emerging_entities.append({
                        'name': data.get('text', ''),
                        'type': data.get('type', ''),
                        'years': sorted(pub_years),
                        'duration': max(pub_years) - min(pub_years)
                    })

            emerging_entities.sort(key=lambda e: e['duration'], reverse=True)

            return {
                'time_span': {
                    'start': min(years),
                    'end': max(years),
                    'years_covered': len(set(years))
                },
                'entity_type_evolution': {
                    str(year): dict(counts)
                    for year, counts in year_entity_counts.items()
                },
                'emerging_research': emerging_entities[:10]
            }
        except Exception as e:
            logger.error(f"Error in analyze_temporal_evolution: {e}")
            return {'status': 'error', 'message': str(e)}

    def analyze_impact_strength(self, entity_id: str) -> dict:
        """Analyze the impact strength of a specific entity."""
        try:
            if not self.graph.has_node(entity_id):
                return {'status': 'error', 'message': 'Entity not found'}

            # Get entity info
            entity_data = self.graph.nodes[entity_id]
            entity_text = entity_data.get('text', '')
            entity_type = entity_data.get('type', '')

            # Calculate influence scores
            in_degree = self.graph.in_degree(entity_id)
            out_degree = self.graph.out_degree(entity_id)

            # Get influence sources (entities that point to this entity)
            influence_sources = [source for source, _ in self.graph.in_edges(entity_id)]
            source_texts = [self.graph.nodes[src].get('text', '') for src in influence_sources]

            # Get influenced targets (entities this entity points to)
            influenced_targets = [target for _, target in self.graph.out_edges(entity_id)]
            target_texts = [self.graph.nodes[tgt].get('text', '') for tgt in influenced_targets]

            # Overall impact score (weighted combination)
            impact_score = (in_degree * 0.6 + out_degree * 0.4) / max(1, self.graph.number_of_nodes())

            # Normalize score between 0 and 1
            impact_score = min(1.0, max(0.0, impact_score))

            return {
                'entity_id': entity_id,
                'entity_text': entity_text,
                'entity_type': entity_type,
                'impact_score': round(impact_score, 4),
                'influence_sources': source_texts,
                'influenced_targets': target_texts,
                'total_connections': in_degree + out_degree,
                'in_degree': in_degree,
                'out_degree': out_degree,
                'description': f"Entity '{entity_text}' has impact score of {impact_score:.4f}"
            }
        except Exception as e:
            logger.error(f"Error in analyze_impact_strength: {e}")
            return {'status': 'error', 'message': str(e)}

    def identify_key_contributors(self, top_k: int = 10) -> list[dict]:
        """Identify key contributors based on their network position and connectivity."""
        try:
            if self.graph.number_of_nodes() == 0:
                return []

            # Calculate various centrality measures
            try:
                pagerank_scores = nx.pagerank(self.graph)
            except Exception:
                pagerank_scores = nx.degree_centrality(self.graph)

            try:
                betweenness_scores = nx.betweenness_centrality(self.graph)
            except Exception:
                betweenness_scores = defaultdict(float)

            try:
                closeness_scores = nx.closeness_centrality(self.graph)
            except Exception:
                closeness_scores = defaultdict(float)

            contributors = []
            for node_id in self.graph.nodes():
                node_data = self.graph.nodes[node_id]
                node_text = node_data.get('text', '')
                node_type = node_data.get('type', '')

                # Get degrees
                in_deg = self.graph.in_degree(node_id)
                out_deg = self.graph.out_degree(node_id)
                total_deg = in_deg + out_deg

                # Get centrality scores
                pr_score = pagerank_scores.get(node_id, 0)
                bt_score = betweenness_scores.get(node_id, 0)
                cl_score = closeness_scores.get(node_id, 0)

                # Combined score (normalized)
                combined_score = (
                    pr_score * 0.4 +
                    bt_score * 0.3 +
                    cl_score * 0.3
                )

                contributors.append({
                    'entity_id': node_id,
                    'entity_text': node_text,
                    'entity_type': node_type,
                    'combined_score': round(combined_score, 4),
                    'in_degree': in_deg,
                    'out_degree': out_deg,
                    'total_degree': total_deg,
                    'pagerank': round(pr_score, 4),
                    'betweenness': round(bt_score, 4),
                    'closeness': round(cl_score, 4)
                })

            # Sort by combined score
            contributors.sort(key=lambda x: x['combined_score'], reverse=True)
            return contributors[:top_k]
        except Exception as e:
            logger.error(f"Error in identify_key_contributors: {e}")
            return []
