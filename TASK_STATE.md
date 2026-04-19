# TASK_STATE

## 当前进度
Phase: 0
Current Task: task-001
Status: pending

## Phase 0: SkillRunner 基础设施

- [ ] task-001 Skill 数据模型
- [ ] task-002 SkillRunner 状态机 (blocked by: task-001)
- [ ] task-003 SkillRegistry + Echo 测试 Skill (blocked by: task-002)
- [ ] task-004 Skill API 端点 (blocked by: task-003)
- [ ] task-005 SSE Skill 事件推送 (blocked by: task-004)
- [ ] task-006 前端 SkillFlowPanel (blocked by: task-005)

## Phase 1: Init 升级（6 步向导）

- [ ] task-101 InitSkillHandler 骨架
- [ ] task-102 Step 1-4 表单采集
- [ ] task-103 Step 5 创意约束包生成
- [ ] task-104 Step 6 一致性复述 + 充分性闸门 + 执行
- [ ] task-105 InitWizard 前端组件
- [ ] task-106 删除 CreateWizard + 迁移入口

## Phase 2: Plan 实现（卷级规划）

- [ ] task-201 PlanSkillHandler 骨架 + Step 1-3
- [ ] task-202 Step 4 节拍表 + Step 4.5 时间线
- [ ] task-203 Step 5 卷骨架
- [ ] task-204 Step 6 章节大纲批量生成
- [ ] task-205 Step 7 回写设定集 + Step 8 验证
- [ ] task-206 PlanFlow 前端组件 + OutlinePage 集成

## Phase 3: Write 实现（章节创作）

- [ ] task-301 ScriptAdapter 实现
- [ ] task-302 WriteSkillHandler 骨架 + 模式选择
- [ ] task-303 Step 1 Context Agent（含 RAG 降级）
- [ ] task-304 Step 2A 正文起草 + Step 2B 风格适配
- [ ] task-305 Step 3 六维审查（并行检查器）
- [ ] task-306 Step 4 润色 + Anti-AI 终检
- [ ] task-307 Step 5 Data Agent + Step 6 Git 备份
- [ ] task-308 WriteFlow 前端组件 + ChapterPage 集成

## Phase 4: Review 实现

- [ ] task-401 ReviewSkillHandler 骨架 + Step 1-2
- [ ] task-402 Step 3 并行审查
- [ ] task-403 Step 4 审查报告 + Step 5-6 落库
- [ ] task-404 Step 7 critical 问题决策 + Step 8 收尾
- [ ] task-405 ReviewFlow 前端组件 + 六维雷达图

## Phase 5: Query 扩展

- [ ] task-501 伏笔查询 API
- [ ] task-502 节奏分析 API
- [ ] task-503 金手指状态 + 债务查询 API
- [ ] task-504 SettingPage 标签页扩展
- [ ] task-505 OverviewPage 创作仪表盘

## Phase 6: RAG 集成

- [ ] task-601 RAG 配置 API + .env 管理
- [ ] task-602 ScriptAdapter 封装 rag_adapter.py
- [ ] task-603 向量索引构建
- [ ] task-604 Context Agent RAG 模式集成
- [ ] task-605 前端 RAG 配置 + 索引管理 UI
