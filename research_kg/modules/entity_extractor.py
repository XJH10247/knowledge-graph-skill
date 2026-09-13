import logging
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class EntityType(Enum):
    METHOD = "method"
    DATASET = "dataset"
    MODEL = "model"
    TASK = "task"
    METRIC = "metric"
    MATERIAL = "material"
    TOOL = "tool"
    THEORY = "theory"
    MEASUREMENT = "measurement"
    SOFTWARE = "software"
    AUTHOR = "author"
    INSTITUTION = "institution"


@dataclass
class Entity:
    entity_id: str
    text: str
    type: str
    start_pos: int
    end_pos: int
    confidence: float
    source_document: str
    synonyms: list[str] = field(default_factory=list)
    attributes: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'entity_id': self.entity_id,
            'text': self.text,
            'type': self.type,
            'start_pos': self.start_pos,
            'end_pos': self.end_pos,
            'confidence': self.confidence,
            'source_document': self.source_document,
            'synonyms': self.synonyms,
            'attributes': self.attributes
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Entity':
        return cls(
            entity_id=data['entity_id'],
            text=data['text'],
            type=data['type'],
            start_pos=data['start_pos'],
            end_pos=data['end_pos'],
            confidence=data['confidence'],
            source_document=data['source_document'],
            synonyms=data.get('synonyms', []),
            attributes=data.get('attributes', {})
        )


class EntityExtractor:
    CONFIDENCE_SPACY = 0.8
    CONFIDENCE_PATTERN = 0.7
    CONFIDENCE_KEYWORD = 0.6
    CONFIDENCE_ACRONYM = 0.65
    CONFIDENCE_ACRONYM_DEFAULT = 0.45
    CONFIDENCE_NOUN_PHRASE = 0.5
    CONFIDENCE_REGEX = 0.55
    CONFIDENCE_NAME = 0.75
    CONFIDENCE_AUTHOR = 0.7

    def __init__(self, model_name: str = "en_core_web_sm"):
        self.nlp = None
        self.model_name = model_name
        self.entity_patterns = self._initialize_patterns()
        self.entity_keywords = self._initialize_keywords()
        self._keyword_patterns = self._precompile_keyword_patterns()
        self._acronym_pattern = re.compile(r'\b[A-Z][A-Z0-9]{1,5}\b')
        self._noun_phrase_pattern = re.compile(r'\b([A-Z][a-z]+(?:\s+[a-z]+){0,3})\s+(?:is|are|was|were|has|have|uses|used|achieves)\b')
        # 支持中英文标点分句（。！？及英文 .!?）
        self._sentence_delimiter = re.compile(r'[。！？!?\.]+')
        self._name_pattern = re.compile(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b')
        self._author_pattern = re.compile(r'\b[A-Z][a-z]+,\s*[A-Z]\.')
        self._load_spacy_model()
        self.custom_entity_types = {}

    def _load_spacy_model(self):
        # 优先加载用户指定模型；若失败，依次尝试英文/中文备选模型，最后回退到纯规则抽取
        candidates = [self.model_name]
        if self.model_name.startswith('en'):
            candidates.append('zh_core_web_sm')
        elif self.model_name.startswith('zh'):
            candidates.append('en_core_web_sm')
        seen = set()
        for name in candidates:
            if not name or name in seen:
                continue
            seen.add(name)
            try:
                import spacy
                self.nlp = spacy.load(name)
                self.model_name = name
                return
            except (ImportError, OSError):
                continue
        logger.warning(
            f"Could not load any spaCy model (tried {candidates}), "
            "falling back to rule-based extraction"
        )
        self.nlp = None

    def _initialize_patterns(self) -> dict[str, list[re.Pattern]]:
        return {
            EntityType.METHOD.value: [
                re.compile(r'\b(?:method|approach|technique|algorithm|procedure|strategy|framework|process)\b', re.IGNORECASE),
                re.compile(r'\b(?:training|inference|optimization|regularization|normalization|fine-tuning|pre-training|transfer learning)\b', re.IGNORECASE),
                re.compile(r'\b(?:backpropagation|gradient descent|cross-validation|ensemble|augmentation)\b', re.IGNORECASE),
                # 中文方法类实体
                re.compile(r'(?:方法|算法|技术|策略|框架|流程|训练|推理|优化|正则化|归一化|微调|预训练|迁移学习|反向传播|梯度下降|交叉验证|数据增强|随机裁剪|残差连接|注意力机制)'),
            ],
            EntityType.DATASET.value: [
                re.compile(r'\b(?:dataset|corpus|collection|data\s+set|benchmark|benchmarking)\b', re.IGNORECASE),
                re.compile(r'\b(?:ImageNet|COCO|SQuAD|GLUE|MNLI|WikiText|CoNLL|UD|FB15K|WN18)\b', re.IGNORECASE),
                # 中文数据集类实体
                re.compile(r'(?:数据集|语料库|语料|基准|基准数据集|训练集|测试集|验证集)'),
            ],
            EntityType.MODEL.value: [
                re.compile(r'\b(?:model|architecture|network|framework|system|module)\b', re.IGNORECASE),
                re.compile(r'\b(?:BERT|GPT|Transformer|ResNet|LSTM|GRU|CNN|GCN|GAT|BERTopic)\b', re.IGNORECASE),
                re.compile(r'\b(?:language model|vision model|graph model|neural network)\b', re.IGNORECASE),
                # 中文模型类实体
                re.compile(r'(?:模型|网络|架构|框架|模块|神经网络|语言模型|卷积神经网络|图神经网络|残差网络)'),
            ],
            EntityType.TASK.value: [
                re.compile(r'\b(?:task|problem|challenge|objective|goal|application)\b', re.IGNORECASE),
                re.compile(r'\b(?:classification|detection|segmentation|generation|translation|retrieval)\b', re.IGNORECASE),
                re.compile(r'\b(?:regression|clustering|anomaly detection|recommendation)\b', re.IGNORECASE),
                # 中文任务类实体
                re.compile(r'(?:任务|问题|挑战|目标|应用|分类|检测|分割|生成|翻译|检索|回归|聚类|异常检测|推荐|节点分类|链接预测|图分类|图像分类|文本生成)'),
            ],
            EntityType.METRIC.value: [
                re.compile(r'\b(?:metric|measure|score|evaluation|accuracy|precision|recall|f1|auc|bleu|rouge|em|f1-score)\b', re.IGNORECASE),
                re.compile(r'\b(?:loss|cost|performance|efficiency|robustness|generalization)\b', re.IGNORECASE),
                # 中文指标类实体
                re.compile(r'(?:指标|度量|评分|准确率|精确率|召回率|精确度|F1|损失|代价|性能|效率|鲁棒性|泛化|评价指标)'),
            ],
            EntityType.MATERIAL.value: [
                re.compile(r'\b(?:material|sample|substrate|compound|solution|reagent|equipment)\b', re.IGNORECASE),
            ],
            EntityType.TOOL.value: [
                re.compile(r'\b(?:tool|software|platform|environment|library|package|api|sdk)\b', re.IGNORECASE),
            ],
            EntityType.THEORY.value: [
                re.compile(r'\b(?:theory|principle|hypothesis|axiom|concept|theorem|lemma|corollary)\b', re.IGNORECASE),
            ],
            EntityType.MEASUREMENT.value: [
                re.compile(r'\b(?:measurement|parameter|variable|dimension|scale|unit)\b', re.IGNORECASE),
            ],
            EntityType.SOFTWARE.value: [
                re.compile(r'\b(?:software|application|program|codebase|toolkit)\b', re.IGNORECASE),
            ],
            EntityType.AUTHOR.value: [
                re.compile(r'\b(?:author|researcher|contributor|creator|developer|scientist|investigator)\b', re.IGNORECASE),
            ],
            EntityType.INSTITUTION.value: [
                re.compile(r'\b(?:institution|university|laboratory|department|institute|center|school|company|organization)\b', re.IGNORECASE),
            ],
        }

    def _initialize_keywords(self) -> dict[str, set[str]]:
        return {
            EntityType.METHOD.value: {
                'training', 'inference', 'optimization', 'regularization', 'normalization',
                'fine-tuning', 'pre-training', 'transfer learning', 'ensemble', 'augmentation',
                'backpropagation', 'gradient descent', 'cross-validation', 'feature extraction',
                'data augmentation', 'early stopping', 'dropout', 'batch normalization',
                '方法', '算法', '技术', '策略', '框架', '流程', '训练', '推理', '优化',
                '正则化', '归一化', '微调', '预训练', '迁移学习', '数据增强', '残差连接', '注意力机制',
            },
            EntityType.DATASET.value: {
                'dataset', 'corpus', 'data', 'collection', 'benchmark', 'benchmarking',
                'training set', 'test set', 'validation set',
                '数据集', '语料库', '语料', '基准', '基准数据集', '训练集', '测试集', '验证集',
            },
            EntityType.MODEL.value: {
                'model', 'network', 'architecture', 'framework', 'system', 'module', 'pipeline',
                '模型', '网络', '架构', '框架', '模块', '神经网络', '语言模型', '卷积神经网络', '图神经网络', '残差网络',
            },
            EntityType.TASK.value: {
                'task', 'problem', 'objective', 'goal', 'challenge', 'application',
                'classification', 'detection', 'segmentation', 'generation',
                '任务', '问题', '挑战', '目标', '应用', '分类', '检测', '分割', '生成', '翻译', '检索',
                '回归', '聚类', '异常检测', '推荐', '节点分类', '链接预测', '图分类', '图像分类', '文本生成',
            },
            EntityType.METRIC.value: {
                'accuracy', 'precision', 'recall', 'f1', 'score', 'measure', 'metric', 'auc', 'bleu', 'rouge',
                'loss', 'cost', 'performance', 'efficiency', 'robustness',
                '准确率', '精确率', '召回率', 'F1', '损失', '代价', '性能', '效率', '鲁棒性', '泛化', '评价指标',
            },
            EntityType.MATERIAL.value: {
                'material', 'sample', 'substrate', 'compound', 'solution', 'reagent', 'equipment',
                '材料', '样本', '试剂', '溶液', '化合物'
            },
            EntityType.TOOL.value: {
                'tool', 'software', 'platform', 'environment', 'library', 'package', 'framework', 'api', 'sdk',
                '工具', '软件', '平台', '环境', '库', '包', '框架', '工具包'
            },
            EntityType.THEORY.value: {
                'theory', 'principle', 'hypothesis', 'method', 'law', 'rule', 'axiom', 'concept',
                '理论', '原理', '假说', '假设', '定律', '规则', '公理', '概念', '定理', '引理'
            },
            EntityType.MEASUREMENT.value: {
                'measurement', 'parameter', 'variable', 'feature', 'dimension', 'scale', 'unit',
                '测量', '参数', '变量', '特征', '维度', '尺度', '单位'
            },
            EntityType.SOFTWARE.value: {
                'software', 'application', 'program', 'code', 'library', 'package', 'framework', 'tool',
                '软件', '应用', '程序', '代码', '工具包', '框架'
            },
            EntityType.AUTHOR.value: {
                'author', 'researcher', 'contributor', 'creator', 'developer', 'scientist',
                '作者', '研究者', '贡献者', '开发者', '科学家'
            },
            EntityType.INSTITUTION.value: {
                'institution', 'university', 'lab', 'department', 'center', 'school', 'company', 'organization',
                '机构', '大学', '实验室', '院系', '研究所', '中心', '学校', '公司', '组织'
            },
        }

    @staticmethod
    def _compile_keyword_pattern(kw: str) -> re.Pattern:
        """编译关键词：纯 ASCII 用词边界 \\b，含非 ASCII（如中文）则直接子串匹配。

        中文没有 \\b 词边界概念，对中文加 \\b 会导致匹配不到，因此按内容是否纯 ASCII 区分处理。
        """
        if kw.isascii():
            return re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
        return re.compile(re.escape(kw))

    def _precompile_keyword_patterns(self) -> dict[str, list[re.Pattern]]:
        return {etype: [self._compile_keyword_pattern(kw) for kw in keywords]
                for etype, keywords in self.entity_keywords.items()}

    def add_custom_entity_type(self, entity_type: str, keywords: set[str], patterns: list[str] = None):
        """Add a custom entity type with keywords and optional regex patterns."""
        self.custom_entity_types[entity_type] = {
            'keywords': keywords,
            'patterns': [re.compile(p, re.IGNORECASE) for p in patterns or []]
        }
        self.entity_keywords[entity_type] = keywords
        self._keyword_patterns[entity_type] = [self._compile_keyword_pattern(kw) for kw in keywords]

    def extract_entities(self, text: str, entity_types: Optional[list[str]] = None,
                        min_confidence: float = 0.5) -> list[Entity]:
        if not text or not text.strip():
            return []

        entities = []

        if self.nlp:
            entities.extend(self._extract_spacy_entities(text, entity_types))

        entities.extend(self._extract_pattern_entities(text, entity_types))
        entities.extend(self._extract_keyword_entities(text, entity_types))
        entities.extend(self._extract_acronym_entities(text, entity_types))
        entities.extend(self._extract_name_entities(text, entity_types))
        entities.extend(self._extract_author_entities(text, entity_types))
        entities.extend(self._extract_custom_entities(text, entity_types))

        entities = self._deduplicate_entities(entities)
        return [e for e in entities if e.confidence >= min_confidence]

    def _extract_spacy_entities(self, text: str, entity_types: Optional[list[str]]) -> list[Entity]:
        entities = []
        if not self.nlp:
            return entities

        try:
            doc = self.nlp(text)
            # Map spaCy labels to our entity types
            type_mapping = {
                'ORG': EntityType.INSTITUTION.value,
                'PERSON': EntityType.AUTHOR.value,
                'PRODUCT': EntityType.TOOL.value,
                'WORK_OF_ART': EntityType.MODEL.value,
                'EVENT': EntityType.TASK.value,
            }

            for ent in doc.ents:
                if ent.label_ in type_mapping:
                    mapped_type = type_mapping[ent.label_]
                    if entity_types is None or mapped_type in entity_types:
                        entities.append(Entity(
                            entity_id=str(uuid.uuid4()),
                            text=ent.text, type=mapped_type,
                            start_pos=ent.start_char, end_pos=ent.end_char,
                            confidence=self.CONFIDENCE_SPACY,
                            source_document='', attributes={'source': 'spacy', 'label': ent.label_}
                        ))
                elif ent.label_ in ['DATE', 'TIME', 'PERCENT', 'MONEY', 'QUANTITY', 'ORDINAL', 'CARDINAL']:
                    # Add temporal and numeric entities
                    if entity_types is None or EntityType.MEASUREMENT.value in entity_types:
                        entities.append(Entity(
                            entity_id=str(uuid.uuid4()),
                            text=ent.text, type=EntityType.MEASUREMENT.value,
                            start_pos=ent.start_char, end_pos=ent.end_char,
                            confidence=self.CONFIDENCE_SPACY * 0.8,
                            source_document='', attributes={'source': 'spacy', 'label': ent.label_}
                        ))
        except Exception as e:
            logger.warning(f"Error in spaCy entity extraction: {e}")

        return entities

    def _extract_pattern_entities(self, text: str, entity_types: Optional[list[str]]) -> list[Entity]:
        entities = []
        types_to_extract = entity_types if entity_types else list(self.entity_patterns.keys())

        for entity_type in types_to_extract:
            if entity_type not in self.entity_patterns:
                continue

            for pattern in self.entity_patterns[entity_type]:
                for match in pattern.finditer(text):
                    # 对中文匹配结果，直接使用 match.group() 不再扩展
                    matched = match.group()
                    if any(ord(c) > 0x4e00 for c in matched):
                        entity_text = matched
                    else:
                        entity_text = self._extract_entity_phrase(text, match.start(), match.end())
                    if len(entity_text) > 1:
                        entities.append(Entity(
                            entity_id=str(uuid.uuid4()),
                            text=entity_text, type=entity_type,
                            start_pos=match.start(), end_pos=match.end(),
                            confidence=self.CONFIDENCE_PATTERN,
                            source_document='', attributes={'source': 'pattern'}
                        ))
        return entities

    def _extract_keyword_entities(self, text: str, entity_types: Optional[list[str]]) -> list[Entity]:
        entities = []
        types_to_extract = entity_types if entity_types else list(self.entity_keywords.keys())
        sentences = self._split_into_sentences(text)

        for entity_type in types_to_extract:
            if entity_type not in self._keyword_patterns:
                continue

            for pattern in self._keyword_patterns[entity_type]:
                for sentence in sentences:
                    for match in pattern.finditer(sentence):
                        entity_text = self._extract_entity_phrase(sentence, match.start(), match.end())
                        # 过滤掉 entity_text 就是关键词本身的情况（例如 "task" 匹配 "task"）
                        if len(entity_text) > 2 and entity_text.lower() != match.group().lower():
                            entities.append(Entity(
                                entity_id=str(uuid.uuid4()),
                                text=entity_text, type=entity_type,
                                start_pos=match.start(), end_pos=match.end(),
                                confidence=self.CONFIDENCE_KEYWORD,
                                source_document='',
                                attributes={'source': 'keyword', 'matched_keyword': match.group()}
                            ))
        return entities

    def _extract_acronym_entities(self, text: str, entity_types: Optional[list[str]]) -> list[Entity]:
        entities = []
        context_patterns = {
            'model': [r'\bmodel\b', r'\bnetwork\b', r'\barchitecture\b', r'\bframework\b'],
            'method': [r'\bmethod\b', r'\btechnique\b', r'\balgorithm\b', r'\bapproach\b'],
            'dataset': [r'\bdataset\b', r'\bdata\b', r'\bbenchmark\b', r'\bcorpus\b'],
            'task': [r'\btask\b', r'\bchallenge\b', r'\bevaluation\b', r'\bbenchmark\b'],
            'metric': [r'\bscore\b', r'\bmetric\b', r'\bmeasure\b'],
        }

        for match in self._acronym_pattern.finditer(text):
            acronym = match.group()
            context = text[max(0, match.start() - 80):match.end() + 80]
            entity_type = None

            for etype, pats in context_patterns.items():
                for pat in pats:
                    if re.search(pat, context, re.IGNORECASE):
                        entity_type = etype
                        break
                if entity_type:
                    break

            if entity_type is None:
                entity_type = 'model'

            confidence = self.CONFIDENCE_ACRONYM if entity_type != 'model' or any(
                re.search(p, context, re.IGNORECASE) for p in context_patterns['model']
            ) else self.CONFIDENCE_ACRONYM_DEFAULT

            if entity_types is None or entity_type in entity_types:
                entities.append(Entity(
                    entity_id=str(uuid.uuid4()),
                    text=acronym, type=entity_type,
                    start_pos=match.start(), end_pos=match.end(),
                    confidence=confidence,
                    source_document='', attributes={'source': 'acronym'}
                ))

        for match in self._noun_phrase_pattern.finditer(text):
            phrase = match.group(1)
            if len(phrase) > 3 and len(phrase) < 60:
                etype = self._classify_noun_phrase(phrase, entity_types)
                entities.append(Entity(
                    entity_id=str(uuid.uuid4()),
                    text=phrase, type=etype,
                    start_pos=match.start(), end_pos=match.end(),
                    confidence=self.CONFIDENCE_NOUN_PHRASE,
                    source_document='', attributes={'source': 'noun_phrase'}
                ))

        return entities

    def _extract_name_entities(self, text: str, entity_types: Optional[list[str]]) -> list[Entity]:
        """Extract names that might be entities (like model names)."""
        entities = []
        for match in self._name_pattern.finditer(text):
            entity_text = match.group()
            # Only extract names that might be models or methodologies
            if any(word.lower() in entity_text.lower() for word in ['model', 'method', 'algorithm', 'approach']):
                if entity_types is None or EntityType.MODEL.value in entity_types:
                    entities.append(Entity(
                        entity_id=str(uuid.uuid4()),
                        text=entity_text, type=EntityType.MODEL.value,
                        start_pos=match.start(), end_pos=match.end(),
                        confidence=self.CONFIDENCE_NAME,
                        source_document='', attributes={'source': 'name_pattern'}
                    ))
        return entities

    def _extract_author_entities(self, text: str, entity_types: Optional[list[str]]) -> list[Entity]:
        """Extract potential author names."""
        entities = []
        for match in self._author_pattern.finditer(text):
            entity_text = match.group()
            if entity_types is None or EntityType.AUTHOR.value in entity_types:
                entities.append(Entity(
                    entity_id=str(uuid.uuid4()),
                    text=entity_text, type=EntityType.AUTHOR.value,
                    start_pos=match.start(), end_pos=match.end(),
                    confidence=self.CONFIDENCE_AUTHOR,
                    source_document='', attributes={'source': 'author_pattern'}
                ))
        return entities

    def _extract_custom_entities(self, text: str, entity_types: Optional[list[str]]) -> list[Entity]:
        """Extract custom-defined entity types."""
        entities = []
        for entity_type, config in self.custom_entity_types.items():
            if entity_types is not None and entity_type not in entity_types:
                continue

            # Check keywords
            for kw in config.get('keywords', []):
                pattern = re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
                for match in pattern.finditer(text):
                    entities.append(Entity(
                        entity_id=str(uuid.uuid4()),
                        text=match.group(), type=entity_type,
                        start_pos=match.start(), end_pos=match.end(),
                        confidence=self.CONFIDENCE_REGEX,
                        source_document='', attributes={'source': 'custom_keyword', 'keyword': kw}
                    ))

            # Check patterns
            for pattern in config.get('patterns', []):
                for match in pattern.finditer(text):
                    entities.append(Entity(
                        entity_id=str(uuid.uuid4()),
                        text=match.group(), type=entity_type,
                        start_pos=match.start(), end_pos=match.end(),
                        confidence=self.CONFIDENCE_REGEX,
                        source_document='', attributes={'source': 'custom_pattern', 'pattern': pattern.pattern}
                    ))
        return entities

    def _classify_noun_phrase(self, phrase: str, entity_types: Optional[list[str]]) -> str:
        phrase_lower = phrase.lower()
        for etype, keywords in self.entity_keywords.items():
            if entity_types is not None and etype not in entity_types:
                continue
            for kw in keywords:
                if len(kw) > 3 and kw in phrase_lower:
                    return etype
        return 'method'

    def _extract_entity_phrase(self, text: str, start: int, end: int) -> str:
        extended_start = start
        extended_end = end

        while extended_start > 0 and (text[extended_start - 1].isalnum() or text[extended_start - 1] in '-_'):
            extended_start -= 1

        while extended_end < len(text) and (text[extended_end].isalnum() or text[extended_end] in '-_'):
            extended_end += 1

        return text[extended_start:extended_end].strip()

    def _split_into_sentences(self, text: str) -> list[str]:
        return [s.strip() for s in self._sentence_delimiter.split(text) if s.strip()]

    def _deduplicate_entities(self, entities: list[Entity]) -> list[Entity]:
        seen = {}
        for entity in entities:
            # For deduplication, we consider text + type combination
            key = (entity.text.lower(), entity.type)
            if key not in seen or entity.confidence > seen[key].confidence:
                seen[key] = entity
        return list(seen.values())

    def extract_from_documents(self, documents: list[str],
                              entity_types: Optional[list[str]] = None,
                              min_confidence: float = 0.5) -> list[list[Entity]]:
        results = []
        for i, doc in enumerate(documents):
            entities = self.extract_entities(doc, entity_types, min_confidence)
            for entity in entities:
                entity.source_document = f"doc_{i}"
            results.append(entities)
        return results

    def get_entity_statistics(self, entities: list[Entity]) -> dict:
        stats = {
            'total_entities': len(entities),
            'by_type': defaultdict(int),
            'avg_confidence': 0.0,
            'high_confidence_count': 0
        }
        if not entities:
            return stats
        total_confidence = sum(e.confidence for e in entities)
        stats['avg_confidence'] = total_confidence / len(entities)
        for entity in entities:
            stats['by_type'][entity.type] += 1
            if entity.confidence >= 0.8:
                stats['high_confidence_count'] += 1
        stats['by_type'] = dict(stats['by_type'])
        return stats

    def build_entity_vocabulary(self, entities: list[Entity]) -> dict[str, list[str]]:
        vocabulary = defaultdict(list)
        for entity in entities:
            vocabulary[entity.type].append(entity.text)
        for etype in vocabulary:
            vocabulary[etype] = list(set(vocabulary[etype]))
        return dict(vocabulary)
