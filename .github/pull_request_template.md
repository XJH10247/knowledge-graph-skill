## 改动说明

<!-- 这个 PR 解决了什么问题？为什么需要它？ -->

关联 Issue：<!-- 例如 Closes #12 -->

## 改动类型

- [ ] `feat` 新增功能
- [ ] `fix` 缺陷修复
- [ ] `docs` 文档
- [ ] `refactor` 重构
- [ ] `test` 测试
- [ ] `chore` 工程化 / 依赖

## 涉及模块

- [ ] `entity_extractor`
- [ ] `relation_extractor`
- [ ] `graph_builder`
- [ ] `visualizer`
- [ ] `trajectory_analyzer`
- [ ] `KnowledgeGraphPipeline`
- [ ] 文档 / 工程化

## 实现方式

<!-- 简述关键设计决策，以及为什么这样实现 -->

## 验证方式

<!-- 粘贴实际执行的命令与结果，例如 pytest 输出 -->

```text

```

## 自查清单

- [ ] `pytest -q` 全绿
- [ ] `ruff check .` 无告警
- [ ] 新增/变更功能已补充测试
- [ ] 已更新 `README.md` / `SKILL.md`（如涉及用法变更）
- [ ] 已在 `CHANGELOG.md` 的 `Unreleased` 段落记录
- [ ] 未引入未使用的依赖；新增依赖已同步 `pyproject.toml` 与 `requirements*.txt`
- [ ] 无 spaCy / 无 matplotlib 环境下仍能优雅降级

## 破坏性变更

- [ ] 本 PR 包含破坏性变更（请在下方说明迁移方式）

<!-- 若有，请说明旧用法、新用法与迁移步骤 -->
