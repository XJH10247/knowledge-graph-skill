# 贡献指南

感谢你有兴趣为 `research-knowledge-graph` 做贡献！本文档说明如何搭建开发环境、
提交改动以及本项目遵循的约定。

## 目录

- [行为准则](#行为准则)
- [开发环境](#开发环境)
- [项目结构约定](#项目结构约定)
- [代码规范](#代码规范)
- [测试](#测试)
- [提交信息规范](#提交信息规范)
- [提交 Pull Request](#提交-pull-request)
- [扩展实体与关系类型](#扩展实体与关系类型)
- [新增可视化类型](#新增可视化类型)

## 行为准则

参与本项目即表示你同意遵守 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)，
并保持友善、专业、就事论事的交流方式。
请勿提交任何包含个人隐私、密钥凭据或未授权版权材料的代码。
安全漏洞请按 [SECURITY.md](SECURITY.md) 私密报告，不要开公开 Issue。

## 开发环境

需要 Python 3.9 或更高版本。

```bash
# 1. Fork 并克隆仓库
git clone https://github.com/<your-name>/research-knowledge-graph.git
cd research-knowledge-graph

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. 以可编辑模式安装全部依赖
pip install -e ".[all,dev]"

# 4. 验证环境
pytest -q
```

## 项目结构约定

```
research_kg/          可导入的 Python 包（唯一发布产物）
├── __init__.py       KnowledgeGraphPipeline 与顶层导出
└── modules/          五大核心模块
examples/             可运行示例（不参与打包）
tests/                单元测试（不参与打包）
docs/                 文档、示例产物与演示材料
references/           Skill 渐进披露的详细 API（SKILL.md 链接至此）
locales/              桌面插件展示元数据（displayName / brief）
SKILL.md              Skill 入口描述（供 AI Agent 读取）
```

新增可导入的代码一律放入 `research_kg/`；新增的包目录必须同步登记到
`pyproject.toml` 的 `[tool.setuptools] packages`。

Skill 相关约定：

- `SKILL.md` frontmatter 的 `name` 必须是 kebab-case，且与安装目录名一致（当前为
  `research-knowledge-graph`）。
- frontmatter 不得出现 XML 尖括号；详细 API 放 `references/`，不要堆进 `SKILL.md`。
- 改动用户可见的展示名时，同步更新 `locales/zh-CN.json` 与 `locales/en-US.json`。

## 代码规范

- 代码风格由 `ruff` 校验与约束，行宽上限 100。提交前请执行：

  ```bash
  ruff check .          # 检查
  ruff check . --fix    # 自动修复
  ```

- 所有公开的函数、方法与类需有 docstring；面向用户的文案与注释使用中文，
  标识符、日志与 commit message 使用英文。
- 优先使用类型注解，保持 `from __future__` 之外的 Python 3.9 兼容语法。
- 新增依赖时，请同步更新 `pyproject.toml` 的 `dependencies` 或对应 extras，
  以及 `requirements.txt` / `requirements-dev.txt`。
  不要引入未在本项目中被实际导入的依赖。
- 变更日志写入 `CHANGELOG.md` 的 `Unreleased` 段落。

## 测试

```bash
pytest -q                                   # 全量
pytest tests/test_knowledge_graph.py -q     # 单文件
pytest -q --cov=research_kg                 # 带覆盖率
```

要求：

- 新增功能必须附带测试，且不降低现有覆盖率。
- 修复缺陷时请先补一个能复现问题的失败用例。
- 提交前确保 `pytest` 全绿；CI 会在 Python 3.9 ~ 3.13 上复跑。
- 涉及文件输出的用例请使用 `tempfile` 写入临时目录，不要污染仓库。

## 提交信息规范

本项目遵循 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/)：

```
<type>(<scope>): <subject>
```

常用 `type`：

| type | 含义 |
|------|------|
| `feat` | 新增功能 |
| `fix` | 修复缺陷 |
| `docs` | 仅文档变更 |
| `refactor` | 重构（不改变外部行为） |
| `test` | 新增或调整测试 |
| `chore` | 构建、依赖、配置等杂项 |
| `perf` | 性能优化 |

`scope` 建议使用模块名，例如 `entity`、`relation`、`graph`、`viz`、`trajectory`。

示例：

```
feat(entity): 支持从标题行抽取机构实体
fix(graph): 修复 GEXF 导出丢失边属性的问题
docs(readme): 补充中文使用示例
```

## 提交 Pull Request

1. 从 `main` 切出特性分支：`git checkout -b feat/your-feature`。
2. 完成改动，确保 `pytest` 全绿且 `ruff check .` 无告警。
3. 更新相关文档（`README.md`、`SKILL.md`、`references/api.md`、`CHANGELOG.md`）。
4. 提交 PR，并在描述中填写：改动目的、实现方式、验证方式、是否破坏兼容性。
5. 建议一个 PR 只解决一件事，便于评审与回滚。

评审人通常会关注：

- 是否引入了硬依赖（能用 extras 隔离的不要放进 `dependencies`）。
- 是否在无 spaCy / 无 matplotlib 的环境下仍能优雅降级。
- 抽取规则的改动是否影响了已有测试的预期结果。

## 扩展实体与关系类型

**新增实体类型**——在 `research_kg/modules/entity_extractor.py` 中：

1. 在 `EntityType` 枚举里添加成员。
2. 在 `_initialize_patterns()` 中补充正则模式。
3. 在 `_initialize_keywords()` 中补充中英文关键词。
4. 在 `tests/` 中添加对应抽取用例。

若只是临时扩展、不想改动源码，可在运行时调用：

```python
extractor.add_custom_entity_type(
    'domain',
    {'machine learning', 'computer vision'},
    [r'\b(machine learning|computer vision)\b'],
)
```

**新增关系类型**——在 `research_kg/modules/relation_extractor.py` 中：

1. 在 `RelationType` 枚举里添加成员。
2. 在 `_initialize_patterns()` 中补充正则模式（需包含两个捕获组，分别对应源实体与目标实体）。
3. 补充测试用例。

运行时扩展：

```python
extractor.add_custom_relation_type('develops', [r'\b(\w+)\s+develops\s+(\w+)\b'])
```

## 新增可视化类型

可视化模块统一放在 `research_kg/modules/visualizer.py`，请遵循既有约定：

- 方法签名以 `visualize_<type>(graph, ..., output_path=...)` 命名。
- 返回值为 `output_path`，便于调用方串联。
- 静态图统一走 `_setup_chinese_font()` 初始化中文字体，避免中文乱码。
- matplotlib 在无显示环境下必须可用（不要依赖交互式后端）。

---

再次感谢你的贡献。有任何疑问，欢迎开 [Issue](https://github.com/XJH10247/research-knowledge-graph/issues) 讨论。
