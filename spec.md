# Web Workbench Spec — CLI 流程 Web 化

> 目标：将 CLI 的完整 AI 驱动创作流程映射为 Web 交互，保持流程约束和防幻觉机制不变，只是把命令行交互变成 Web 页面交互。

## 一、背景

本项目 fork 自一个完整的 CLI 网文创作系统，具备：
- 防幻觉三定律（大纲即法律 / 设定即物理 / 发明需识别）
- 双 Agent 架构（Context Agent 读 + Data Agent 写）
- 6 个 Skill（init / plan / write / review / query / resume）
- RAG 向量检索、六维并行审查、工作流状态机

当前 Web 版是一个**文件编辑器 + 轻量 AI 助手**，与 CLI 的完整流程存在巨大差距。详细差异分析见 [docs/cli-vs-web-comparison.md](docs/cli-vs-web-comparison.md)。

## 二、核心设计原则

1. **流程忠实**：Web 版必须完整复现 CLI 每个 Skill 的步骤，不得缩水或跳步
2. **交互升级**：CLI 的文本问答变为表单/向导/卡片，但信息采集深度不降
3. **渐进展示**：长流程用 Step Indicator + 实时日志展示进度，用户可观察每步状态
4. **后端驱动**：核心逻辑在后端执行（调用现有 scripts/），前端只做展示和交互采集
5. **断点可恢复**：每个 Step 完成后持久化状态，中断后可从断点继续

## 三、架构设计

### 3.1 当前架构问题

```
前端 (React) → API (FastAPI) → claude_runner.py → 半真实命令映射：
                                                    - 章节类：preflight + extract-context
                                                    - 大纲/设定类：preflight + 文件存在性校验
                                                    - 均不执行完整 Skill 流程
```

### 3.2 目标架构

```
前端 (React)
  ├── 向导式 UI（采集用户输入）
  ├── Step 进度条（实时展示流程状态）
  └── SSE 实时日志

FastAPI 后端
  ├── /api/skill/{skill_name}/start   — 启动 Skill 流程
  ├── /api/skill/{skill_id}/step      — 提交当前 Step 的用户输入
  ├── /api/skill/{skill_id}/status    — 查询流程状态
  └── /api/skill/{skill_id}/cancel    — 取消流程

SkillRunner（新增，替代 claude_runner.py）
  ├── 管理 Skill 生命周期（Step 状态机）
  ├── 通过 ScriptAdapter 调用 scripts/
  ├── 调用 AI API 执行创作/审查
  └── 通过 SSE 推送进度

ScriptAdapter（新增，scripts/ 的 Python API 封装）
  ├── 将 scripts/ 的 CLI 调用封装为 async Python 函数
  ├── 统一错误处理和超时控制
  └── 避免 SkillRunner 直接 subprocess 调用

scripts/（现有，尽量不改动，通过 ScriptAdapter 桥接）
  ├── webnovel.py（统一 CLI 入口）
  ├── init_project.py
  ├── extract_chapter_context.py
  └── data_modules/（状态管理、RAG、实体等）
```

> **关于 scripts/ 的改动策略**：scripts/ 是 CLI 时代的产物，接口是命令行参数 + stdout/stderr。SkillRunner 不直接 subprocess 调用它们，而是通过 ScriptAdapter 封装层桥接。如果某个 script 的输出格式不适合 Web 消费（如纯文本而非 JSON），在 ScriptAdapter 中做转换，尽量不改 scripts/ 本身。但如果某个 script 确实需要改（如 `init_project.py` 需要接受更多参数），允许小幅修改，在对应 task 文件中明确标注。

### 3.3 SkillRunner 状态机

每个 Skill 实例维护一个状态机：

```
CREATED → STEP_N_WAITING_INPUT → STEP_N_RUNNING → STEP_N_DONE → ... → COMPLETED
                                       ↓
                                  STEP_N_FAILED → (用户重试) → STEP_N_RUNNING
```

状态持久化到 `.webnovel/workflow/` 目录，支持断点恢复。

### 3.4 与现有 workflow_manager.py 的关系

现有 `scripts/workflow_manager.py` 使用单一 `.webnovel/workflow_state.json` 文件，记录 CLI 任务的 step 进度（start-task / complete-step / detect）。

**共存策略**：
- SkillRunner 使用独立的 `.webnovel/workflow/instances/` 目录存储 Skill 实例状态（每实例一个 JSON）
- SkillRunner 在执行 Step 时，同时调用 `workflow_manager.py` 的 `start-task` / `complete-step` 写入 `workflow_state.json`，保持与 CLI `/webnovel-resume` 的兼容
- `workflow_state.json` 是 CLI 的断点恢复数据源，SkillRunner 的实例 JSON 是 Web 的断点恢复数据源
- 两者记录同一次执行的不同视角：`workflow_state.json` 记录"哪个命令执行到哪一步"，实例 JSON 记录完整的输入/输出/上下文

后续如果 CLI 也迁移到 SkillRunner，可以统一为一套，但当前阶段保持双写。

### 3.5 前后端交互协议

每个 Step 的交互模式分三类：

| 模式 | 说明 | 前端行为 |
|------|------|---------|
| `auto` | 后端自动执行，无需用户输入 | 显示进度条 + 日志 |
| `form` | 需要用户填写表单后提交 | 渲染动态表单，提交后继续 |
| `confirm` | 需要用户确认/选择后继续 | 显示结果 + 确认/选择按钮 |

SSE 事件格式：
```json
{
  "type": "skill.step",
  "skillId": "xxx",
  "step": { "id": "step_3", "name": "审查", "status": "running", "progress": 0.6 },
  "log": "正在执行设定一致性检查..."
}
```

### 3.6 TaskService → SkillRunner 迁移策略

当前 `task_service.py` + `claude_runner.py` 是前端唯一的任务执行通道，前端 `App.jsx`、`api.js`、SSE `/api/events` 都依赖它。直接替换风险很高。

**渐进迁移方案**：

| 阶段 | 旧接口 | 新接口 | 说明 |
|------|--------|--------|------|
| Phase 0 | `/api/tasks` 保留 | `/api/skill/*` 新增 | 双轨并存，前端可选择走哪条路 |
| Phase 1-3 | `/api/tasks` 保留但不再新增功能 | 各 Skill 入口迁移到 `/api/skill/*` | 新功能只走 Skill API |
| Phase 4+ | `/api/tasks` 标记 deprecated | `/api/skill/*` 成为唯一通道 | 前端移除旧 task 调用 |
| 最终 | 删除 `task_service.py` + `claude_runner.py` | — | 确认无引用后清理 |

SSE 事件也是双轨：
- 旧：`task.updated`（TaskService 发出）
- 新：`skill.step` / `skill.completed` / `skill.failed`（SkillRunner 发出）
- 共用同一个 `/api/events` SSE 端点，前端按 `type` 字段区分

### 3.7 Git 自动提交策略

CLI 的 write Step 6 会自动 git commit。Web 场景需要更谨慎：

- 默认**关闭**自动提交（Web 用户可能不在 git 仓库中工作）
- 通过 `.webnovel/config.json` 的 `auto_git_commit: true` 开启
- 提交信息格式：`[webnovel] 第{N}章 - {title}（{skill_name} Step {step_id}）`
- 提交失败不阻断流程，记录 warning 日志
- 前端在 OverviewPage 的设置区域提供开关

## 四、现有页面改造方案

### 4.0 总览：现有组件 → 目标状态

| 现有组件 | 当前职责 | 改造方向 | 涉及 Phase |
|---------|---------|---------|-----------|
| `CreateWizard.jsx` | 3 步简化表单（书名/题材/主角） | Phase 1 被 `InitWizard.jsx` 替代后**删除** | Phase 1 |
| `ChapterPage.jsx` | textarea 手动编辑 + 文件列表 | 保留手动编辑，新增 `WriteFlow` 面板（用户选择"AI 写"或"手写"） | Phase 3 |
| `OutlinePage.jsx` | markdown 文件编辑器 | 保留编辑功能，新增 `PlanFlow` 面板（"生成大纲"按钮启动 plan Skill） | Phase 2 |
| `SettingPage.jsx` | 实体列表浏览（仅 index.db 查询） | 扩展标签页：实体 / 伏笔 / 金手指 / 节奏 / 债务 | Phase 5 |
| `OverviewPage.jsx` | 项目概况 + "下一步"建议 | 新增：中断恢复卡片、Skill 快捷入口卡片、创作进度仪表盘 | Phase 0/5 |
| `AIAssistant.jsx` | 浮动聊天面板 + 关键词匹配 → 动作卡 | **重定位为 Skill 启动器**（见下方详述） | Phase 0 |
| `TopBar.jsx` | 页面导航 + 项目切换 | 新增：活跃 Skill 进度指示器 | Phase 0 |
| `data.js` | 页面模型 + 动作路由 | 扩展：Skill 状态模型、Skill 路由逻辑 | Phase 0 |
| `api.js` | 文件读写 + chat + task API | 新增：`/api/skill/*` 系列函数 | Phase 0 |

### 4.0.1 AIAssistant → Skill 启动器

当前 `AIAssistant.jsx` 是一个浮动聊天面板，通过关键词匹配生成"动作卡"，但动作卡背后的 `claude_runner.py` 只做 preflight。

改造后的定位：**意图识别 + Skill 路由器**

- 用户输入自然语言（如"写第5章"、"审查1-3章"、"规划第2卷"）
- 后端识别意图，返回对应的 Skill 启动参数
- 前端不再显示动作卡，而是直接启动 Skill，流程在页面内的 `SkillFlowPanel` 展示
- AIAssistant 面板本身变为轻量：只有输入框 + 最近启动的 Skill 列表
- 去掉 `workbench_service.py` 中的 `build_chat_response()` 关键词匹配逻辑，替换为 Skill 意图路由

交互流程：
```
用户输入 "写第5章"
  → POST /api/chat → 后端识别意图 → 返回 { "skill": "write", "params": { "chapter": 5 } }
  → 前端自动调用 POST /api/skill/write/start
  → 页面切换到 ChapterPage，WriteFlow 面板展示流程进度
  → AIAssistant 面板显示 "正在执行：写第5章" 状态
```

### 4.0.2 各页面具体改动

#### OverviewPage（总览页）

当前：项目概况 + StepProgressBar（起步/写作中/审查）+ 下一步建议

改造：
- StepProgressBar 改为反映真实创作阶段（init 完成 → plan 完成 → 写作进度 → 审查覆盖率）
- "下一步"建议卡片改为 Skill 快捷入口（点击直接启动 Skill，不再跳转页面）
- 新增"中断恢复"卡片：检测到未完成的 Skill 时显示，点击恢复
- 新增"创作仪表盘"：总字数/章节进度/审查覆盖率/伏笔回收率

#### ChapterPage（章节页）

当前：左侧文件列表 + 右侧 textarea 编辑器 + 专注模式

改造：
- 保留现有手动编辑功能不变
- 编辑器顶部新增模式切换：`手动编辑` | `AI 创作`
- 选择"AI 创作"时，编辑区域替换为 `WriteFlow` 面板（SkillFlowPanel 的 write 实例）
- WriteFlow 完成后，正文自动加载到编辑器，用户可继续微调
- 新增"审查"按钮：对当前章节启动 review Skill，结果在侧面板展示

#### OutlinePage（大纲页）

当前：左侧大纲文件列表 + 右侧 markdown 编辑器 + "生成第N卷大纲"按钮（不工作）

改造：
- 保留 markdown 编辑功能
- "生成第N卷大纲"按钮改为启动 plan Skill
- 点击后编辑区域替换为 `PlanFlow` 面板，展示 8 步流程进度
- 节拍表/时间线/卷骨架生成后用结构化卡片展示（非纯 markdown），用户确认后写入文件
- PlanFlow 完成后，自动切回编辑器，加载生成的大纲文件

#### SettingPage（设定页）

当前：实体列表 + 实体详情（从 index.db 查询）

改造：
- 顶部新增标签页切换：`实体` | `伏笔` | `金手指` | `节奏` | `债务`
- 实体标签页保留现有功能
- 伏笔标签页：三层分类 + 紧急度颜色标记 + 回收状态
- 金手指标签页：当前等级/技能/升级条件/发展建议
- 节奏标签页：Strand 连续/断档检测时间轴
- 债务标签页：伏笔回收紧急度排序列表

### 4.0.3 新增通用组件

| 组件 | 用途 | 引入 Phase |
|------|------|-----------|
| `SkillFlowPanel.jsx` | Skill 流程展示（Step 进度条 + 日志 + 表单/确认） | Phase 0 |
| `InitWizard.jsx` | 6 步深度初始化向导 | Phase 1 |
| `PlanFlow.jsx` | 卷规划流程面板（嵌入 OutlinePage） | Phase 2 |
| `WriteFlow.jsx` | 章节创作流程面板（嵌入 ChapterPage） | Phase 3 |
| `ReviewFlow.jsx` | 审查流程面板（嵌入 ChapterPage 侧面板） | Phase 4 |
| `RadarChart.jsx` | 六维雷达图（审查结果可视化） | Phase 4 |

### 4.0.4 要删除/迁移的代码

| 文件/代码 | 处理方式 | 时机 |
|----------|---------|------|
| `CreateWizard.jsx` | 删除，被 InitWizard 替代 | Phase 1 完成后 |
| `claude_runner.py` | 删除，被 SkillRunner + ScriptAdapter 替代 | Phase 4 完成后（确认所有 Skill 已迁移） |
| `workbench_service.py` 中的 `build_chat_response()` | 替换为 Skill 意图路由 | Phase 0 完成后 |
| `task_service.py` | 渐进迁移，Phase 0-3 双轨并存，Phase 4+ 标记 deprecated | 最终删除在所有前端引用清理后 |
| `/api/tasks` 系列端点 | 保留到 Phase 4+，前端逐步切换到 `/api/skill/*` | 最终删除在前端完全迁移后 |

---

## 五、各 Skill Web 化规格

### 5.1 `/webnovel-init` — 项目初始化（6 步向导）

当前 Web 版是 3 步简化表单，需要升级为 6 步深度采集。

#### Step 定义

| Step | 名称 | 交互模式 | 采集内容 |
|------|------|---------|---------|
| 1 | 故事核与商业定位 | `form` | 书名、题材(复合)、目标规模、一句话故事、核心冲突、目标读者 |
| 2 | 角色骨架与关系冲突 | `form` | 主角姓名/欲望/缺陷/结构、感情线配置、反派分层 |
| 3 | 金手指与兑现机制 | `form` | 类型/名称/风格/可见度/不可逆代价/成长节奏 + 条件必收项 |
| 4 | 世界观与力量规则 | `form` | 世界规模/力量体系/势力格局/社会阶层 + 题材相关项 |
| 5 | 创意约束包 | `confirm` | 后端生成 2-3 套创意包 → 用户三问筛选 → 五维评分 → 选择 |
| 6 | 一致性复述与确认 | `confirm` | 后端输出摘要草案 → 用户确认 → 执行生成 |

#### 充分性闸门（Step 6 前校验）

6 项必须全部通过才可执行生成：
1. 书名 + 题材已确认
2. 目标规模已设定
3. 主角欲望 + 缺陷已填写
4. 世界观 + 力量体系已定义
5. 创意约束包已选择
6. 用户已确认摘要

#### 后处理（Step 6 确认后自动执行）

- 调用 `init_project.py` 生成项目骨架
- Patch 总纲（补齐故事一句话/核心暗线/创意约束/反派分层/爽点里程碑）
- 写入 `.webnovel/idea_bank.json`

#### 前端组件

- `InitWizard.jsx`：替代当前 `CreateWizard.jsx`，6 步向导
- 每步有 AI 辅助提示（后端根据已填内容生成建议）
- Step 5 创意约束包需要特殊 UI：卡片式展示 + 对比选择

---

### 5.2 `/webnovel-plan` — 卷级规划（8 步流程）

当前 Web 版完全未实现，大纲页只是 markdown 编辑器。

#### Step 定义

| Step | 名称 | 交互模式 | 说明 |
|------|------|---------|------|
| 1 | 加载项目数据 | `auto` | 读取 state.json/总纲/设定集/idea_bank |
| 2 | 构建设定基线 | `auto` | 增量补齐设定集，不清空重写 |
| 3 | 选择卷 | `form` | 确认卷名/章节范围/特殊需求 |
| 4 | 生成卷节拍表 | `auto` → `confirm` | 生成后展示，用户确认或调整 |
| 4.5 | 生成卷时间线表 | `auto` → `confirm` | 生成后展示，用户确认 |
| 5 | 生成卷骨架 | `auto` → `confirm` | Strand 规划/爽点密度/伏笔/约束触发 |
| 6 | 生成章节大纲 | `auto` | 分批生成，每章 16 字段，实时推送进度 |
| 7 | 回写设定集 | `auto` | 新增事实写回设定集，冲突标记 BLOCKER |
| 8 | 验证 + 保存 | `auto` | 7 项验证检查 |

#### 7 项验证（Step 8）

1. 爽点密度达标
2. Strand 比例合理
3. 总纲一致性
4. 约束频率达标
5. 章节大纲完整性
6. 时间线无矛盾
7. 设定补全无遗漏

#### 前端组件

- `PlanFlow.jsx`：卷规划流程面板，嵌入 OutlinePage
- 节拍表/时间线/卷骨架用结构化卡片展示（非纯 markdown）
- 章节大纲生成时显示批次进度（如 "正在生成第 5/12 章"）

---

### 5.3 `/webnovel-write` — 章节创作（6 步流程，最核心）

当前 Web 版只是 textarea 手动编辑，完全缺失 AI 创作流程。

#### Step 定义

| Step | 名称 | 交互模式 | 说明 |
|------|------|---------|------|
| 1 | Context Agent | `auto` | 生成 7 板块任务书 + Context Contract + 写作执行包 |
| 2A | 正文起草 | `auto` → `confirm` | 遵循大纲约束，2000-2500 字，生成后用户可预览/微调 |
| 2B | 风格适配 | `auto` → `confirm` | 定向改写模板腔/说明腔/机械腔（--fast 跳过） |
| 3 | 六维审查 | `auto` | 6 个 Checker 并行执行，结果实时推送 |
| 4 | 润色 | `auto` → `confirm` | 修复 critical→high→medium/low，Anti-AI 终检 |
| 5 | Data Agent | `auto` | 实体提取→消歧→写入→摘要→场景切片→RAG→风格样本→债务 |
| 6 | Git 备份 | `auto` | 自动提交 |

#### 模式支持

- 标准模式：Step 1 → 2A → 2B → 3 → 4 → 5 → 6
- `--fast`：Step 1 → 2A → 3 → 4 → 5 → 6（跳过 2B）
- `--minimal`：Step 1 → 2A → 3(仅核心 3 项) → 4 → 5 → 6

#### RAG 降级模式

write 的 Context Agent（Step 1）依赖 RAG 检索相关设定/伏笔/前文。RAG 在 Phase 6 才完整集成，因此 Phase 3 实现 write 时采用降级策略：

- **无 RAG 时**：Context Agent 仅从文件系统加载（总纲 + 设定集 + 前 N 章摘要），不做向量检索
- **有 RAG 时**：Context Agent 额外通过 RAG 检索语义相关的设定片段和伏笔
- 降级模式下 write 功能完整可用，但长篇连载（50 章+）的上下文质量会下降
- 前端在 Step 1 日志中标注"RAG 未配置，使用文件系统降级模式"

#### 流程硬约束

- 禁止并步（不得合并两个 Step）
- 禁止跳步（不得跳过未标记可跳过的 Step）
- 禁止自审替代（Step 3 必须由独立检查器执行）

#### 前端组件

- `WriteFlow.jsx`：章节创作流程面板，嵌入 ChapterPage
- Step 2A/2B/4 完成后显示正文预览 + diff 对比
- Step 3 审查结果用六维雷达图 + 问题列表展示
- 模式选择器（标准/快速/极简）

---

### 5.4 `/webnovel-review` — 章节审查（8 步流程）

当前 Web 版完全未实现。

#### Step 定义

| Step | 名称 | 交互模式 | 说明 |
|------|------|---------|------|
| 1 | 加载参考 | `auto` | 加载 core-constraints 等 |
| 2 | 加载项目状态 | `auto` | 读取 state.json + 相关章节 |
| 3 | 并行调用检查员 | `auto` | 6 维并行审查，实时推送各维度进度 |
| 4 | 生成审查报告 | `auto` → `confirm` | 6 维评分 + 修改优先级 + 改进建议 |
| 5 | 保存审查指标 | `auto` | 写入 index.db |
| 6 | 写回审查记录 | `auto` | 更新 state.json |
| 7 | 处理关键问题 | `confirm` | critical 问题必须用户决策修复方案 |
| 8 | 收尾 | `auto` | 完成任务 |

#### 前端组件

- `ReviewFlow.jsx`：审查流程面板
- 六维雷达图（爽点密度/设定一致性/节奏比例/人物 OOC/叙事连贯性/追读力）
- 问题列表按 critical → high → medium → low 排序
- critical 问题弹出决策对话框

---

### 5.5 `/webnovel-query` — 信息查询

当前 Web 版只有实体列表浏览。

#### 查询类型

| 类型 | 说明 | 前端入口 |
|------|------|---------|
| 标准查询 | 角色/境界/金手指等 | SettingPage 搜索框 |
| 伏笔分析 | 三层分类 + 紧急度公式 | 专用"伏笔"标签页 |
| 金手指状态 | 基本信息/等级/技能/升级条件 | 专用"金手指"标签页 |
| 节奏分析 | Strand 连续/断档检测 | 专用"节奏"标签页 |
| 标签格式 | 实体标签规范 | 设定页内联 |
| 紧急债务 | 伏笔回收紧急度排序 | 专用"债务"标签页 |

#### 前端组件

- 扩展 `SettingPage.jsx`，增加标签页切换
- 伏笔紧急度用颜色标记（Critical 红 / Warning 黄 / Normal 绿）
- 节奏分析用时间轴可视化

---

### 5.6 `/webnovel-resume` — 中断恢复

当前 Web 版完全未实现。

#### 流程

1. 后端检测 `.webnovel/workflow/` 中的中断状态
2. 前端展示恢复选项（命令/中断时间/已完成步骤/剩余步骤）
3. 用户选择恢复策略
4. 执行恢复

#### 前端组件

- 总览页检测到中断任务时显示恢复卡片
- 恢复选项对话框

---

## 六、缺失基础设施

### 6.1 双 Agent 架构

| Agent | 职责 | 实现方式 |
|-------|------|---------|
| Context Agent | 写作前构建创作任务书 | SkillRunner 在 write Step 1 调用 |
| Data Agent | 写后提取实体/更新状态/建 RAG 索引 | SkillRunner 在 write Step 5 调用 |

### 6.2 RAG 向量检索

- 写作时通过 RAG 检索相关设定/伏笔/前文
- 依赖 `.env` 中配置的 Embedding 模型和 Rerank 模型
- 后端调用 `scripts/data_modules/rag_adapter.py`

### 6.3 工作流状态机

- SkillRunner 实例状态持久化到 `.webnovel/workflow/instances/{skill_id}.json`
- 同时双写 `.webnovel/workflow_state.json`（兼容 CLI 的 `/webnovel-resume`）
- 支持断点检测：OverviewPage 加载时扫描 instances/ 中 status 为 running/waiting_input 的实例
- 恢复流程：`SkillRunner.resume(instance_path)` → 从 JSON 恢复 → 继续执行剩余步骤
- 断点恢复是 Phase 0 的一部分（SkillRunner 核心能力），不是独立 Phase

---

## 七、实施路线

每个 Phase 附带验收标准，完成后对照 `docs/cli-vs-web-comparison.md` 确认差距消除情况。

### Phase 0：基础设施（SkillRunner + API + 断点恢复）

- [ ] 实现 `SkillRunner` 状态机 + `ScriptAdapter`
- [ ] 实现 `/api/skill/*` 系列 API（与 `/api/tasks` 双轨并存）
- [ ] SSE 推送 skill step 事件
- [ ] 前端 `SkillFlowPanel` 通用组件（Step 进度条 + 日志 + 表单渲染）
- [ ] 断点恢复基础能力：SkillRunner 从持久化 JSON 恢复 + OverviewPage 恢复卡片

验收：前端启动 echo 测试 Skill → 3 步自动执行 → SSE 实时推送 → 进度条走完 → 中断后刷新页面能恢复

### Phase 1：Init 升级（6 步向导）

- [ ] `InitWizard.jsx` 替代 `CreateWizard.jsx`
- [ ] 后端 init skill handler（6 步状态机）
- [ ] AI 辅助提示（每步根据已填内容生成建议）
- [ ] 创意约束包 UI

验收：通过 6 步向导创建项目 → state.json/总纲/设定集/idea_bank 全部生成 → 充分性闸门拦截不完整提交

### Phase 2：Plan 实现（卷级规划）

- [ ] `PlanFlow.jsx` 嵌入 OutlinePage
- [ ] 后端 plan skill handler（8 步状态机）
- [ ] 节拍表/时间线/卷骨架结构化展示
- [ ] 章节大纲批量生成 + 进度推送

验收：选择卷 → 节拍表/时间线/卷骨架生成并展示 → 用户确认 → 章节大纲分批生成 → 7 项验证通过 → 文件写入

### Phase 3：Write 实现（章节创作，最核心）

- [ ] `WriteFlow.jsx` 嵌入 ChapterPage
- [ ] 后端 write skill handler（6 步状态机，RAG 降级模式）
- [ ] Context Agent + Data Agent 集成
- [ ] 六维审查结果展示
- [ ] 正文预览 + diff 对比
- [ ] 模式选择器（标准/快速/极简）

验收：选择章节 → AI 创作模式 → 6 步流程走完 → 正文文件 + review_metrics + 摘要 + state 更新全部落盘 → 失败可从断点恢复

### Phase 4：Review 实现

- [ ] `ReviewFlow.jsx`
- [ ] 后端 review skill handler（8 步状态机）
- [ ] 六维雷达图
- [ ] critical 问题决策对话框

验收：选择章节范围 → 6 维并行审查 → 报告生成 → 指标落库 → critical 问题弹出决策 → 用户选择修复方案

### Phase 5：Query 扩展

- [ ] SettingPage 标签页扩展（伏笔/金手指/节奏/债务）
- [ ] 伏笔紧急度可视化
- [ ] 节奏分析时间轴
- [ ] 创作仪表盘（OverviewPage）

验收：各标签页数据正确展示 → 伏笔紧急度颜色标记 → Strand 断档检测

### Phase 6：RAG 集成

- [ ] RAG 环境配置 UI（.env 中的 Embedding/Rerank 模型）
- [ ] 写作时 RAG 检索集成（替换 Phase 3 的降级模式）
- [ ] 向量索引管理（构建/更新/状态查看）

验收：配置 RAG → write Step 1 使用向量检索 → 上下文质量明显优于文件系统降级模式

---

## 八、关于 `docs/cli-vs-web-comparison.md`

该文档准确描述了 CLI 与当前 Web 版的差异，作为本 spec 的需求分析基础保留。后续开发中可作为验收对照表使用——每完成一个 Phase，对照该文档确认差距是否已消除。

建议保留在 `docs/` 目录，作为项目文档的一部分。
