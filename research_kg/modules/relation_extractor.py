import logging
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .entity_extractor import Entity

logger = logging.getLogger(__name__)


class RelationType(Enum):
    """关系类型词表。

    前 14 项（USES ~ TESTS）已在 :meth:`RelationExtractor._initialize_patterns`
    中实现中英文抽取模式，并被视觉化模块的配色 / 线型表覆盖。

    后 4 项（ASSIGNS / PREDICTS / ANALYZES / OPTIMIZES）为**预留类型**，
    尚未提供内置模式；如需使用，请通过
    :meth:`RelationExtractor.add_custom_relation_type` 自行注册。
    """

    # ---- 已实现抽取模式 ----
    USES = "uses"
    COMPARES = "compares"
    EVALUATES = "evaluates"
    EXTENDS = "extends"
    PROPOSES = "proposes"
    COMBINES = "combines"
    REPLACES = "replaces"
    ENABLES = "enables"
    IMPROVES = "improves"
    ACHIEVES = "achieves"
    INTRODUCES = "introduces"
    DEVELOPS = "develops"
    TRAINS = "trains"
    TESTS = "tests"

    # ---- 预留类型（暂无内置模式） ----
    ASSIGNS = "assigns"
    PREDICTS = "predicts"
    ANALYZES = "analyzes"
    OPTIMIZES = "optimizes"


@dataclass
class Relation:
    entity_id: str
    source_entity_id: str
    target_entity_id: str
    relation_type: str
    confidence: float
    context: str
    source_document: str
    attributes: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'entity_id': self.entity_id,
            'source_entity_id': self.source_entity_id,
            'target_entity_id': self.target_entity_id,
            'relation_type': self.relation_type,
            'confidence': self.confidence,
            'context': self.context,
            'source_document': self.source_document,
            'attributes': self.attributes
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Relation':
        return cls(
            entity_id=data['entity_id'],
            source_entity_id=data['source_entity_id'],
            target_entity_id=data['target_entity_id'],
            relation_type=data['relation_type'],
            confidence=data['confidence'],
            context=data['context'],
            source_document=data['source_document'],
            attributes=data.get('attributes', {})
        )


class RelationExtractor:
    CONFIDENCE_PATTERN = 0.7
    CONFIDENCE_DEPENDENCY = 0.6
    CONFIDENCE_AUTO_ENTITY = 0.3
    CONFIDENCE_CONTEXT = 0.55
    CONFIDENCE_SYNTACTIC = 0.65

    def __init__(self, model_name: str = "en_core_web_sm"):
        self.nlp = None
        self.model_name = model_name
        self.relation_patterns = self._initialize_patterns()
        self.dependency_rules = self._initialize_dependency_rules()
        self._load_spacy_model()
        self.custom_relation_types = {}

    def _load_spacy_model(self):
        try:
            import spacy
            self.nlp = spacy.load(self.model_name)
        except (ImportError, OSError):
            logger.warning(f"Could not load spaCy model {self.model_name}, falling back to rule-based extraction")
            self.nlp = None

    def _initialize_patterns(self) -> dict[str, list[re.Pattern]]:
        return {
            RelationType.USES.value: [
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:uses?|using|utilizes?)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:based\s+on|built\s+(?:upon|on))\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:employs?|applies?|implements?)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                # 中文关系：使用/基于/采用
                re.compile(r'([一-鿿\w\s]+?)(?:使用|利用|采用|基于|建立在|依赖于|依赖于)([一-鿿\w\s]+)'),
            ],
            RelationType.COMPARES.value: [
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:compares?|compared\s+(?:to|with))\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:outperforms?)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:better\s+than|superior\s+to)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:evaluates?|measures?|assesses?)\s+(?:against|with)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                # 中文关系：比较/优于/胜于
                re.compile(r'([一-鿿\w\s]+?)(?:比较|对比|优于|优于|胜于|超过|相|相于)([一-鿿\w\s]+)'),
            ],
            RelationType.EVALUATES.value: [
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:evaluates?|tested\s+on|benchmarked\s+on)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:achieves?|reaches?)\s+(\d+(?:\.\d+)?)\s+(?:on|with)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:achieves?|reaches?|obtains?)\s+(?:an?\s+)?(\d+(?:\.\d+)?%?)\s*(?:on|with)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                # 中文关系：评估/测试/验证于
                re.compile(r'([一-鿿\w\s]+?)(?:评估|测试|验证|评测|基准测试)(?:于|\s*在\s*)([一-鿿\w\s]+)'),
            ],
            RelationType.EXTENDS.value: [
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:extends?|builds?\s+(?:upon|on)|improves?\s+upon)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:based\s+on|derived\s+from)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:enhances?|improves?|refines?)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                # 中文关系：扩展/改进/增强
                re.compile(r'([一-鿿\w\s]+?)(?:扩展|改进|增强|改良|优化|完善)([一-鿿\w\s]+)'),
            ],
            RelationType.PROPOSES.value: [
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:proposes?|introduces?|presents?)\s+(?:a\s+)?(?:novel\s+)?(\w+(?:\s+\w+)?)', re.IGNORECASE),
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:suggests?|advocates?|recommends?)\s+(?:a\s+)?(\w+(?:\s+\w+)?)', re.IGNORECASE),
                # 中文关系：提出/引入/建议
                re.compile(r'([一-鿿\w\s]+?)(?:提出|引入|建议|推荐|倡导)([一-鿿\w\s]+)'),
            ],
            RelationType.COMBINES.value: [
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:combines?|integrates?|merges?)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:joins?|unites?|associates?)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                # 中文关系：结合/融合/集成
                re.compile(r'([一-鿿\w\s]+?)(?:结合|融合|集成|合并|联合)([一-鿿\w\s]+)'),
            ],
            RelationType.REPLACES.value: [
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:replaces?|supplants?|substitutes?|replaces?)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:supersedes?|outperforms?)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                # 中文关系：替代/取代
                re.compile(r'([一-鿿\w\s]+?)(?:替代|取代|代替|替换)([一-鿿\w\s]+)'),
            ],
            RelationType.ENABLES.value: [
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:enables?|allows?|facilitates?)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:makes\s+possible|enables\s+the\s+use\s+of)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                # 中文关系：使能/允许/促进
                re.compile(r'([一-鿿\w\s]+?)(?:使得|使|允许|促进|促成)([一-鿿\w\s]+)'),
            ],
            RelationType.IMPROVES.value: [
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:improves?|enhances?|boosts?|increases?)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:optimizes?|refines?|enhances?)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                # 中文关系：提升/提高/增强
                re.compile(r'([一-鿿\w\s]+?)(?:提升|提高|增强|增加|改善|改善)([一-鿿\w\s]+)'),
            ],
            RelationType.ACHIEVES.value: [
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:achieves?|reaches?|obtains?)\s+(\d+(?:\.\d+)?%?)', re.IGNORECASE),
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:state-of-the-art|SoTA|SOTA)\s+(?:results?|performance)', re.IGNORECASE),
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:outperforms?|surpasses?|exceeds?)\s+(?:the\s+previous\s+best|other\s+methods)', re.IGNORECASE),
                # 中文关系：达到/获得/取得
                re.compile(r'([一-鿿\w\s]+?)(?:达到|获得|取得|实现)(\d+(?:\.\d+)?%?)'),
            ],
            RelationType.INTRODUCES.value: [
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:introduces?|presents?|proposes?|develops?)\s+(?:a\s+)?(?:novel\s+)?(\w+(?:\s+\w+)?)', re.IGNORECASE),
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:first\s+introduces?|initially\s+introduces?|pioneers?)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                # 中文关系：首创/率先引入
                re.compile(r'([一-鿿\w\s]+?)(?:首创|率先引入|率先提出|率先)([一-鿿\w\s]+)'),
            ],
            RelationType.DEVELOPS.value: [
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:develops?|creates?|builds?|constructs?)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:formulates?|designs?|constructs?)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                # 中文关系：开发/构建/设计
                re.compile(r'([一-鿿\w\s]+?)(?:开发|构建|设计|构造|创建)([一-鿿\w\s]+)'),
            ],
            RelationType.TRAINS.value: [
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:trains?|teaches?|learns?|optimizes?)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:optimizes?|fine-tunes?|adjusts?)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                # 中文关系：训练/微调/优化
                re.compile(r'([一-鿿\w\s]+?)(?:训练|微调|调整|优化)([一-鿿\w\s]+)'),
            ],
            RelationType.TESTS.value: [
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:tests?|evaluates?|validates?|assesses?)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                re.compile(r'\b(\w+(?:\s+\w+)?)\s+(?:benchmarks?|evaluates?|measures?)\s+(?:on|with)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE),
                # 中文关系：测试/检验/验证
                re.compile(r'([一-鿿\w\s]+?)(?:测试|检验|验证|校验|评估)([一-鿿\w\s]+)'),
            ],
        }

    def _initialize_dependency_rules(self) -> list[dict]:
        return [
            {'pattern': ['nsubj', 'ROOT', 'dobj'], 'relation_type': RelationType.USES.value, 'description': 'Subject uses object'},
            {'pattern': ['nsubj', 'ROOT', 'prep', 'pobj'], 'relation_type': RelationType.USES.value, 'description': 'Subject uses prepositional object'},
            {'pattern': ['nsubj', 'ROOT', 'dobj', 'prep', 'pobj'], 'relation_type': RelationType.EVALUATES.value, 'description': 'Subject evaluates on object'},
            {'pattern': ['nsubj', 'ROOT', 'xcomp', 'dobj'], 'relation_type': RelationType.PROPOSES.value, 'description': 'Subject proposes object'},
            {'pattern': ['nsubj', 'ROOT', 'advmod', 'dobj'], 'relation_type': RelationType.IMPROVES.value, 'description': 'Subject improves object'},
            {'pattern': ['nsubj', 'ROOT', 'conj', 'dobj'], 'relation_type': RelationType.COMBINES.value, 'description': 'Subject combines objects'},
        ]

    def add_custom_relation_type(self, relation_type: str, patterns: list[str]):
        """Add a custom relation type with regex patterns."""
        self.custom_relation_types[relation_type] = [re.compile(p, re.IGNORECASE) for p in patterns]
        self.relation_patterns[relation_type] = [re.compile(p, re.IGNORECASE) for p in patterns]

    def extract_relations(self, text: str, entities: list, min_confidence: float = 0.5) -> list[Relation]:
        if not text or not text.strip() or not entities:
            return []

        relations = self._extract_pattern_relations(text, entities)
        relations.extend(self._extract_custom_relations(text, entities))

        if self.nlp:
            relations.extend(self._extract_dependency_relations(text, entities))
            relations.extend(self._extract_syntactic_relations(text, entities))

        relations = self._deduplicate_relations(relations)
        return [r for r in relations if r.confidence >= min_confidence]

    def _extract_pattern_relations(self, text: str, entities: list) -> list[Relation]:
        relations = []
        entity_texts = {e.text.lower(): e.entity_id for e in entities}
        temp_entity_ids = {}

        for relation_type, patterns in self.relation_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    groups = match.groups()
                    if len(groups) < 2:
                        continue

                    context = text[max(0, match.start() - 50):min(len(text), match.end() + 50)]
                    source_text_raw = groups[0].lower()
                    target_text_raw = groups[1].lower()

                    source_id = entity_texts.get(source_text_raw)
                    target_id = entity_texts.get(target_text_raw)

                    # Create temporary entities if needed
                    if source_id is None:
                        if source_text_raw not in temp_entity_ids:
                            new_id = str(uuid.uuid4())
                            temp_entity_ids[source_text_raw] = new_id
                            entities.append(Entity(
                                entity_id=new_id, text=groups[0], type='unknown',
                                start_pos=0, end_pos=0, confidence=self.CONFIDENCE_AUTO_ENTITY,
                                source_document='', attributes={'auto_created': True, 'original_text': groups[0]}
                            ))
                        source_id = temp_entity_ids[source_text_raw]

                    if target_id is None:
                        if target_text_raw not in temp_entity_ids:
                            new_id = str(uuid.uuid4())
                            temp_entity_ids[target_text_raw] = new_id
                            entities.append(Entity(
                                entity_id=new_id, text=groups[1], type='unknown',
                                start_pos=0, end_pos=0, confidence=self.CONFIDENCE_AUTO_ENTITY,
                                source_document='', attributes={'auto_created': True, 'original_text': groups[1]}
                            ))
                        target_id = temp_entity_ids[target_text_raw]

                    if source_id and target_id and source_id != target_id:
                        relations.append(Relation(
                            entity_id=str(uuid.uuid4()),
                            source_entity_id=source_id,
                            target_entity_id=target_id,
                            relation_type=relation_type,
                            confidence=self.CONFIDENCE_PATTERN,
                            context=context,
                            source_document='',
                            attributes={'source': 'pattern', 'match_text': match.group(0), 'groups': groups}
                        ))

        return relations

    def _extract_custom_relations(self, text: str, entities: list) -> list[Relation]:
        """Extract relations based on custom patterns."""
        relations = []
        entity_texts = {e.text.lower(): e.entity_id for e in entities}

        for relation_type, patterns in self.custom_relation_types.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    groups = match.groups()
                    if len(groups) < 2:
                        continue

                    context = text[max(0, match.start() - 50):min(len(text), match.end() + 50)]
                    source_text_raw = groups[0].lower()
                    target_text_raw = groups[1].lower()

                    source_id = entity_texts.get(source_text_raw)
                    target_id = entity_texts.get(target_text_raw)

                    if source_id and target_id and source_id != target_id:
                        relations.append(Relation(
                            entity_id=str(uuid.uuid4()),
                            source_entity_id=source_id,
                            target_entity_id=target_id,
                            relation_type=relation_type,
                            confidence=self.CONFIDENCE_CONTEXT,
                            context=context,
                            source_document='',
                            attributes={'source': 'custom_pattern', 'match_text': match.group(0), 'pattern': pattern.pattern}
                        ))

        return relations

    def _extract_dependency_relations(self, text: str, entities: list) -> list[Relation]:
        relations = []
        if not self.nlp:
            return relations

        try:
            doc = self.nlp(text)
            entity_texts = {e.text.lower(): e.entity_id for e in entities}

            for token in doc:
                for rule in self.dependency_rules:
                    if self._match_dependency_pattern(token, rule['pattern']):
                        source_text = token.text.lower()
                        target_text = self._find_target_entity(token, rule['pattern'], entity_texts)

                        if source_text in entity_texts and target_text in entity_texts:
                            source_id = entity_texts[source_text]
                            target_id = entity_texts[target_text]

                            if source_id != target_id:
                                context = text[max(0, token.idx - 50):min(len(text), token.idx + len(token.text) + 50)]
                                relations.append(Relation(
                                    entity_id=str(uuid.uuid4()),
                                    source_entity_id=source_id,
                                    target_entity_id=target_id,
                                    relation_type=rule['relation_type'],
                                    confidence=self.CONFIDENCE_DEPENDENCY,
                                    context=context,
                                    source_document='',
                                    attributes={'source': 'dependency', 'rule': rule['description'], 'token': token.text}
                                ))
        except Exception as e:
            logger.warning(f"Error in dependency relation extraction: {e}")

        return relations

    def _extract_syntactic_relations(self, text: str, entities: list) -> list[Relation]:
        """Extract additional relations using advanced syntactic analysis."""
        relations = []
        if not self.nlp:
            return relations

        try:
            doc = self.nlp(text)
            entity_texts = {e.text.lower(): e.entity_id for e in entities}

            # Look for more complex patterns
            for token in doc:
                # Look for passive voice constructions indicating relationships
                if token.dep_ == 'nsubjpass' and token.head.pos_ == 'VERB':
                    # Subject of passive construction may be related to the verb
                    source_text = token.text.lower()
                    if source_text in entity_texts:
                        source_id = entity_texts[source_text]

                        # Look for objects of the main verb
                        for child in token.head.children:
                            if child.dep_ == 'dobj':
                                target_text = child.text.lower()
                                if target_text in entity_texts and target_text != source_text:
                                    target_id = entity_texts[target_text]
                                    relations.append(Relation(
                                        entity_id=str(uuid.uuid4()),
                                        source_entity_id=source_id,
                                        target_entity_id=target_id,
                                        relation_type=RelationType.ASSIGNS.value,
                                        confidence=self.CONFIDENCE_SYNTACTIC,
                                        context=text[max(0, token.idx - 30):min(len(text), token.idx + len(token.text) + 30)],
                                        source_document='',
                                        attributes={'source': 'syntactic', 'type': 'passive_voice'}
                                    ))

                # Look for "designed for" / "proposed for" constructions
                elif token.dep_ == 'prep' and token.text.lower() == 'for':
                    # Get the parent of prep
                    parent = token.head
                    if parent.pos_ == 'VERB':
                        # Find subject of the verb
                        source_text = ''
                        for child in parent.children:
                            if child.dep_ == 'nsubj':
                                source_text = child.text.lower()
                                break

                        if source_text and source_text in entity_texts:
                            source_id = entity_texts[source_text]
                            # Get the object of 'for'
                            for child in token.children:
                                if child.dep_ == 'pobj':
                                    target_text = child.text.lower()
                                    if target_text in entity_texts and target_text != source_text:
                                        target_id = entity_texts[target_text]
                                        relations.append(Relation(
                                            entity_id=str(uuid.uuid4()),
                                            source_entity_id=source_id,
                                            target_entity_id=target_id,
                                            relation_type=RelationType.PROPOSES.value,
                                            confidence=self.CONFIDENCE_SYNTACTIC,
                                            context=text[max(0, token.idx - 30):min(len(text), token.idx + len(token.text) + 30)],
                                            source_document='',
                                            attributes={'source': 'syntactic', 'type': 'designed_for'}
                                        ))
        except Exception as e:
            logger.warning(f"Error in syntactic relation extraction: {e}")

        return relations

    def _match_dependency_pattern(self, token, pattern: list[str]) -> bool:
        if not pattern or token.dep_ != pattern[0]:
            return False
        if len(pattern) == 1:
            return True
        if pattern[1] == 'ROOT':
            return True
        for child in token.children:
            if self._match_dependency_pattern_recursive(child, pattern, 1):
                return True
        return False

    def _match_dependency_pattern_recursive(self, token, pattern: list[str], index: int) -> bool:
        if index >= len(pattern):
            return True
        if token.dep_ != pattern[index]:
            return False
        if index == len(pattern) - 1:
            return True
        for child in token.children:
            if self._match_dependency_pattern_recursive(child, pattern, index + 1):
                return True
        return False

    def _find_target_entity(self, token, pattern: list[str], entity_texts: dict[str, str]) -> Optional[str]:
        target_dep = pattern[-1]
        for child in token.children:
            if child.dep_ == target_dep and child.text.lower() in entity_texts:
                return child.text.lower()
        for child in token.children:
            for grandchild in child.children:
                if grandchild.dep_ == target_dep and grandchild.text.lower() in entity_texts:
                    return grandchild.text.lower()
        return None

    def _deduplicate_relations(self, relations: list[Relation]) -> list[Relation]:
        seen = {}
        for r in relations:
            key = (r.source_entity_id, r.target_entity_id, r.relation_type)
            if key not in seen or r.confidence > seen[key].confidence:
                seen[key] = r
        return list(seen.values())

    def extract_from_documents(self, documents: list[str], entities_list: list[list]) -> list[list[Relation]]:
        results = []
        for i, (doc_text, entities) in enumerate(zip(documents, entities_list)):
            relations = self.extract_relations(doc_text, entities)
            for relation in relations:
                relation.source_document = f"doc_{i}"
            results.append(relations)
        return results

    def get_relation_statistics(self, relations: list[Relation]) -> dict:
        stats = {
            'total_relations': len(relations),
            'by_type': defaultdict(int),
            'avg_confidence': 0.0,
            'high_confidence_count': 0
        }
        if not relations:
            return stats
        total_confidence = sum(r.confidence for r in relations)
        stats['avg_confidence'] = total_confidence / len(relations)
        for relation in relations:
            stats['by_type'][relation.relation_type] += 1
            if relation.confidence >= 0.8:
                stats['high_confidence_count'] += 1
        stats['by_type'] = dict(stats['by_type'])
        return stats

    def build_relation_vocabulary(self, relations: list[Relation]) -> dict[str, list[tuple[str, str]]]:
        vocabulary = defaultdict(list)
        for relation in relations:
            vocabulary[relation.relation_type].append((relation.source_entity_id, relation.target_entity_id))
        for rtype in vocabulary:
            vocabulary[rtype] = list(set(vocabulary[rtype]))
        return dict(vocabulary)
