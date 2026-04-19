# Phase 6: RAG 集成

## 目标

集成 RAG 向量检索，替换 Phase 3 write 的文件系统降级模式，解决长篇连载（50 章+）的"遗忘"问题。

## 架构决策

- RAG 依赖 `.env` 中配置的 Embedding 模型（如 text-embedding-3-small）和 Rerank 模型
- 后端调用 `scripts/data_modules/rag_adapter.py`（已存在，需要通过 ScriptAdapter 封装）
- 向量索引存储在 `.webnovel/rag/` 目录
- 索引构建是耗时操作，需要后台执行 + 进度推送
- write Step 1 Context Agent 检测 RAG 可用性：有索引 → 向量检索；无索引 → 文件系统降级

## Task 列表

| Task | 文件数 | 依赖 |
|------|--------|------|
| [task-601](task-601-rag-config-api.md) RAG 配置 API + .env 管理 | 2 | Phase 0 |
| [task-602](task-602-rag-adapter-bridge.md) ScriptAdapter 封装 rag_adapter.py | 1 | task-601 |
| [task-603](task-603-rag-index-build.md) 向量索引构建（后台任务 + 进度推送） | 2 | task-602 |
| [task-604](task-604-rag-context-agent.md) Context Agent RAG 模式集成 | 1 | task-603 |
| [task-605](task-605-rag-config-ui.md) 前端 RAG 配置 + 索引管理 UI | 2 | task-604 |

## 验收标准

1. 配置 Embedding/Rerank 模型 → 保存到 .env
2. 构建向量索引 → 后台执行 → 进度推送 → 完成
3. write Step 1 使用向量检索 → 日志标注"RAG 模式"
4. 对比测试：RAG 模式 vs 降级模式，上下文相关性明显提升
5. 无 .env 配置时优雅降级，不报错
