# Task 105: InitWizard 前端组件

## 目标

实现 6 步初始化向导的前端组件，替代当前 CreateWizard 的 UI 入口。

## 涉及文件

- `webnovel-writer/dashboard/frontend/src/workbench/InitWizard.jsx`（新建）
- `webnovel-writer/dashboard/frontend/src/api.js`（修改，添加 init schema 获取）
- `webnovel-writer/dashboard/frontend/src/workbench/OverviewPage.jsx`（修改，替换创建入口）

## 依赖

- task-104（后端 init Skill 完整可用）
- Phase 0 task-006（SkillFlowPanel 已存在）

## 前置知识

SkillFlowPanel 已实现通用的 Step 进度条 + 日志 + 表单/确认渲染。InitWizard 基于它构建，但需要自定义每步的表单 UI。

api.js 中已有的 Skill API 函数（Phase 0 task-006）：

```javascript
export function startSkill(skillName, options = {}) { ... }
export function getSkillStatus(skillId) { ... }
export function submitSkillStep(skillId, stepId, data) { ... }
export function cancelSkill(skillId) { ... }
```

## 规格

### InitWizard 组件

```jsx
/**
 * 6 步初始化向导。
 * 基于 SkillFlowPanel，但自定义每步的表单渲染。
 *
 * Props:
 *   onCompleted(projectRoot: string) — 创建成功回调
 *   onCancelled() — 取消回调
 */
export default function InitWizard({ onCompleted, onCancelled }) {
  const [skillId, setSkillId] = useState(null)

  // 启动 init Skill
  const handleStart = async () => {
    const result = await startSkill("init")
    setSkillId(result.id)
  }

  if (!skillId) {
    // 显示"开始创建"按钮
    return <StartScreen onStart={handleStart} />
  }

  return (
    <SkillFlowPanel
      skillId={skillId}
      stepRenderers={INIT_STEP_RENDERERS}
      onCompleted={() => onCompleted(/* projectRoot */)}
      onCancelled={onCancelled}
    />
  )
}
```

### stepRenderers — 每步的自定义渲染

SkillFlowPanel 支持 `stepRenderers` prop，允许每步自定义 UI：

```javascript
const INIT_STEP_RENDERERS = {
  step_1: StoryCoreFom,      // 故事核表单
  step_2: CharacterForm,      // 角色骨架表单
  step_3: GoldenFingerForm,   // 金手指表单
  step_4: WorldBuildingForm,  // 世界观表单
  step_5: CreativityPackageSelector,  // 创意约束包选择器
  step_6: SummaryConfirmation,        // 摘要确认
}
```

### Step 1-4 表单组件

每个表单组件接收 props：

```jsx
function StoryCoreFom({ stepState, onSubmit }) {
  // stepState.output_data 包含 schema（字段定义）
  // onSubmit(data) 提交表单数据
  const [formData, setFormData] = useState({})

  return (
    <form onSubmit={() => onSubmit(formData)}>
      {/* 根据 schema 渲染字段 */}
      {/* text → input, textarea → textarea, select → select, multi_select → checkbox group */}
      {/* required 字段标红星 */}
      {/* hint 显示为字段下方灰色提示 */}
    </form>
  )
}
```

### Step 5 创意约束包选择器

```jsx
function CreativityPackageSelector({ stepState, onSubmit }) {
  // stepState.output_data.packages = [{ id, name, description, constraints, score }]
  const packages = stepState.output_data?.packages || []
  const [selectedId, setSelectedId] = useState(null)

  return (
    <div>
      <h3>选择创意约束包</h3>
      <div className="package-cards">
        {packages.map(pkg => (
          <PackageCard
            key={pkg.id}
            package={pkg}
            selected={selectedId === pkg.id}
            onClick={() => setSelectedId(pkg.id)}
          />
        ))}
      </div>
      <button onClick={() => onSubmit({ selected_package_id: selectedId })}>
        确认选择
      </button>
    </div>
  )
}

// PackageCard 展示：名称、描述、约束列表、五维评分雷达/条形图
```

### Step 6 摘要确认

```jsx
function SummaryConfirmation({ stepState, onSubmit }) {
  // stepState.output_data.summary = 结构化摘要文本
  // stepState.output_data.gate_passed = true/false
  const { summary, gate_passed, missing_items } = stepState.output_data || {}

  if (!gate_passed) {
    return (
      <div className="gate-warning">
        <h3>以下必填项尚未完成</h3>
        <ul>{missing_items?.map(item => <li key={item}>{item}</li>)}</ul>
        <p>请返回对应步骤补填</p>
      </div>
    )
  }

  return (
    <div>
      <h3>项目摘要</h3>
      <pre>{summary}</pre>
      <button onClick={() => onSubmit({ confirmed: true })}>确认创建</button>
    </div>
  )
}
```

### SkillFlowPanel 扩展

SkillFlowPanel 需要支持 `stepRenderers` prop（如果 Phase 0 未实现此功能）：

```jsx
// 在 SkillFlowPanel 中，渲染当前步骤时：
const StepRenderer = stepRenderers?.[currentStep.id]
if (StepRenderer) {
  return <StepRenderer stepState={currentStepState} onSubmit={handleSubmit} />
} else {
  // 默认渲染（auto → spinner, form → 通用表单, confirm → 通用确认）
}
```

### OverviewPage 集成

在 OverviewPage 的"创建新项目"入口，将 CreateWizard 替换为 InitWizard：

```jsx
// 原来：<CreateWizard onComplete={...} />
// 改为：<InitWizard onCompleted={handleProjectCreated} onCancelled={handleCancel} />
```

## TDD 验收

- Happy path：6 步向导完整走通 → 每步表单正确渲染 → 最终显示创建成功
- Edge case 1：Step 5 创意包卡片正确展示 → 选择后提交
- Edge case 2：Step 6 闸门不通过 → 显示缺失项列表 → 不显示确认按钮
- Error case：后端返回错误 → 显示错误信息而非白屏
