# Web Workbench 重设计实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 Web Workbench 用户流程重设计——后端新增 7 个 API，前端重构所有 4 个页面 + 创建向导 + AI 助手浮动组件 + 项目切换器。

**Architecture:** 后端在 `app.py` 中新增路由，业务逻辑拆分到独立服务模块（`genre_service.py`、`project_service.py`）。前端保持 React 单组件架构，重构现有页面组件，新增创建向导弹窗和 AI 助手浮动对话框，移除固定右侧栏。

**Tech Stack:** FastAPI (Python)、React 19 + Vite、SSE 实时推送

**Spec:** `docs/superpowers/specs/2026-04-16-web-workbench-redesign.md`
**Design mockups:** `docs/design-mockups/v4-all-pages.html`、`docs/design-mockups/v4.1-supplements.html`

---

## File Structure

### Backend — 新建文件
| File | Responsibility |
|------|---------------|
| `dashboard/genre_service.py` | 题材列表解析、金手指类型解析 |
| `dashboard/project_service.py` | 项目创建、列表、切换 |
| `dashboard/tests/test_new_apis.py` | 新增 API 的契约测试（TDD：先写） |

### Backend — 修改文件
| File | Changes |
|------|---------|
| `dashboard/app.py` | 新增 7 个路由，新增 import，新增 `_PACKAGE_ROOT` 常量，`_recent_activities` 缓存，活动写入逻辑 |
| `dashboard/workbench_service.py` | 新增 `build_outline_tree()` 函数 |

### Frontend — 新建文件
| File | Responsibility |
|------|---------------|
| `frontend/src/workbench/CreateWizard.jsx` | 3 步创建向导弹窗 |
| `frontend/src/workbench/AIAssistant.jsx` | 浮动 💬 按钮 + 展开对话框 |
| `frontend/src/workbench/ProjectSwitcher.jsx` | 项目切换器下拉 |

### Frontend — 重构文件
| File | Changes |
|------|---------|
| `frontend/src/api.js` | 新增 7 个 API 函数 |
| `frontend/src/workbench/data.js` | 新增项目状态判断、页面序号、"下一步"建议、实体类型映射 |
| `frontend/src/App.jsx` | 移除 RightSidebar 固定布局，集成 AIAssistant 浮动组件，新增项目状态管理 |
| `frontend/src/workbench/TopBar.jsx` | 带序号标签 ①②③④ + 项目切换器 |
| `frontend/src/workbench/OverviewPage.jsx` | 全面重写：空状态/未完成/就绪 3 种视图 + loading/error |
| `frontend/src/workbench/OutlinePage.jsx` | 左侧树形 + 右侧编辑区 |
| `frontend/src/workbench/SettingPage.jsx` | 左侧卡片 + 筛选标签 + 右侧编辑区 |
| `frontend/src/workbench/ChapterPage.jsx` | 倒序列表 + 编辑区 + 专注模式 |
| `frontend/src/index.css` | 移除右侧栏布局、新增浮动 AI/专注模式/向导弹窗/切换器样式 |

### Frontend — 移除/替换文件
| File | Reason |
|------|--------|
| `frontend/src/workbench/RightSidebar.jsx` | 被 AIAssistant.jsx 替代 |
| `frontend/src/workbench/OnboardingGuide.jsx` | 新设计已有步骤引导条，不再需要独立引导组件 |

---

## Task 1: Backend — 契约测试（TDD 红灯）

**Files:**
- Create: `webnovel-writer/dashboard/tests/test_new_apis.py`

**TDD 原则**：先写测试定义 API 契约，此时测试应全部失败（红灯）。后续 Task 2-4 逐步实现使测试通过。

参照现有 `test_phase1_contracts.py` 的测试模式（使用 ASGI raw scope 直接调用 FastAPI app，不依赖 httpx），复用其中的 `make_project()` 和 `request_json()` 辅助函数。

需扩展 `make_project()` 以支持不同测试场景（见下方辅助函数扩展）。

- [x] **Step 1: 创建测试文件**

测试用例覆盖：

**GET /api/genres**
1. 返回 200，`genres` 为列表且非空
2. 每项有 `key`（str）、`label`（str）字段
3. 至少包含 `xuanhuan`（修仙）和 `rules-mystery`（规则怪谈）
4. 每项可选包含 `profile_id`（str 或 null）

**GET /api/golden-finger-types**
5. 返回 200，`types` 为列表
6. types 包含 key=`"none"` 的项（无金手指）
7. 每项有 `key`（str）、`label`（str）字段

**GET /api/outline/tree**
8. 返回 200，包含 `files`（列表）、`volumes`（列表）、`total_volumes`（int）字段
9. `volumes` 每项有 `number`、`has_outline`（bool）、`chapter_range`（[int,int]）字段

**GET /api/recent-activity**
10. 返回 200，`activities` 为列表

**GET /api/projects**
11. 返回 200，包含 `projects`（列表）和 `current`（str 或 null）字段

**POST /api/project/create**
12. 缺少 `title` 字段时返回 400
13. 正常创建：返回 `success`=true、`project_root`（str）、`state`（dict），项目目录存在且含 `.webnovel/state.json`

**POST /api/project/switch**
14. 目标路径不存在 `.webnovel/state.json` 时返回 400
15. 正常切换：返回 `success`=true

扩展 `make_project()` 辅助函数，增加可选参数创建 index.db 和多项目场景：
```python
def make_project(tmp_path: Path, *, title="测试小说", genre="玄幻",
                  with_db=False, chapters=None) -> Path:
    # ... 现有逻辑 ...
    if with_db:
        import sqlite3
        db_path = webnovel_dir / "index.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE entities (id TEXT PRIMARY KEY, type TEXT, canonical_name TEXT, ...)")
        conn.execute("CREATE TABLE chapters (chapter INTEGER PRIMARY KEY, title TEXT, ...)")
        if chapters:
            for ch in chapters:
                conn.execute("INSERT INTO chapters VALUES (?, ?, ...)", (ch['num'], ch['title'], ...))
        conn.commit()
        conn.close()
    return project_root
```

- [x] **Step 2: 运行测试（预期全红）**

Run: `cd webnovel-writer && python -m pytest dashboard/tests/test_new_apis.py -v`
Expected: 全部 FAILED（路由尚不存在），确认测试本身语法无误

- [x] **Step 3: Commit**

```bash
git add dashboard/tests/test_new_apis.py
git commit -m "test: add contract tests for new APIs (TDD red phase)"
```

---

## Task 2: Backend — 题材与金手指 API

**Files:**
- Create: `webnovel-writer/dashboard/genre_service.py`
- Modify: `webnovel-writer/dashboard/app.py:8-24` (imports) + 新增路由

### genre_service.py 数据源（3 个，需合并）

| 数据源 | 数量 | 内容 | 用途 |
|--------|------|------|------|
| `webnovel-writer/genres/` 子目录 | 6 个 | xuanhuan, dog-blood-romance, rules-mystery, zhihu-short, period-drama, realistic | `key`（唯一标识符），子目录名即 key |
| `webnovel-writer/templates/genres/` .md 文件 | 37 个 | 文件名即中文题材名（修仙.md, 规则怪谈.md, 都市脑洞.md 等） | `label`（中文显示名）、`template`（模板文件名） |
| `webnovel-writer/references/genre-profiles.md` | 13 个 | 格式为 Markdown，每个 profile 有 `id:` 和 `name:` 行 | `profile_id`（追读力配置关联） |

### list_genres() 合并逻辑

1. 扫描 `templates/genres/*.md` 文件列表 → 这是完整的题材集合（37 个）
2. 每个文件的文件名（去掉 .md）即为 `label`
3. 尝试匹配 `genres/` 子目录名：若存在则用子目录名作为 `key`，否则用 label 的拼音或英文slug 作为 `key`
4. 解析 `genre-profiles.md`，提取每个 profile 的 `id` 和 `name`，按 `name` 匹配到 label，关联 `profile_id`

**key 分配策略**：
- `genres/` 子目录存在的题材：key = 子目录名（如 `xuanhuan`）
- `genres/` 子目录不存在的题材：key = label 本身（如 `"都市脑洞"`, `"高武"`）

**genre-profiles.md 解析**：
- 文件格式为 Markdown，每个 profile 块以 `### ` 或 `## ` 标题开头
- 包含 `id: xxx` 和 `name: xxx` 行
- 用正则 `r"id:\s*(\S+)"` 和 `r"name:\s*(.+)"` 提取
- `name` 与 `label` 模糊匹配（profile name "修仙/玄幻" 匹配 label "修仙"）

### 金手指类型解析

解析 `templates/golden-finger-templates.md`，提取类型列表：
- 查找"类型速查表"或类似的 Markdown 表格
- 表格行格式：`| 类型名 | 简述 | ... |`
- 也可按二级标题 `## XXX流` 提取（8 个类型标题：系统面板流/随身空间流/重生穿越流/签到打卡流/器灵导师型/血脉觉醒型/异能觉醒型/无金手指）
- key 由中文类型名映射生成

```python
GF_KEY_MAP = {
    "系统面板": "system",
    "随身空间": "space",
    "重生穿越": "rebirth",
    "签到打卡": "checkin",
    "器灵导师": "spirit",
    "血脉觉醒": "bloodline",
    "异能觉醒": "ability",
}
# "无金手指" → key="none"
```

- [x] **Step 1: 创建 `genre_service.py`**

创建 `webnovel-writer/dashboard/genre_service.py`，实现两个纯函数：
- `list_genres(package_root: Path) -> dict` — 合并三个数据源，返回 `{ genres: [{ key, label, template, profile_id }, ...] }`
- `list_golden_finger_types(package_root: Path) -> dict` — 解析 golden-finger-templates.md，返回 `{ types: [{ key, label }, ...] }`

- [x] **Step 2: 在 `app.py` 中添加路由**

在 `app.py` 导入区新增 `from .genre_service import list_genres, list_golden_finger_types`。

在全局变量区新增：
```python
_PACKAGE_ROOT = Path(__file__).parent.parent  # webnovel-writer/ 包根目录
```

在 `file_save` 路由之后、`tasks/current` 路由之前，新增：
```python
@app.get("/api/genres")
def api_genres():
    return list_genres(_PACKAGE_ROOT)

@app.get("/api/golden-finger-types")
def api_golden_finger_types():
    return list_golden_finger_types(_PACKAGE_ROOT)
```

- [x] **Step 3: 运行测试（genres + gf-types 应变绿）**

Run: `cd webnovel-writer && python -m pytest dashboard/tests/test_new_apis.py::test_genres dashboard/tests/test_new_apis.py::test_golden_finger_types -v`
Expected: PASS

- [x] **Step 4: Commit**

```bash
git add dashboard/genre_service.py dashboard/app.py
git commit -m "feat(api): add GET /api/genres and GET /api/golden-finger-types"
```

---

## Task 3: Backend — 项目创建/列表/切换 API

**Files:**
- Create: `webnovel-writer/dashboard/project_service.py`
- Modify: `webnovel-writer/dashboard/app.py` (新增 3 个路由)

### init_project 调用方式：subprocess（非 import）

**原因**：`init_project.py` 有 `from runtime_compat import ...` 等相对导入依赖 `scripts/` 作为工作路径。`sys.path.insert` + import 在 dashboard 包上下文中会导致各种 import 冲突。使用 subprocess 调用 CLI 是最安全的方式，与现有 `claude_runner.py` 调用 `webnovel.py` 的模式一致。

```python
import subprocess, sys

def _run_init_project(project_dir: str, title: str, genre: str, **kwargs) -> subprocess.CompletedProcess:
    script_path = _PACKAGE_ROOT / "scripts" / "init_project.py"
    cmd = [sys.executable, str(script_path), project_dir, title, genre]
    if kwargs.get("protagonist_name"):
        cmd += ["--protagonist-name", kwargs["protagonist_name"]]
    if kwargs.get("target_words"):
        cmd += ["--target-words", str(kwargs["target_words"])]
    if kwargs.get("target_chapters"):
        cmd += ["--target-chapters", str(kwargs["target_chapters"]]
    if kwargs.get("golden_finger_name"):
        cmd += ["--golden-finger-name", kwargs["golden_finger_name"]]
    if kwargs.get("golden_finger_type"):
        cmd += ["--golden-finger-type", kwargs["golden_finger_type"]]
    if kwargs.get("core_selling_points"):
        cmd += ["--core-selling-points", kwargs["core_selling_points"]]
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
```

### project_dir 生成策略
1. 默认 `~/webnovel-projects/`，可通过 `WEBNOVEL_PROJECTS_ROOT` 环境变量覆盖
2. 子目录名 = `{title}/`
3. 若已存在，追加 `-2`、`-3` 等

### list_projects 实现
- 读取 `~/.claude/webnovel-writer/workspaces.json`（使用 `project_locator._load_global_registry()` 的逻辑，但直接读 JSON 避免导入冲突）
- 遍历 workspaces 中的每个项目路径，读取其 `.webnovel/state.json` 获取 name/genre/current_chapter
- 加 limit 参数（默认 50），避免项目过多时性能问题

### switch_project 实现

注意：`app.py` 中 `_get_db()` 每次请求都新建 SQLite 连接（不缓存），所以切换项目后无需"重连 index.db"，只需更新 `_project_root` 和重启 FileWatcher。

- [x] **Step 1: 创建 `project_service.py`**

创建 `webnovel-writer/dashboard/project_service.py`，实现三个函数：
- `create_project(payload: dict, package_root: Path) -> dict` — 生成 project_dir，subprocess 调用 init_project.py，注册到 workspaces.json，返回 {success, project_root, state}
- `list_projects() -> dict` — 读取 workspaces.json，遍历项目读取 state.json，返回 {projects, current}
- `switch_project(target_path: str, current_root: Path) -> dict` — 校验目标路径下有 .webnovel/state.json，更新 workspaces.json，返回 {success, project_root}

注意 watcher 停止/重启逻辑留在 app.py 路由层，不侵入 service 层。

- [x] **Step 2: 在 `app.py` 中添加 3 个路由**

```python
from .project_service import create_project, list_projects, switch_project

@app.post("/api/project/create")
def api_create_project(payload: dict):
    title = payload.get("title")
    if not title or not isinstance(title, str) or not title.strip():
        raise HTTPException(400, "title 必填")
    result = create_project(payload, _PACKAGE_ROOT)
    global _project_root
    _project_root = Path(result["project_root"])
    # 重启 watcher 监控新项目
    _watcher.stop()
    _watcher.start(_project_root / ".webnovel", asyncio.get_event_loop())
    return result

@app.get("/api/projects")
def api_list_projects():
    return list_projects()

@app.post("/api/project/switch")
def api_switch_project(payload: dict):
    target = payload.get("path", "")
    result = switch_project(target, _project_root)
    if result.get("success"):
        global _project_root
        _project_root = Path(result["project_root"])
        _watcher.stop()
        _watcher.start(_project_root / ".webnovel", asyncio.get_event_loop())
    return result
```

- [x] **Step 3: 运行测试（project 相关应变绿）**

Run: `cd webnovel-writer && python -m pytest dashboard/tests/test_new_apis.py -k "project" -v`
Expected: PASS

- [x] **Step 4: Commit**

```bash
git add dashboard/project_service.py dashboard/app.py
git commit -m "feat(api): add project create/list/switch APIs"
```

---

## Task 4: Backend — 大纲树与最近动态 API

**Files:**
- Modify: `webnovel-writer/dashboard/workbench_service.py` (新增 `build_outline_tree`)
- Modify: `webnovel-writer/dashboard/app.py` (新增 2 个路由 + 全局 `_recent_activities` 缓存 + 写入逻辑)

### 大纲目录实际结构（平铺，非子目录）
- `大纲/总纲.md` — 初始化生成
- `大纲/爽点规划.md` — 初始化生成
- `大纲/第1卷-详细大纲.md` — AI 规划生成（平铺文件，文件名模式 `第N卷-详细大纲.md`）

### _recent_activities 写入时机

- `TaskService.mark_completed()` / `mark_failed()` 时追加一条 `task_completed` / `task_failed` 活动
- `FileWatcher` 检测到文件变更时追加一条 `file_modified` 活动
- 在 app.py 中通过调用 `_recent_activities.append()` 实现，不需要修改 TaskService 和 FileWatcher 的接口

- [x] **Step 1: 在 `workbench_service.py` 中新增 `build_outline_tree()`**

实现逻辑：
1. 扫描 `大纲/` 目录下所有 .md 文件 → `files` 列表
2. 从 state.json 读取 `project_info.target_chapters`（默认 600）
3. 每卷 50 章，计算 `total_volumes`
4. 匹配 `大纲/第N卷-详细大纲.md` 判断 `has_outline`
5. 用正则 `r"第(\d+)卷"` 从文件名提取卷号
6. 空项目（大纲目录不存在）返回空 files + 根据 target_chapters 计算的 volumes

- [x] **Step 2: 在 `app.py` 中新增路由和活动缓存**

```python
from .workbench_service import build_outline_tree  # 新增 import

# 全局变量区新增
_recent_activities: list[dict] = []

# 路由
@app.get("/api/outline/tree")
def api_outline_tree():
    return build_outline_tree(_get_project_root())

@app.get("/api/recent-activity")
def api_recent_activity():
    return {"activities": list(_recent_activities[-50:])}
```

在 TaskService 的 `mark_completed`/`mark_failed` 后追加活动记录（在路由层或 app.py 中 hook）。

- [x] **Step 3: 运行测试（全部应变绿）**

Run: `cd webnovel-writer && python -m pytest dashboard/tests/test_new_apis.py -v`
Expected: 全部 PASS

- [x] **Step 4: Commit**

```bash
git add dashboard/workbench_service.py dashboard/app.py
git commit -m "feat(api): add GET /api/outline/tree and GET /api/recent-activity"
```

---

## Task 5: Frontend — API 层与数据模型更新

**Files:**
- Modify: `webnovel-writer/dashboard/frontend/src/api.js`
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/data.js`

- [ ] **Step 1: 在 `api.js` 中新增 API 函数**

在文件末尾（`subscribeSSE` 之后）追加（先检查是否有重复，如已有 `fetchProjectInfo` 则跳过）：
```javascript
// --- 新增 API（创建向导 & 项目管理）---
export function fetchGenres() {
    return fetchJSON('/api/genres');
}
export function fetchGoldenFingerTypes() {
    return fetchJSON('/api/golden-finger-types');
}
export function createProject(data) {
    return postJSON('/api/project/create', data);
}
export function fetchProjects() {
    return fetchJSON('/api/projects');
}
export function switchProject(path) {
    return postJSON('/api/project/switch', { path });
}
export function fetchOutlineTree() {
    return fetchJSON('/api/outline/tree');
}
export function fetchRecentActivity() {
    return fetchJSON('/api/recent-activity');
}
```

- [ ] **Step 2: 更新 `data.js`**

修改 `WORKBENCH_PAGES` 数组（顺序从 `[overview, chapters, outline, settings]` 改为 `[overview, outline, settings, chapters]`），添加序号：
```javascript
export const WORKBENCH_PAGES = [
  { id: 'overview', label: '总览', number: '①' },
  { id: 'outline', label: '大纲', number: '②' },
  { id: 'settings', label: '设定', number: '③' },
  { id: 'chapters', label: '章节', number: '④' },
]
```

新增项目状态判断：
```javascript
export function getProjectStatus(projectInfo) {
  if (!projectInfo) return 'no-project';
  const pi = projectInfo.project_info || projectInfo.project || {};
  if (!pi.title || !pi.genre) return 'incomplete';
  return 'ready';
}
```

新增"下一步建议"计算：
```javascript
export function getNextSuggestion(summary) {
  if (!summary) return null;
  const progress = summary.progress || {};
  const chapter = progress.current_chapter || 0;
  if (chapter === 0) {
    return { text: '开始写第1章', action: 'write_chapter', params: { chapter: 1 } };
  }
  return { text: `写第${chapter + 1}章`, action: 'write_chapter', params: { chapter: chapter + 1 } };
}
```

新增实体类型映射（index.db 的 type 值 → 前端显示名和图标）：
```javascript
export const ENTITY_TYPE_MAP = {
  '角色': { label: '人物', icon: '👤' },
  '势力': { label: '势力', icon: '🏛' },
  '地点': { label: '地点', icon: '📍' },
  '物品': { label: '物品', icon: '💎' },
  '招式': { label: '招式', icon: '⚔️' },
};
export const ENTITY_FILTER_CATEGORIES = ['全部', '人物', '势力', '地点', '物品', '招式'];
// 前端筛选标签的 type 映射（显示名 → 数据库 type 值）
export const FILTER_TO_DB_TYPE = {
  '人物': '角色',
  '势力': '势力',
  '地点': '地点',
  '物品': '物品',
  '招式': '招式',
};
```

更新 `resolveTargetPage()` 确保与新页面顺序一致。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api.js frontend/src/workbench/data.js
git commit -m "feat(frontend): add new API functions, data model, entity type mapping"
```

---

## Task 6: Frontend — App.jsx 重构集成（骨架优先）

**Files:**
- Rewrite: `webnovel-writer/dashboard/frontend/src/App.jsx`

**策略**：先做 App.jsx 骨架，定义全局状态和 props 传递接口，后续 Task 7-12 的页面组件才能有数据源。App.jsx 先渲染空壳子（页面组件暂用 placeholder），后续 Task 逐个替换为真实组件。

### 核心变更
1. 移除 `RightSidebar` 固定布局 → 预留 `AIAssistant` 浮动组件位置
2. 移除 `OnboardingGuide` → 新设计已有步骤引导
3. 新增项目状态管理（无/未完成/就绪）
4. 新增 `CreateWizard` 弹窗触发
5. 新增 `ProjectSwitcher` 数据加载
6. SSE 文件变更冲突处理
7. 页面跳转规则实现

### 新增全局状态
```javascript
const [projectStatus, setProjectStatus] = useState('loading') // 'loading'|'no-project'|'incomplete'|'ready'
const [projectInfo, setProjectInfo] = useState(null)
const [projects, setProjects] = useState([])
const [showWizard, setShowWizard] = useState(false)
const [wizardPrefill, setWizardPrefill] = useState(null)
const [aiOpen, setAiOpen] = useState(false)
const [recentActivities, setRecentActivities] = useState([])
```

### SSE 文件变更冲突处理
在 SSE `file.changed` 事件处理中：
```javascript
if (changedFile === pageState[activePage]?.selectedPath) {
  if (pageState[activePage]?.dirty) {
    // React state 弹出确认对话框
    setConflictDialog({ visible: true, file: changedFile });
  } else {
    // 静默重新加载
    reloadCurrentFile();
  }
}
```

使用 React 组件渲染确认对话框（非 `window.confirm`），包含"重新加载"和"保留我的修改"两个按钮。

### 布局结构改为全宽
```jsx
<div className="workbench-shell">
  <TopBar model={topBarModel} ... projects={projects} ... />
  <div className="workbench-body">
    <div className="workbench-main">
      {/* 各页面组件，先用 placeholder */}
      {activePage === 'overview' && <p>Overview placeholder</p>}
      {/* ... */}
    </div>
  </div>
  {/* AIAssistant 浮动组件位置，先用 placeholder */}
  {showWizard && <p>Wizard placeholder</p>}
  {/* 冲突确认对话框 */}
  {conflictDialog.visible && <ConflictDialog ... />}
</div>
```

- [ ] **Step 1: 重写 App.jsx**

保留核心逻辑（SSE 订阅、任务管理、聊天），但改变布局结构：
- 移除 `.workbench-body > .workbench-main + RightSidebar` 双栏布局
- 改为 `.workbench-body > 全宽 .workbench-main`
- 页面组件先用 placeholder，后续 Task 逐个替换

新增初始化逻辑：
```javascript
useEffect(() => {
  fetchProjectInfo()
    .then(info => { setProjectInfo(info); setProjectStatus(getProjectStatus(info)); })
    .catch(() => setProjectStatus('no-project'));
  fetchProjects().then(r => setProjects(r.projects || []));
  fetchRecentActivity().then(r => setRecentActivities(r.activities || []));
}, []);
```

- [ ] **Step 2: 验证构建**

Run: `cd webnovel-writer/dashboard/frontend && npm run build`
Expected: 构建成功（页面显示 placeholder）

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "refactor(frontend): restructure App.jsx with project state, remove RightSidebar layout"
```

---

## Task 7: Frontend — TopBar + ProjectSwitcher + AIAssistant

**Files:**
- Rewrite: `webnovel-writer/dashboard/frontend/src/workbench/TopBar.jsx`
- Create: `webnovel-writer/dashboard/frontend/src/workbench/ProjectSwitcher.jsx`
- Create: `webnovel-writer/dashboard/frontend/src/workbench/AIAssistant.jsx`

这三个组件互相独立，可并行开发。

### TopBar 设计（spec §全局组件·顶栏）
- 左侧：页面导航标签 ①总览 / ②大纲 / ③设定 / ④章节
- 右侧：项目切换器（醒目样式）；无项目时显示"选择项目 ▾"

### AIAssistant 设计（spec §全局组件·AI助手）
- 右下角浮动 💬 按钮，全局可用
- 默认收起，点击展开对话框
- 对话框包含：消息区 + 动作卡 + 输入框
- 逻辑复用现有 `RightSidebar.jsx` 的聊天、动作卡、任务面板逻辑，改为浮动定位

- [ ] **Step 1: 创建 ProjectSwitcher 组件**

props: `{ projects, currentPath, onSwitch, onCreateNew }`
- 下拉显示项目列表（名称 + 题材 + 当前章节）
- 底部"+ 创建新小说"选项
- 无项目时显示"暂无项目"

- [ ] **Step 2: 重写 TopBar 组件**

props: `{ model, connected, onSelectPage, projects, currentProjectPath, onSwitchProject, onCreateNew }`
- 左侧渲染带序号的标签按钮（从 `model.pages` 读取，使用 `number` 字段）
- 右侧渲染 `<ProjectSwitcher />`
- 当前标签高亮

- [ ] **Step 3: 创建 AIAssistant 组件**

props: `{ chatMessages, suggestedActions, currentTask, chatPending, onSendMessage, onRunAction, onRetryAction, onNavigateToPage, visible, onToggle }`

组件结构：
1. 浮动按钮（position:fixed, right:24px, bottom:24px, z-index:1000）
2. 展开的对话框（position:fixed, right:24px, bottom:80px, width:380px, max-height:500px, z-index:1000）
3. 对话框内部：消息列表 + 动作卡 + 输入框

从 `RightSidebar.jsx` 迁移聊天、动作卡、任务面板的 JSX 和逻辑。

- [ ] **Step 4: 在 App.jsx 中替换 placeholder**

将 TopBar 替换为新版（带 ProjectSwitcher），将 AIAssistant 浮动组件加入布局。

- [ ] **Step 5: 验证构建**

Run: `cd webnovel-writer/dashboard/frontend && npm run build`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/workbench/TopBar.jsx frontend/src/workbench/ProjectSwitcher.jsx frontend/src/workbench/AIAssistant.jsx frontend/src/App.jsx
git commit -m "feat(frontend): add TopBar with numbered tabs, ProjectSwitcher, floating AIAssistant"
```

---

## Task 8: Frontend — 总览页重写

**Files:**
- Rewrite: `webnovel-writer/dashboard/frontend/src/workbench/OverviewPage.jsx`

### 3 种状态（spec §页面设计·总览页）+ loading + error

**空状态（无项目）**：
- 居中欢迎文案 + "＋ 创建新小说"大按钮

**未完成设置**：
- 步骤引导条（橙色高亮）
- 项目概况（已有字段）
- 提示条"项目设置尚未完成" + "继续设置"按钮

**项目就绪**：
- 步骤引导条（起步✓ → 写作中 → 审查）
- "下一步"行动卡
- 项目概况 + 最近动态（并排）

**Loading 状态**：显示骨架屏或 spinner
**Error 状态**：显示错误信息 + 重试按钮

- [ ] **Step 1: 重写 OverviewPage**

props: `{ summary, loading, loadError, onRetry, projectStatus, projectInfo, recentActivities, onCreateNew, onContinueSetup, onNavigateToPage, onRunAction }`

根据 `projectStatus` 渲染不同视图：
- `'loading'` → LoadingState
- `'no-project'` → EmptyState
- `'incomplete'` → IncompleteState
- `'ready'` → ReadyState
- `loadError` → ErrorState

- [ ] **Step 2: 在 App.jsx 中替换 OverviewPage placeholder**

- [ ] **Step 3: 验证构建**

Run: `cd webnovel-writer/dashboard/frontend && npm run build`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/workbench/OverviewPage.jsx frontend/src/App.jsx
git commit -m "feat(frontend): redesign OverviewPage with 3 project states + loading/error"
```

---

## Task 9: Frontend — 创建向导弹窗

**Files:**
- Create: `webnovel-writer/dashboard/frontend/src/workbench/CreateWizard.jsx`

### 3 步向导（spec §创建向导）

**第1步：基本信息** — 书名(必填)、题材(标签多选)、目标字数(默认200万)、目标章节数(默认600)、核心卖点(可选)
**第2步：主角设定（可选）** — 主角名字、金手指名称、金手指类型(含"无金手指")、底部"跳过此步→"
**第3步：确认创建** — 信息摘要 + "创建项目"按钮

- [ ] **Step 1: 创建 CreateWizard 组件**

props: `{ open, onClose, onCreated, genres, goldenFingerTypes, prefillData }`

状态管理：
- `step` (1|2|3)
- `formData` — 所有表单字段
- `creating` — 提交中 loading
- `error` — 创建失败信息

第1步表单校验：书名必填，题材至少选 1 个
第2步可跳过："跳过此步→" 链接跳到第3步
第3步提交：调用 `createProject(formData)`，成功后调用 `onCreated(result)`，失败显示 error

题材标签渲染为可点击的 tag，选中高亮。金手指类型渲染为 radio 选项，"无金手指"用绿色虚线边框突出。

弹窗使用 `position:fixed` + `z-index:2000` 覆盖全屏，带半透明遮罩。

- [ ] **Step 2: 在 App.jsx 中替换 Wizard placeholder**

- [ ] **Step 3: 验证构建**

Run: `cd webnovel-writer/dashboard/frontend && npm run build`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/workbench/CreateWizard.jsx frontend/src/App.jsx
git commit -m "feat(frontend): add 3-step create wizard modal"
```

---

## Task 10: Frontend — 大纲页重写

**Files:**
- Rewrite: `webnovel-writer/dashboard/frontend/src/workbench/OutlinePage.jsx`

### 设计（spec §页面设计·大纲页）
- 左侧 220px：树形缩进列表（总纲 → 第N卷 → 操作入口）
- 右侧：大编辑区
- 按钮：保存、生成卷纲🔒、生成章纲🔒

### 数据来源
- `GET /api/outline/tree` — 返回 files + volumes
- `GET /api/files/read` — 加载文件内容
- `POST /api/files/save` — 保存修改

- [ ] **Step 1: 重写 OutlinePage**

初始化加载 `fetchOutlineTree()` 获取树数据。loading 时显示 spinner。

左侧树渲染逻辑：
1. 总纲节点（点击加载 `大纲/总纲.md`）
2. 爽点规划节点（点击加载 `大纲/爽点规划.md`）
3. 每卷节点：
   - `has_outline=true` → ✓ + 卷名，点击加载对应 .md
   - `has_outline=false` → "＋ 生成第N卷大纲"按钮（触发 AI 助手）

编辑区复用现有保存/dirty 逻辑。禁用按钮用虚线边框 + 🔒 + tooltip。

- [ ] **Step 2: 在 App.jsx 中替换 OutlinePage placeholder**

- [ ] **Step 3: 验证构建**

Run: `cd webnovel-writer/dashboard/frontend && npm run build`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/workbench/OutlinePage.jsx frontend/src/App.jsx
git commit -m "feat(frontend): redesign OutlinePage with tree sidebar"
```

---

## Task 11: Frontend — 设定页重写

**Files:**
- Rewrite: `webnovel-writer/dashboard/frontend/src/workbench/SettingPage.jsx`

### 设计（spec §页面设计·设定页）
- 左侧 220px：卡片式实体列表 + 分类筛选标签（含数量）
- 右侧：大编辑区
- 按钮：保存、检查冲突🔒

### 数据来源
- `GET /api/entities?type=` — 实体列表（type 值：`角色`/`势力`/`地点`/`物品`/`招式`，前端显示为"人物/势力/地点/物品/招式"）
- `GET /api/files/read` — 通过实体关联的文件路径加载内容
- `POST /api/files/save` — 保存修改

### 实体类型映射（index.db → 前端显示）

| index.db type | 前端 label | 图标 | 筛选标签 |
|---------------|-----------|------|----------|
| 角色 | 人物 | 👤 | 人物(N) |
| 势力 | 势力 | 🏛 | 势力(N) |
| 地点 | 地点 | 📍 | 地点(N) |
| 物品 | 物品 | 💎 | 物品(N) |
| 招式 | 招式 | ⚔️ | 招式(N) |

API 调用时的 type 参数使用数据库原值（如 `?type=角色`），前端筛选标签使用映射后的中文显示名。

- [ ] **Step 1: 重写 SettingPage**

筛选标签：全部(N) / 人物(N) / 势力(N) / 地点(N) / 物品(N) / 招式(N)
数量从 `GET /api/entities` 全量返回后前端按 type 统计（或分次请求 `?type=角色` 等）。

卡片组件：实体名（图标按 `ENTITY_TYPE_MAP`）+ 一行摘要（`desc` 字段，text-overflow:ellipsis）

编辑区复用现有保存/dirty 逻辑。loading 时显示 spinner。

- [ ] **Step 2: 在 App.jsx 中替换 SettingPage placeholder**

- [ ] **Step 3: 验证构建**

Run: `cd webnovel-writer/dashboard/frontend && npm run build`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/workbench/SettingPage.jsx frontend/src/App.jsx
git commit -m "feat(frontend): redesign SettingPage with card sidebar, entity type mapping, filter tags"
```

---

## Task 12: Frontend — 章节页重写

**Files:**
- Rewrite: `webnovel-writer/dashboard/frontend/src/workbench/ChapterPage.jsx`

### 设计（spec §页面设计·章节页）

**空状态**：左侧"还没有章节"，右侧"开始写第1章吧！" + 按钮

**有章节时**：
- 左侧 140px（可折叠）：倒序章节列表 + 底部"＋ 写第N章"
- 右侧编辑区：顶部文件路径 + 专注模式按钮(绿色)，底部状态栏 + 字数统计
- **专注模式**：隐藏左侧列表和 AI 助手，全屏写作。ESC 或右上角退出

### 数据来源
- `GET /api/chapters` — 章节列表（从 index.db）
- `GET /api/files/tree` — 正文目录文件列表
- `GET /api/files/read` / `POST /api/files/save` — 文件读写

- [ ] **Step 1: 重写 ChapterPage**

新增状态：
- `focusMode` (boolean) — 专注模式
- `wordCount` (number) — 字数统计（编辑区 onChange 实时计算）
- `sidebarCollapsed` (boolean) — 左侧折叠

章节列表倒序：`chapters.slice().reverse()`

字数统计：`draft.replace(/\s/g, '').length`（中文字数统计不含空白）

专注模式：通过回调 `onFocusModeChange(true)` 通知 App.jsx 隐藏 AI 助手。ESC 键盘事件监听退出。CSS class 控制布局变化。

- [ ] **Step 2: 在 App.jsx 中替换 ChapterPage placeholder**

- [ ] **Step 3: 验证构建**

Run: `cd webnovel-writer/dashboard/frontend && npm run build`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/workbench/ChapterPage.jsx frontend/src/App.jsx
git commit -m "feat(frontend): redesign ChapterPage with reverse list and focus mode"
```

---

## Task 13: Frontend — CSS 重构

**Files:**
- Modify: `webnovel-writer/dashboard/frontend/src/index.css`

这是关键 Task——所有新 UI 组件需要样式支撑，但现有 CSS 有大量需要改动的部分。

### 需要修改的 CSS

| 选择器 | 改动 |
|--------|------|
| `.workbench-body` | `grid-template-columns: minmax(0, 1fr) 320px` → `minmax(0, 1fr)`（移除右侧栏） |
| `.workbench-right` | 删除（被浮动 AIAssistant 替代） |
| `.workbench-main` | 确保全宽，移除与右侧栏相关的 margin/padding |

### 需要新增的 CSS

| 选择器 | 说明 |
|--------|------|
| `.ai-fab` | 浮动 💬 按钮（fixed, right:24px, bottom:24px, 56x56px, 圆形, z-index:1000） |
| `.ai-dialog` | 展开的对话框（fixed, right:24px, bottom:80px, width:380px, max-height:500px, 圆角, 阴影, z-index:1000） |
| `.ai-dialog-messages` | 消息区（flex:1, overflow-y:auto） |
| `.ai-dialog-input` | 输入区（固定底部） |
| `.project-switcher` | 下拉菜单（absolute, 与顶栏对齐） |
| `.create-wizard-overlay` | 全屏遮罩（fixed, z-index:2000, 半透明黑） |
| `.create-wizard-modal` | 弹窗主体（居中, max-width:600px, z-index:2001） |
| `.create-wizard-step` | 步骤指示器 |
| `.genre-tag` | 题材标签（inline-block, padding, 圆角, cursor:pointer） |
| `.genre-tag.selected` | 选中态（高亮背景） |
| `.gf-option` | 金手指选项（radio 样式） |
| `.gf-option.none` | "无金手指"特殊样式（绿色虚线边框） |
| `.focus-mode .workbench-sidebar` | 专注模式隐藏左侧栏（display:none） |
| `.focus-mode .ai-fab` | 专注模式隐藏 AI 按钮（display:none） |
| `.outline-tree` | 大纲树（缩进列表） |
| `.outline-tree-item` | 树节点（padding-left 按层级递增） |
| `.entity-card` | 实体卡片（hover 高亮） |
| `.entity-filter-tag` | 筛选标签（含数量） |
| `.step-progress-bar` | 步骤引导条 |
| `.step-progress-item` | 引导条单项 |
| `.step-progress-item.active` | 当前步骤（发光效果） |
| `.step-progress-item.completed` | 已完成步骤 |
| `.next-step-card` | "下一步"行动卡（醒目样式 + 发光按钮） |
| `.chapter-word-count` | 字数统计（底部状态栏） |
| `.disabled-action-btn` | 禁用按钮（虚线边框 + 🔒 + tooltip） |

### 需要删除/注释的 CSS
- `.workbench-right` 相关样式（约 200 行）
- `.onboarding-*` 相关样式（约 100 行）

- [ ] **Step 1: 修改现有 CSS**

修改 `.workbench-body` grid、删除 `.workbench-right` 样式。

- [ ] **Step 2: 新增所有新组件样式**

按上方表格逐一添加。

- [ ] **Step 3: 删除/注释旧组件样式**

删除 `.workbench-right` 和 `.onboarding-*` 相关样式。

- [ ] **Step 4: 验证构建**

Run: `cd webnovel-writer/dashboard/frontend && npm run build`
Expected: 构建成功，浏览器打开页面不再显示旧右侧栏

- [ ] **Step 5: Commit**

```bash
git add frontend/src/index.css
git commit -m "refactor(css): remove right sidebar layout, add floating AI/wizard/focus mode styles"
```

---

## Task 14: Frontend — 清理旧组件

**Files:**
- Delete: `frontend/src/workbench/RightSidebar.jsx`
- Delete: `frontend/src/workbench/OnboardingGuide.jsx`

- [ ] **Step 1: 删除旧文件**

确认 App.jsx 中已无 RightSidebar 和 OnboardingGuide 的 import（Task 6 已移除）。直接删除两个文件。

- [ ] **Step 2: 验证构建无错误**

Run: `cd webnovel-writer/dashboard/frontend && npm run build`
Expected: 构建成功，无 "import not found" 错误

- [ ] **Step 3: Commit**

```bash
git rm frontend/src/workbench/RightSidebar.jsx frontend/src/workbench/OnboardingGuide.jsx
git commit -m "refactor(frontend): remove old RightSidebar and OnboardingGuide"
```

---

## Task 15: 全量集成验证

- [ ] **Step 1: 后端测试**

Run: `cd webnovel-writer && python -m pytest dashboard/tests/ -v`
Expected: 全部 PASS

- [ ] **Step 2: 前端构建**

Run: `cd webnovel-writer/dashboard/frontend && npm run build`
Expected: 构建成功

- [ ] **Step 3: 启动前后端联调**

启动后端（需要一个项目目录）：
```bash
cd webnovel-writer && python -m dashboard --project-root /path/to/test-project
```

启动前端开发服务器：
```bash
cd webnovel-writer/dashboard/frontend && npm run dev
```

浏览器访问 http://localhost:5173，检查：
1. 总览页空状态 → "创建新小说"按钮可见
2. 点击创建 → 弹出创建向导，题材列表加载 37 项
3. 金手指类型含"无金手指"（绿色虚线）
4. 创建项目成功后跳转到总览页（就绪状态）
5. 大纲页树形结构正确渲染
6. 设定页卡片列表和筛选标签（人物/势力/地点/物品/招式）
7. 章节页倒序列表和专注模式（ESC 退出）
8. AI 助手浮动按钮可展开
9. 项目切换器显示项目列表
10. SSE 文件变更：编辑区脏状态弹确认，非脏状态静默刷新
11. 字数统计实时计算

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete web workbench redesign (Phase 1)"
```
