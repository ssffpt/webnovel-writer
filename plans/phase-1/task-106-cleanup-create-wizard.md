# Task 106: 删除 CreateWizard + 迁移入口

## 目标

删除旧的 CreateWizard 组件，将所有项目创建入口迁移到 InitWizard。

## 涉及文件

- `webnovel-writer/dashboard/frontend/src/workbench/CreateWizard.jsx`（删除）
- `webnovel-writer/dashboard/frontend/src/App.jsx`（修改，移除 CreateWizard 引用）

## 依赖

- task-105（InitWizard 已完成并验证）

## 规格

### 删除 CreateWizard.jsx

确认以下引用已在 task-105 中迁移后，删除文件：

```bash
# 搜索所有引用
grep -r "CreateWizard" webnovel-writer/dashboard/frontend/src/
```

预期引用点：
- `App.jsx` 中的 import 和路由
- `OverviewPage.jsx` 中的创建入口（已在 task-105 迁移）

### App.jsx 修改

```jsx
// 删除：import CreateWizard from './workbench/CreateWizard'
// 删除或替换：<CreateWizard ... /> 相关路由/条件渲染

// 如果 App.jsx 中有 "showCreateWizard" 状态，改为 "showInitWizard"
// 对应的 InitWizard 已在 OverviewPage 中集成，App.jsx 可能不需要直接引用
```

### 后端清理

检查 `project_service.py` 中的 `POST /api/project/create` 端点：
- 如果 InitWizard 完全通过 `/api/skill/init/start` 创建项目，则 `/api/project/create` 可标记 deprecated
- 暂不删除，保持向后兼容，在注释中标注 "deprecated: use /api/skill/init/start"

## TDD 验收

- Happy path：删除 CreateWizard 后，`npm run build` 无报错
- Edge case 1：OverviewPage 的创建入口正常工作（使用 InitWizard）
- Edge case 2：`/api/project/create` 仍然可用（向后兼容）
- Error case：无残留的 CreateWizard import 导致运行时错误
