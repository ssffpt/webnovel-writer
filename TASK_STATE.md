# TASK_STATE

## 当前进度
Phase: 6
Current Task: code-review-fix
Status: completed

## Phase 0: SkillRunner 基础设施

- [x] task-001 Skill 数据模型
- [x] task-002 SkillRunner 状态机
- [x] task-003 SkillRegistry + Echo 测试 Skill
- [x] task-004 Skill API 端点 (blocked by: task-003)
- [x] task-005 SSE Skill 事件推送 (blocked by: task-004)
- [x] task-006 前端 SkillFlowPanel (blocked by: task-005)

## Phase 1: Init 升级（6 步向导）

- [x] task-101 InitSkillHandler 骨架
- [x] task-102 Step 1-4 表单采集
- [x] task-103 Step 5 创意约束包生成
- [x] task-104 Step 6 一致性复述 + 充分性闸门 + 执行
- [x] task-105 InitWizard 前端组件
- [x] task-106 删除 CreateWizard + 迁移入口

## Phase 2: Plan 实现（卷级规划）

- [x] task-201 PlanSkillHandler 骨架 + Step 1-3
- [x] task-202 Step 4 节拍表 + Step 4.5 时间线
- [x] task-203 Step 5 卷骨架
- [x] task-204 Step 6 章节大纲批量生成
- [x] task-205 Step 7 回写设定集 + Step 8 验证
- [x] task-206 PlanFlow 前端组件 + OutlinePage 集成

## Phase 3: Write 实现（章节创作）

- [x] task-301 ScriptAdapter 实现
- [x] task-302 WriteSkillHandler 骨架 + 模式选择
- [x] task-303 Step 1 Context Agent（含 RAG 降级）
- [x] task-304 Step 2A 正文起草 + Step 2B 风格适配
- [x] task-305 Step 3 六维审查（并行检查器）
- [x] task-306 Step 4 润色 + Anti-AI 终检
- [x] task-307 Step 5 Data Agent + Step 6 Git 备份
- [x] task-308 WriteFlow 前端组件 + ChapterPage 集成

## Phase 4: Review 实现

- [x] task-401 ReviewSkillHandler 骨架 + Step 1-2
- [x] task-402 Step 3 并行审查
- [x] task-403 Step 4 审查报告 + Step 5-6 落库
- [x] task-404 Step 7 critical 问题决策 + Step 8 收尾
- [x] task-405 ReviewFlow 前端组件 + 六维雷达图

## Phase 5: Query 扩展

- [x] task-501 伏笔查询 API
- [x] task-502 节奏分析 API
- [x] task-503 金手指状态 + 债务查询 API
- [x] task-504 SettingPage 标签页扩展
- [x] task-505 OverviewPage 创作仪表盘

## Phase 6: RAG 集成

- [x] task-601 RAG 配置 API + .env 管理
- [x] task-602 ScriptAdapter 封装 rag_adapter.py
- [x] task-603 向量索引构建
- [x] task-604 Context Agent RAG 模式集成
- [x] task-605 前端 RAG 配置 + 索引管理 UI

## 代码评审修复

- [x] fix-1 api.js GET 参数重复编码（去掉 encodeURIComponent）
- [x] fix-2 Skill 启动协议前后端统一（前端参数包进 context）
- [x] fix-3 SkillFlowPanel 状态模型对齐（合并 steps+step_states、step_id 匹配、启用 stepRenderers）
- [x] fix-4 WriteFlow 完成回调透传最终状态
- [x] fix-5 RAG 前后端接口统一（添加 /api/rag/test、统一 API key 读取）
- [x] fix-6 大纲存储格式与工作台读取对齐
