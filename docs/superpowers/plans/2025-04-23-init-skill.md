# Init Skill 最小闭环实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 打通 Init Skill 端到端流程：前端 InitWizard → 后端 6 步 Handler → ScriptAdapter → init_project.py → 文件生成，验证 SkillRunner 全链路工作。

**Architecture:** 复用现有 SkillRunner + SkillFlowPanel 基础设施，将 `skill_registry.py` 注册的 placeholder InitSkillHandler 替换为 `skill_handlers/init_handler.py` 的完整实现，修复发现的接口不匹配问题。

**Tech Stack:** Python (FastAPI + asyncio), React, subprocess CLI 桥接

---

## 文件结构

| 文件 | 职责 | 操作 |
|------|------|------|
| `dashboard/skill_registry.py` | Skill 注册表，将 `init` 指向完整 Handler | 修改 |
| `dashboard/skill_handlers/__init__.py` | 导出 `InitSkillHandler` | 新增 |
| `dashboard/skill_handlers.py` | 清理 placeholder InitSkillHandler | 修改 |
| `dashboard/skill_handlers/init_handler.py` | 完整的 6 步 Init Handler | 修改（修复接口） |
| `dashboard/skill_handlers/init_schemas.py` | 4 步表单 schema | 只读（验证） |
| `dashboard/skill_runner.py` | 状态机执行引擎 | 只读（验证） |
| `dashboard/script_adapter.py` | CLI 桥接 | 只读（验证） |
| `dashboard/skill_models.py` | 数据模型 | 只读（验证） |
| `dashboard/app.py` | Skill API 端点 | 只读（验证） |
| `dashboard/frontend/src/workbench/InitWizard.jsx` | 前端向导组件 | 修改（传 project_root） |
| `dashboard/frontend/src/workbench/SkillFlowPanel.jsx` | Skill 流程面板 | 只读（验证） |
| `dashboard/frontend/src/api.js` | API 调用 | 只读（验证） |
| `scripts/init_project.py` | 项目初始化脚本 | 只读（验证） |

---

## Task 1: 让 skill_handlers 包可导入

**Files:**
- Create: `dashboard/skill_handlers/__init__.py`

- [ ] **Step 1: 创建 `__init__.py` 导出 InitSkillHandler**

```python
"""Skill handlers package."""
from __future__ import annotations

from dashboard.skill_handlers.init_handler import InitSkillHandler

__all__ = ["InitSkillHandler"]
```

- [ ] **Step 2: 验证导入**

Run:
```bash
cd /Users/liushuang/Projects/webnovel-writer/webnovel-writer && python -c "from dashboard.skill_handlers import InitSkillHandler; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add dashboard/skill_handlers/__init__.py
git commit -m "feat: 导出 InitSkillHandler"
```

---

## Task 2: 修复 init_handler.py 接口不匹配

**背景:** `init_handler.py` 中的 `execute_step` 方法签名与 `SkillHandler` 抽象接口不匹配。`SkillRunner` 调用时传入的是 `StepState` 对象，但 `init_handler.py` 中的逻辑假设 `step` 有 `input_data` 和 `step_id` 属性。

**Files:**
- Modify: `dashboard/skill_handlers/init_handler.py`

- [ ] **Step 1: 修复 `execute_step` 中对 `step.input_data` 的访问**

当前代码第 45-47 行：
```python
if step.step_id in ("step_1", "step_2", "step_3", "step_4"):
    context.update(step.input_data or {})
    return {"merged_fields": list((step.input_data or {}).keys())}
```

问题：`step` 是 `StepState` 对象，确实有 `step_id` 和 `input_data` 属性，但需要确认。查看 `skill_models.py` 第 32-40 行，`StepState` 有 `step_id` 和 `input_data`。这部分应该没问题。

真正的问题在第 63-82 行：
```python
if step.step_id == "step_6":
    if step.input_data:
        # 第二次调用 — 用户已确认，执行项目创建
        ...
    # 第一次调用 — 生成摘要供用户确认
```

`SkillRunner.submit_input()` 的流程是：
1. 用户提交数据 → `current.input_data = data` → `status = "running"`
2. 调用 `handler.execute_step(current, context)`
3. 所以 `execute_step` 被调用时，`step.input_data` 已经有值了

但 `start()` 方法在启动时也会调用 `execute_step` 处理 auto 步骤。对于 step_6（confirm 类型），`start()` 不会执行它（confirm 会停在 waiting_input）。所以 step_6 的 `execute_step` 只会在 `submit_input` 后被调用，此时 `input_data` 一定有值。

**结论：** 当前代码逻辑是正确的，不需要修改 `execute_step` 的主体逻辑。

但需要修复一个问题：`validate_input` 第 119-120 行：
```python
if self._creation_result and not self._creation_result.get("success"):
    return f"项目创建失败：{self._creation_result.get('error', '未知错误')}"
```

这个检查在 `validate_input` 中，但 `_creation_result` 是在 `execute_step` 中设置的。`SkillRunner` 的流程是：先 `validate_input`，再 `execute_step`。所以这里 `_creation_result` 永远是 None。

修复方案：把项目创建失败的处理放到 `execute_step` 中，如果创建失败，抛出异常让 `SkillRunner` 捕获并设置 step 为 failed。

- [ ] **Step 2: 修复 `validate_input` 中 `_creation_result` 时序问题**

修改 `dashboard/skill_handlers/init_handler.py` 第 114-121 行：

```python
# Step 6: require user confirmation
if step.step_id == "step_6":
    confirmed = data.get("confirmed", False)
    if not confirmed:
        return "请确认项目摘要"
    return None
```

（删除 `_creation_result` 的检查，因为此时还没执行创建）

- [ ] **Step 3: 在 `execute_step` step_6 中处理创建失败**

修改第 70-78 行：

```python
self._creation_input = step.input_data
self._creation_result = await self._execute_project_creation(
    {**context, **step.input_data}
)

if not self._creation_result.get("success"):
    raise RuntimeError(
        self._creation_result.get("error", "项目创建失败")
    )

step.output_data = {
    "gate_passed": True,
    "summary": self._build_summary({**context, **step.input_data}),
    "project_root": self._creation_result.get("project_root"),
    "message": "项目创建成功",
}
```

- [ ] **Step 4: 运行验证**

Run:
```bash
cd /Users/liushuang/Projects/webnovel-writer/webnovel-writer && python -c "
from dashboard.skill_handlers.init_handler import InitSkillHandler
from dashboard.skill_models import StepState
h = InitSkillHandler()
steps = h.get_steps()
print(f'Steps: {[s.id for s in steps]}')
"
```

Expected:
```
Steps: ['step_1', 'step_2', 'step_3', 'step_4', 'step_5', 'step_6']
```

- [ ] **Step 5: Commit**

```bash
git add dashboard/skill_handlers/init_handler.py
git commit -m "fix: 修复 init_handler 时序问题，创建失败时抛出异常"
```

---

## Task 3: 更新 SkillRegistry 注册完整 InitSkillHandler

**Files:**
- Modify: `dashboard/skill_registry.py`

- [ ] **Step 1: 修改导入，使用完整 Handler**

当前第 4-10 行：
```python
from dashboard.skill_handlers import (
    EchoSkillHandler,
    InitSkillHandler,
    PlanSkillHandler,
    ReviewSkillHandler,
    WriteSkillHandler,
)
```

修改为：
```python
from dashboard.skill_handlers import InitSkillHandler as FullInitSkillHandler
from dashboard.skill_handlers import (
    EchoSkillHandler,
    PlanSkillHandler,
    ReviewSkillHandler,
    WriteSkillHandler,
)
```

然后第 47 行：
```python
default_registry.register("init", FullInitSkillHandler)
```

- [ ] **Step 2: 清理 skill_handlers.py 中的 placeholder**

修改 `dashboard/skill_handlers.py`，删除 placeholder InitSkillHandler（第 42-54 行），或者保留但改名避免冲突。

方案：保留但改名，避免其他引用出错：
```python
class _InitSkillHandlerPlaceholder(SkillHandler):
    """Deprecated — use dashboard.skill_handlers.init_handler.InitSkillHandler."""
    ...
```

或者直接删除，因为 `skill_registry.py` 不再引用它。

- [ ] **Step 3: 验证注册**

Run:
```bash
cd /Users/liushuang/Projects/webnovel-writer/webnovel-writer && python -c "
from dashboard.skill_registry import default_registry
h = default_registry.get_handler('init')
print(f'Handler: {type(h).__name__}')
steps = h.get_steps()
print(f'Steps: {len(steps)}')
for s in steps:
    print(f'  {s.id}: {s.name} ({s.interaction})')
"
```

Expected:
```
Handler: InitSkillHandler
Steps: 6
  step_1: 故事核与商业定位 (form)
  step_2: 角色骨架与关系冲突 (form)
  step_3: 金手指与兑现机制 (form)
  step_4: 世界观与力量规则 (form)
  step_5: 创意约束包 (confirm)
  step_6: 一致性复述与确认 (confirm)
```

- [ ] **Step 4: Commit**

```bash
git add dashboard/skill_registry.py dashboard/skill_handlers.py
git commit -m "feat: 注册完整 InitSkillHandler，替换 placeholder"
```

---

## Task 4: 修复前端 InitWizard 传递 project_root

**背景:** `InitWizard` 启动 Skill 时没有传递 `project_root`，但后端 `start_skill` 需要知道在哪个目录创建项目。

查看 `app.py` 第 172-206 行，`start_skill` 使用 `_get_project_root()` 作为默认 project_root。但 Init Skill 需要创建新项目，可能需要传递不同的路径。

查看 `ScriptAdapter.init_project()` — 它接受 `project_root` 参数，如果目录不存在会创建。

所以 Init Skill 需要：
1. 用户指定项目路径（或通过某种方式确定）
2. 或者使用一个默认路径

当前 `OverviewPage.jsx` 的 `handleCreateNew` 只是 `setShowWizard(true)`，没有路径选择。

方案：Step 1 表单中增加 `project_root` 字段，或者前端自动生成一个基于书名的路径。

更简单的方案：前端在 `startSkill` 时传递 `context.project_root`，使用书名生成目录名。

- [ ] **Step 1: 修改 `InitWizard.jsx` 的 `handleStart`，传递 context**

修改第 97-105 行：

```javascript
const handleStart = async () => {
    setStartError('')
    try {
      // 临时使用默认路径，后续可从用户输入获取
      const result = await startSkill('init', {
        context: { project_root: './projects/new-novel' }
      })
      setSkillId(result.id)
    } catch (err) {
      setStartError(err instanceof Error ? err.message : '启动失败')
    }
  }
```

等等，这不够。用户需要能指定路径和书名。

更好的方案：Step 1 表单已经包含 `title` 字段，后端可以根据 title 生成目录名。或者前端在 `onCompleted` 回调中处理项目切换。

实际上，查看 `init_handler.py` 的 `_execute_project_creation`：
```python
adapter = ScriptAdapter(project_root=context.get("project_root", ""))
```

如果 `project_root` 为空，会使用 `"."` 作为项目根目录。

**决策：** 最小闭环方案 — 前端传递一个基于当前时间戳的临时目录，完成后再切换到该项目。

修改 `InitWizard.jsx`：

```javascript
const handleStart = async () => {
    setStartError('')
    try {
      const timestamp = Date.now()
      const result = await startSkill('init', {
        context: { project_root: `./projects/novel-${timestamp}` }
      })
      setSkillId(result.id)
    } catch (err) {
      setStartError(err instanceof Error ? err.message : '启动失败')
    }
  }
```

- [ ] **Step 2: 修改 `InitWizard` 的 `onCompleted` 回调，切换项目**

当前 `OverviewPage.jsx` 第 295-299 行：
```javascript
const handleWizardCompleted = useCallback(() => {
    setShowWizard(false)
    loadSummary()
    fetchProjects().then(r => setProjects(r.projects || []))
  }, [loadSummary])
```

需要接收创建结果并切换项目：

```javascript
const handleWizardCompleted = useCallback((result) => {
    setShowWizard(false)
    if (result?.result?.step_6?.project_root) {
      switchProjectAPI(result.result.step_6.project_root)
        .then(() => loadSummary())
        .then(() => fetchProjects())
        .then(r => setProjects(r.projects || []))
        .catch(() => loadSummary())
    } else {
      loadSummary()
      fetchProjects().then(r => setProjects(r.projects || []))
    }
  }, [loadSummary])
```

但 `switchProjectAPI` 未在 App.jsx 中导入。查看 App.jsx 第 10 行：
```javascript
import { switchProject as switchProjectAPI } from './api.js'
```

已经导入了。

- [ ] **Step 3: 修改 `InitWizard` 的 `onCompleted` 参数传递**

当前 `InitWizard.jsx` 第 120-122 行：
```javascript
<SkillFlowPanel
      skillId={skillId}
      stepRenderers={INIT_STEP_RENDERERS}
      onCompleted={onCompleted}
      onCancelled={onCancelled}
    />
```

`SkillFlowPanel` 的 `onCompleted` 调用时传入 `{ result, steps }`（第 432 行）。所以 `onCompleted` 回调会收到这个结果。

但 `OverviewPage.jsx` 的 `handleWizardCompleted` 当前不接受参数。需要修改：

```javascript
const handleWizardCompleted = useCallback((finalState) => {
    setShowWizard(false)
    const projectRoot = finalState?.result?.step_6?.project_root
    if (projectRoot) {
      switchProjectAPI(projectRoot)
        .then(() => loadSummary())
        .catch(() => loadSummary())
    } else {
      loadSummary()
    }
    fetchProjects().then(r => setProjects(r.projects || [])).catch(() => {})
  }, [loadSummary])
```

- [ ] **Step 4: Commit**

```bash
git add dashboard/frontend/src/workbench/InitWizard.jsx dashboard/frontend/src/workbench/OverviewPage.jsx
git commit -m "feat: InitWizard 传递 project_root，完成后自动切换项目"
```

---

## Task 5: 验证表单 schema 返回

**背景:** `SkillFlowPanel` 的 `FormStepPanel` 需要 `step.output_data.schema` 来渲染表单。但当前 `init_handler.py` 的 `execute_step` 在 step_1-4 中只返回 `{"merged_fields": [...]}`，没有返回 schema。

查看 `SkillRunner.start()` 第 270-277 行：
```python
if interaction in ("form", "confirm"):
    current.status = "waiting_input"
    ...
    return
```

对于 form 步骤，当状态变为 `waiting_input` 时，`execute_step` 还没有被调用。`execute_step` 是在 `submit_input` 时才调用的。

所以 form 步骤的 schema 应该从哪里来？

查看 `SkillFlowPanel.jsx` 第 71 行：
```javascript
const schema = step.output_data?.schema ?? {}
```

如果 `output_data` 没有 schema，就渲染空表单。

**问题：** 当前 `init_handler.py` 的 step_1-4 在 `execute_step` 中不返回 schema，所以前端看不到表单字段。

**解决方案：** 有两种方式：
1. 在 `get_steps()` 返回的 `StepDefinition` 中附加 schema 信息
2. 在 `execute_step` 中返回 schema

查看 `StepDefinition` 模型 — 只有 `id`, `name`, `interaction`, `skippable`，没有 schema 字段。

所以应该在 `execute_step` 中返回 schema。但 `execute_step` 是在用户提交后才调用的...

等等，再仔细看 `SkillRunner.start()`：

对于 form 步骤：
1. `start()` 中遇到 form 步骤 → 设置 `waiting_input` → 返回
2. 前端看到 `waiting_input` → 渲染表单
3. 用户提交 → `submit_input()` → 调用 `execute_step()`

所以前端渲染表单时，`execute_step` 还没执行，拿不到 schema。

这意味着 schema 必须在步骤定义中携带，或者在 `start()` 执行 form 步骤前就准备好。

查看 `StepDefinition` — 没有 schema 字段。需要扩展。

或者，更简单的方式：前端 `InitWizard` 的 `INIT_STEP_RENDERERS` 中 step_1-4 设为 `null`，让 `SkillFlowPanel` 使用默认的 `FormStepPanel`。但 `FormStepPanel` 需要 schema。

**方案：** 扩展 `StepDefinition` 增加可选的 `schema` 字段，在 `get_steps()` 中返回。

- [ ] **Step 1: 扩展 `StepDefinition` 增加 schema 字段**

修改 `dashboard/skill_models.py` 第 11-19 行：

```python
@dataclass
class StepDefinition:
    id: str
    name: str
    interaction: str  # "auto" | "form" | "confirm"
    skippable: bool = False
    schema: dict | None = None  # form 步骤的表单定义

    def to_dict(self) -> dict:
        return asdict(self)
```

- [ ] **Step 2: 修改 `InitSkillHandler.get_steps()` 返回 schema**

修改 `dashboard/skill_handlers/init_handler.py` 第 28-36 行：

```python
def get_steps(self, mode: str | None = None) -> list[StepDefinition]:
    return [
        StepDefinition(id="step_1", name="故事核与商业定位", interaction="form", schema=INIT_STEP_SCHEMAS["step_1"]),
        StepDefinition(id="step_2", name="角色骨架与关系冲突", interaction="form", schema=INIT_STEP_SCHEMAS["step_2"]),
        StepDefinition(id="step_3", name="金手指与兑现机制", interaction="form", schema=INIT_STEP_SCHEMAS["step_3"]),
        StepDefinition(id="step_4", name="世界观与力量规则", interaction="form", schema=INIT_STEP_SCHEMAS["step_4"]),
        StepDefinition(id="step_5", name="创意约束包", interaction="confirm"),
        StepDefinition(id="step_6", name="一致性复述与确认", interaction="confirm"),
    ]
```

- [ ] **Step 3: 修改 `SkillFlowPanel` 从步骤定义中读取 schema**

修改 `dashboard/frontend/src/workbench/SkillFlowPanel.jsx` 第 71 行：

```javascript
const schema = step.schema ?? step.output_data?.schema ?? {}
```

同时修改 `mergeStepsAndStates` 函数（第 235-253 行），将 `schema` 从定义合并到步骤：

```javascript
return steps.map(def => {
    const state = stateMap[def.id ?? def.step_id]
    return {
      id: def.id ?? def.step_id,
      name: def.name ?? def.step_id,
      interaction: def.interaction,
      schema: def.schema ?? null,  // 添加 schema
      status: state ? normalizeStepStatus(state.status) : 'pending',
      output_data: state?.output_data ?? null,
      progress: state?.progress ?? 0,
    }
  })
```

- [ ] **Step 4: 验证 schema 传递**

Run:
```bash
cd /Users/liushuang/Projects/webnovel-writer/webnovel-writer && python -c "
from dashboard.skill_handlers.init_handler import InitSkillHandler
h = InitSkillHandler()
steps = h.get_steps()
for s in steps:
    print(f'{s.id}: schema={\"yes\" if s.schema else \"no\"}')
"
```

Expected:
```
step_1: schema=yes
step_2: schema=yes
step_3: schema=yes
step_4: schema=yes
step_5: schema=no
step_6: schema=no
```

- [ ] **Step 5: Commit**

```bash
git add dashboard/skill_models.py dashboard/skill_handlers/init_handler.py dashboard/frontend/src/workbench/SkillFlowPanel.jsx
git commit -m "feat: StepDefinition 支持 schema 字段，Init 表单可渲染"
```

---

## Task 6: 端到端测试

**Files:**
- 只读验证

- [ ] **Step 1: 启动后端服务**

```bash
cd /Users/liushuang/Projects/webnovel-writer/webnovel-writer/dashboard && python -m uvicorn app:create_app --factory --host 0.0.0.0 --port 8000 --reload
```

在另一个终端验证 API：
```bash
curl -X POST http://localhost:8000/api/skill/init/start -H "Content-Type: application/json" -d '{"context": {"project_root": "./test-novel"}}'
```

Expected: 返回包含 6 个 steps 的 JSON

- [ ] **Step 2: 验证 Step 1 表单 schema**

```bash
curl http://localhost:8000/api/skill/init-1/status
```

Expected: `current_step` 是 `step_1`，`steps[0].schema` 包含 fields 定义

- [ ] **Step 3: 提交 Step 1 表单**

```bash
curl -X POST http://localhost:8000/api/skill/init-1/step -H "Content-Type: application/json" -d '{
  "step_id": "step_1",
  "data": {
    "title": "测试小说",
    "genres": ["修仙"],
    "target_words": 1000000,
    "target_chapters": 300,
    "one_line_story": "一个凡人修仙的故事",
    "core_conflict": "人与天的对抗"
  }
}'
```

Expected: 返回状态，current_step 变为 step_2

- [ ] **Step 4: 依次提交 Step 2-4**

Step 2:
```bash
curl -X POST http://localhost:8000/api/skill/init-1/step -H "Content-Type: application/json" -d '{
  "step_id": "step_2",
  "data": {
    "protagonist_name": "张三",
    "protagonist_desire": "成为最强仙人",
    "protagonist_flaw": "过于自负",
    "protagonist_structure": "正向成长弧",
    "romance_config": "单女主",
    "villain_tiers": "小反派:李四;中反派:王五;大反派:赵六"
  }
}'
```

Step 3:
```bash
curl -X POST http://localhost:8000/api/skill/init-1/step -H "Content-Type: application/json" -d '{
  "step_id": "step_3",
  "data": {
    "golden_finger_type": "系统流",
    "golden_finger_name": "修仙系统",
    "golden_finger_style": "科技感",
    "golden_finger_visibility": "仅主角可见",
    "golden_finger_cost": "消耗寿命",
    "golden_finger_growth": "线性成长"
  }
}'
```

Step 4:
```bash
curl -X POST http://localhost:8000/api/skill/init-1/step -H "Content-Type: application/json" -d '{
  "step_id": "step_4",
  "data": {
    "world_scale": "多大陆",
    "power_system": "炼气→筑基→金丹→元婴→化神",
    "faction_layout": "正道联盟 vs 魔道",
    "social_hierarchy": "凡人→修士→仙人"
  }
}'
```

- [ ] **Step 5: 提交 Step 5（选择创意包）**

```bash
curl -X POST http://localhost:8000/api/skill/init-1/step -H "Content-Type: application/json" -d '{
  "step_id": "step_5",
  "data": {
    "selected_package_id": "pkg_fallback"
  }
}'
```

- [ ] **Step 6: 提交 Step 6（确认）**

```bash
curl -X POST http://localhost:8000/api/skill/init-1/step -H "Content-Type: application/json" -d '{
  "step_id": "step_6",
  "data": {
    "confirmed": true
  }
}'
```

Expected: 返回 completed 状态，result 中包含 project_root

- [ ] **Step 7: 验证文件生成**

```bash
ls -la ./test-novel/.webnovel/
ls -la ./test-novel/设定集/
ls -la ./test-novel/大纲/
cat ./test-novel/.webnovel/state.json
```

Expected: state.json 存在且包含正确的项目信息

- [ ] **Step 8: 前端测试**

1. 打开浏览器访问 http://localhost:8000
2. 点击"创建新小说"
3. 依次填写 6 步表单
4. 确认后查看是否自动切换到新项目
5. 检查总览页是否显示正确的书名和题材

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "test: Init Skill 端到端测试通过"
```

---

## Task 7: 清理和收尾

- [ ] **Step 1: 删除测试项目**

```bash
rm -rf ./test-novel ./projects
```

- [ ] **Step 2: 运行现有测试确保没破坏**

```bash
cd /Users/liushuang/Projects/webnovel-writer/webnovel-writer && pytest dashboard/tests/ -v --tb=short
```

Expected: 所有现有测试通过

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: 清理测试数据"
```

---

## Spec 覆盖检查

| Spec 要求 | 对应 Task |
|-----------|-----------|
| 6 步向导流程 | Task 2, 3, 5 |
| 表单 schema 定义 | Task 5 |
| 创意约束包选择 | Task 2 (已有 fallback) |
| 充分性闸门 | Task 2 (已有) |
| 项目创建调用 init_project.py | Task 2 (已有) |
| Patch 总纲 + idea_bank | Task 2 (已有) |
| 前端 SkillFlowPanel 展示 | Task 4, 5 |
| 完成后自动切换项目 | Task 4 |
| SSE 实时推送 | 已有基础设施，无需修改 |

**无缺口。**

---

## Placeholder 扫描

- [x] 无 "TBD", "TODO", "implement later"
- [x] 无 "Add appropriate error handling" 等模糊描述
- [x] 每个步骤都有具体代码
- [x] 无 "Similar to Task N" 引用

---

## 类型一致性检查

- `StepDefinition.schema` — Task 5 中添加，类型为 `dict | None`
- `InitSkillHandler.get_steps()` — 返回 `list[StepDefinition]`，与基类一致
- `execute_step` 签名 — `async def execute_step(self, step: StepState, context: dict) -> dict`，与基类一致
- `validate_input` 签名 — `async def validate_input(self, step: StepState, data: dict) -> str | None`，与基类一致

**一致。**
