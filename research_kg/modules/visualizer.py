import logging
import uuid
from collections import defaultdict

import matplotlib

# 必须在导入 pyplot 之前切换后端，否则在服务器 / Docker / CI 等无显示环境下会报错
matplotlib.use('Agg')

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib import font_manager

from .html_io import write_pyvis_html

logger = logging.getLogger(__name__)


def _setup_chinese_font():
    font_candidates = [
        'Microsoft YaHei',
        'SimHei',
        'SimSun',
        'KaiTi',
        'FangSong',
        'Arial Unicode MS',
        'PingFang SC',
        'Noto Sans CJK SC',
        'WenQuanYi Micro Hei',
    ]
    available_fonts = {f.name for f in font_manager.fontManager.ttflist}
    for font in font_candidates:
        if font in available_fonts:
            plt.rcParams['font.sans-serif'] = [font]
            plt.rcParams['axes.unicode_minus'] = False
            return font
    return None


class GraphVisualizer:
    def __init__(self, figsize: tuple[int, int] = (16, 12), dpi: int = 150):
        self.figsize = figsize
        self.dpi = dpi
        self.chinese_font = _setup_chinese_font()
        self.layout_type = 'spring'
        self.entity_colors = {
            'method': '#FF6B6B', 'dataset': '#4ECDC4', 'model': '#45B7D1',
            'task': '#96CEB4', 'metric': '#FFEAA7', 'material': '#DDA0DD',
            'tool': '#98D8C8', 'theory': '#FFD93D', 'measurement': '#F7DC6F',
            'software': '#85C1E9', 'author': '#FF9AA2', 'institution': '#B5EAD7',
            'unknown': '#BDC3C7'
        }
        self.relation_styles = {
            'uses': 'solid', 'compares': 'dashed', 'evaluates': 'dotted',
            'extends': 'dashdot', 'proposes': 'solid', 'combines': 'dashed',
            'replaces': 'dotted', 'enables': 'dashdot', 'improves': 'solid',
            'achieves': 'dashed', 'introduces': 'solid', 'develops': 'dashed',
            'trains': 'dotted', 'tests': 'dashdot'
        }
        self.relation_colors = {
            'uses': '#2C3E50', 'compares': '#E74C3C', 'evaluates': '#3498DB',
            'extends': '#27AE60', 'proposes': '#9B59B6', 'combines': '#1ABC9C',
            'replaces': '#95A5A6', 'enables': '#F39C12', 'improves': '#2ECC71',
            'achieves': '#E67E22', 'introduces': '#8E44AD', 'develops': '#34495E',
            'trains': '#27AE60', 'tests': '#E67E22'
        }

    def set_custom_colors(self, entity_colors: dict[str, str] = None,
                         relation_colors: dict[str, str] = None):
        """Set custom colors for visualization."""
        if entity_colors:
            self.entity_colors.update(entity_colors)
        if relation_colors:
            self.relation_colors.update(relation_colors)

    def set_custom_layout(self, layout_type: str = 'spring'):
        """Set custom layout algorithm."""
        self.layout_type = layout_type

    def visualize_static(self, graph: nx.DiGraph, output_path: str = 'knowledge_graph.png',
                        title: str = 'Research Knowledge Graph', layout_type: str = 'spring'):
        try:
            plt.figure(figsize=self.figsize, dpi=self.dpi)

            # Choose layout algorithm: use parameter first, fall back to instance default
            effective_layout = layout_type if layout_type != 'spring' else self.layout_type
            if effective_layout == 'spring':
                pos = nx.spring_layout(graph, k=2, iterations=50, seed=42)
            elif effective_layout == 'circular':
                pos = nx.circular_layout(graph)
            elif effective_layout == 'shell':
                pos = nx.shell_layout(graph)
            elif effective_layout == 'kamada_kawai':
                pos = nx.kamada_kawai_layout(graph)
            else:
                pos = nx.spring_layout(graph, k=2, iterations=50, seed=42)

            node_colors = []
            node_sizes = []
            for _, data in graph.nodes(data=True):
                etype = data.get('type', 'unknown')
                node_colors.append(self.entity_colors.get(etype, '#BDC3C7'))
                # Size based on text length and confidence
                base_size = 300
                text_length_factor = len(data.get('text', '')) * 2
                confidence_factor = data.get('confidence', 0.5) * 100
                node_sizes.append(max(200, min(2000, base_size + text_length_factor + confidence_factor)))

            edge_colors = []
            edge_styles = []
            edge_widths = []
            for _, _, data in graph.edges(data=True):
                rtype = data.get('relation_type', 'unknown')
                edge_colors.append(self.relation_colors.get(rtype, '#7F8C8D'))
                edge_styles.append(self.relation_styles.get(rtype, 'solid'))
                # Width based on confidence
                confidence = data.get('confidence', 0.5)
                edge_widths.append(max(0.5, min(5.0, 0.5 + confidence * 4.0)))

            # Draw edges
            nx.draw_networkx_edges(graph, pos, edge_color=edge_colors, style=edge_styles,
                                   alpha=0.4, arrows=True, arrowsize=15,
                                   arrowstyle='->', connectionstyle='arc3,rad=0.1',
                                   width=edge_widths)

            # Draw nodes
            nx.draw_networkx_nodes(graph, pos, node_color=node_colors,
                                   node_size=node_sizes, alpha=0.9,
                                   edgecolors='white', linewidths=1.5)

            # Draw labels
            labels = {}
            for n, data in graph.nodes(data=True):
                text = data.get('text', '')
                # Truncate long labels
                if len(text) > 25:
                    labels[n] = text[:22] + '...'
                else:
                    labels[n] = text

            nx.draw_networkx_labels(graph, pos, labels=labels,
                                    font_size=7, font_weight='bold')

            # Create legend
            legend_patches = []
            unique_types = set()
            for _, data in graph.nodes(data=True):
                etype = data.get('type', 'unknown')
                if etype not in unique_types:
                    unique_types.add(etype)
                    color = self.entity_colors.get(etype, '#BDC3C7')
                    legend_patches.append(mpatches.Patch(color=color, label=etype.capitalize()))

            if legend_patches:
                plt.legend(handles=legend_patches, loc='upper left',
                          bbox_to_anchor=(1, 1), title='Entity Types', fontsize=8)

            plt.title(title, fontsize=16, fontweight='bold', pad=20)
            plt.axis('off')
            plt.tight_layout()
            plt.savefig(output_path, bbox_inches='tight', dpi=self.dpi)
            plt.close()
            logger.info(f"Static graph saved to: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error creating static visualization: {e}")
            raise

    def visualize_interactive(self, graph: nx.DiGraph, output_path: str = 'knowledge_graph.html',
                             cdn_resources: str = 'in_line'):
        """生成可交互的 PyVis HTML 图谱。

        Args:
            graph: 待可视化的有向图。
            output_path: 输出 HTML 路径。
            cdn_resources: JS/CSS 的加载方式，取值为 ``'in_line'``（默认，全部内联，
                生成的 HTML 自包含、可离线打开，且不会在工作目录留下 ``lib/`` 文件夹）、
                ``'remote'``（引用 CDN，文件体积最小但需要联网）或
                ``'local'``（把 vis-network 静态资源复制到当前工作目录的 ``lib/`` 下，
                文件可离线使用，但移动 HTML 后相对引用会失效）。

        Returns:
            实际写入的 ``output_path``。
        """
        try:
            from pyvis.network import Network
            net = Network(height='750px', width='100%', directed=True, notebook=False,
                          cdn_resources=cdn_resources)
            net.set_options('''{
              "nodes": {"font": {"size": 12}, "borderWidth": 2},
              "edges": {"font": {"size": 10}, "smooth": {"type": "curvedCW"},
                        "arrows": {"to": {"enabled": true}}},
              "physics": {"barnesHut": {"gravitationalConstant": -3000,
                          "springLength": 200}},
              "interaction": {"hover": true, "tooltipDelay": 200}
            }''')

            for nid, data in graph.nodes(data=True):
                etype = data.get('type', 'unknown')
                text = data.get('text', '')
                # Add more tooltip information
                tooltip_info = f"<b>{text}</b><br>Type: {etype}<br>Conf: {data.get('confidence', 0):.2f}"
                if data.get('source_document'):
                    tooltip_info += f"<br>Source: {data['source_document']}"

                net.add_node(nid, label=text[:15],
                    title=tooltip_info,
                    color=self.entity_colors.get(etype, '#BDC3C7'),
                    size=15 + len(text) * 0.5, group=etype)

            for u, v, data in graph.edges(data=True):
                rtype = data.get('relation_type', 'unknown')
                tooltip_info = f"<b>{rtype}</b><br>Conf: {data.get('confidence', 0):.2f}"
                if data.get('context'):
                    tooltip_info += f"<br>Context: {data['context'][:50]}..."

                net.add_edge(u, v, label=rtype,
                    title=tooltip_info,
                    color=self.relation_colors.get(rtype, '#7F8C8D'),
                    width=0.5 + data.get('confidence', 0) * 2)

            write_pyvis_html(net, output_path)
            logger.info(f"Interactive graph saved to: {output_path}")
            return output_path
        except ImportError:
            logger.warning("pyvis not installed. Falling back to static visualization.")
            return self.visualize_static(graph, output_path.replace('.html', '.png'))

    def visualize_timeline(self, graph: nx.DiGraph, publications: list[dict],
                          output_path: str = 'timeline.html',
                          cdn_resources: str = 'in_line'):
        """按年份生成研究演进时间线（HTML）。

        ``cdn_resources`` 语义同 :meth:`visualize_interactive`。
        """
        try:
            from pyvis.network import Network
            net = Network(height='750px', width='100%', directed=True, notebook=False,
                          cdn_resources=cdn_resources)

            # 实体既可能是图谱节点 ID，也可能只是实体文本（调用方通常只有文本），
            # 因此额外建立 文本 -> 节点 ID 的索引用于兜底解析。
            text_index = {}
            for nid, ndata in graph.nodes(data=True):
                tkey = (ndata.get('text') or '').strip().lower()
                if tkey:
                    text_index.setdefault(tkey, nid)

            def resolve_entity(ref):
                if graph.has_node(ref):
                    return ref
                return text_index.get(str(ref).strip().lower())

            year_groups = defaultdict(list)
            for pub in publications:
                year_groups[pub.get('year', 0)].append(pub)

            added_entity_nodes = set()
            unresolved = 0

            for idx, year in enumerate(sorted(year_groups.keys())):
                for pub in year_groups[year]:
                    pub_id_str = f"pub_{pub.get('id', uuid.uuid4().hex[:8])}"
                    net.add_node(pub_id_str,
                        label=f"{pub.get('title', '')[:30]} ({year})",
                        title=f"<b>{pub.get('title', '')}</b><br>Year: {year}",
                        color='#3498DB', size=20, level=idx)

                    for ref in (pub.get('entities') or []):
                        entity_id = resolve_entity(ref)
                        if entity_id is None:
                            # 图谱中找不到该实体：跳过连边，否则 pyvis 会直接断言失败
                            unresolved += 1
                            continue

                        if entity_id not in added_entity_nodes:
                            ed = graph.nodes[entity_id]
                            net.add_node(entity_id,
                                label=ed.get('text', '')[:20],
                                title=f"<b>{ed.get('text', '')}</b><br>Type: {ed.get('type', '')}",
                                color=self.entity_colors.get(ed.get('type', ''), '#BDC3C7'),
                                size=15)
                            added_entity_nodes.add(entity_id)

                        net.add_edge(pub_id_str, entity_id, color='#95A5A6', width=1)

            if unresolved:
                logger.info(
                    f"Skipped {unresolved} publication entity reference(s) "
                    "that do not exist in the graph"
                )

            write_pyvis_html(net, output_path)
            logger.info(f"Timeline graph saved to: {output_path}")
            return output_path
        except ImportError:
            logger.warning("pyvis not installed. Timeline visualization requires pyvis.")
            return None

    def visualize_entity_distribution(self, graph: nx.DiGraph, output_path: str = 'entity_distribution.png'):
        try:
            entity_types = defaultdict(int)
            for _, data in graph.nodes(data=True):
                entity_types[data.get('type', 'unknown')] += 1

            if not entity_types:
                logger.warning("No entities found in graph for distribution visualization.")
                return None

            plt.figure(figsize=(10, 6), dpi=self.dpi)
            types = list(entity_types.keys())
            counts = list(entity_types.values())
            colors = [self.entity_colors.get(t, '#BDC3C7') for t in types]

            bars = plt.bar(types, counts, color=colors, edgecolor='white', linewidth=1.5)
            for bar, count in zip(bars, counts):
                plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                        str(count), ha='center', va='bottom', fontweight='bold')

            plt.title('Entity Type Distribution', fontsize=14, fontweight='bold')
            plt.xlabel('Entity Type', fontsize=12)
            plt.ylabel('Count', fontsize=12)
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig(output_path, bbox_inches='tight', dpi=self.dpi)
            plt.close()
            logger.info(f"Entity distribution chart saved to: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error creating entity distribution chart: {e}")
            raise

    def visualize_relation_network(self, graph: nx.DiGraph, entity_type: str = None,
                                  output_path: str = 'relation_network.png'):
        try:
            if entity_type:
                target = {n for n, d in graph.nodes(data=True) if d.get('type') == entity_type}
                subgraph_nodes = set(target)
                for node in target:
                    subgraph_nodes.update(graph.predecessors(node))
                    subgraph_nodes.update(graph.successors(node))
                subgraph = graph.subgraph(subgraph_nodes)
            else:
                subgraph = graph

            title = f'Relation Network{f" Focus: {entity_type}" if entity_type else ""}'
            return self.visualize_static(subgraph, output_path, title=title)
        except Exception as e:
            logger.error(f"Error creating relation network visualization: {e}")
            raise

    def visualize_subgraph(self, graph: nx.DiGraph, node_ids: list[str],
                          output_path: str = 'subgraph.png', title: str = 'Subgraph Visualization'):
        """Visualize a specific subgraph defined by node IDs."""
        try:
            if not node_ids:
                logger.warning("No node IDs provided for subgraph visualization")
                return None

            # Create subgraph
            subgraph = graph.subgraph(node_ids)

            return self.visualize_static(subgraph, output_path, title)
        except Exception as e:
            logger.error(f"Error creating subgraph visualization: {e}")
            raise

    def visualize_graph_summary(self, graph: nx.DiGraph, output_path: str = 'graph_summary.png'):
        """Create a summary visualization showing key graph statistics."""
        try:
            # Get basic stats
            stats = {
                'Nodes': graph.number_of_nodes(),
                'Edges': graph.number_of_edges(),
                'Density': nx.density(graph),
                'Connected Components': nx.number_weakly_connected_components(graph)
            }

            plt.figure(figsize=(12, 8), dpi=self.dpi)

            # Plot 1: Node distribution by type
            ax1 = plt.subplot(2, 2, 1)
            entity_types = defaultdict(int)
            for _, data in graph.nodes(data=True):
                entity_types[data.get('type', 'unknown')] += 1

            types = list(entity_types.keys())
            counts = list(entity_types.values())
            colors = [self.entity_colors.get(t, '#BDC3C7') for t in types]

            ax1.bar(range(len(types)), counts, color=colors)
            ax1.set_title('Entity Distribution')
            ax1.set_xlabel('Entity Types')
            ax1.set_ylabel('Count')
            ax1.set_xticks(range(len(types)))
            ax1.set_xticklabels(types, rotation=45, ha='right')

            # Plot 2: Edge distribution by type
            ax2 = plt.subplot(2, 2, 2)
            relation_types = defaultdict(int)
            for _, _, data in graph.edges(data=True):
                relation_types[data.get('relation_type', 'unknown')] += 1

            if relation_types:
                rtypes = list(relation_types.keys())
                rcounts = list(relation_types.values())
                rcolors = [self.relation_colors.get(t, '#7F8C8D') for t in rtypes]

                ax2.bar(range(len(rtypes)), rcounts, color=rcolors)
                ax2.set_title('Relation Distribution')
                ax2.set_xlabel('Relation Types')
                ax2.set_ylabel('Count')
                ax2.set_xticks(range(len(rtypes)))
                ax2.set_xticklabels(rtypes, rotation=45, ha='right')
            else:
                ax2.set_title('No Relations Found')

            # Plot 3: Basic statistics text
            ax3 = plt.subplot(2, 2, 3)
            ax3.axis('off')
            ax3.set_title('Graph Statistics')
            stat_text = '\n'.join([f'{k}: {v}' for k, v in stats.items()])
            ax3.text(0.1, 0.5, stat_text, fontsize=10, verticalalignment='center')

            # Plot 4: Layout visualization
            ax4 = plt.subplot(2, 2, 4)
            pos = nx.spring_layout(graph, k=1, iterations=50, seed=42)
            node_colors = [self.entity_colors.get(graph.nodes[n].get('type', 'unknown'), '#BDC3C7')
                          for n in graph.nodes()]
            nx.draw_networkx_nodes(graph, pos, node_color=node_colors, ax=ax4,
                                 node_size=200, alpha=0.7)
            ax4.set_title('Graph Layout')
            ax4.axis('off')

            plt.tight_layout()
            plt.savefig(output_path, bbox_inches='tight', dpi=self.dpi)
            plt.close()
            logger.info(f"Graph summary visualization saved to: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error creating graph summary visualization: {e}")
            raise
