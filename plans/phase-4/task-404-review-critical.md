# Task 404: Step 7 critical 问题决策 + Step 8 收尾

## 目标

实现 ReviewSkillHandler 的 Step 7（处理关键问题，confirm 模式）和 Step 8（收尾，auto）。

## 涉及文件

- `webnovel-writer/dashboard/skill_handlers/review_handler.py`（修改 execute_step + validate_input）

## 依赖

- task-403（Step 5-6 完成后审查指标已落库）

## 前置知识

context 中已有的数据：
- `context["review_summary"]` — 含 critical_issues 列表
- `context["review_report"]` — 审查报告
- `context["all_chapter_results"]` — 各章审查结果
- `context["project_root"]` — 项目根目录

Step 7 是 `confirm` 模式：
- 如果有 critical 问题 → 展示问题 + 修复方案选项 → 用户选择
- 如果无 critical 问题 → 自动跳过（通过 output_data 标记）

## 规格

### execute_step（Step 7 / Step 8）

```python
async def execute_step(self, step: StepState, context: dict) -> dict:
    if step.step_id == "step_7":
        return await self._handle_critical_issues(context)
    if step.step_id == "step_8":
        return await self._finalize(context)
    # ... 其他步骤
```

### _handle_critical_issues（Step 7）

```python
async def _handle_critical_issues(self, context: dict) -> dict:
    """处理 critical 问题。

    如果有 critical 问题：展示问题 + 修复方案 → 等待用户决策。
    如果无 critical 问题：标记 auto_resolved，SkillRunner 自动 advance。
    """
    summary = context.get("review_summary", {})
    critical_issues = summary.get("critical_issues", [])

    if not critical_issues:
        # 无 critical 问题，自动通过
        return {
            "has_critical": False,
            "auto_resolved": True,
            "instruction": "无关键问题，自动通过",
        }

    # 为每个 critical 问题生成修复方案选项
    issues_with_options = []
    for issue in critical_issues:
        options = self._generate_fix_options(issue)
        issues_with_options.append({
            "issue": issue,
            "options": options,
        })

    context["critical_issues_with_options"] = issues_with_options

    return {
        "has_critical": True,
        "auto_resolved": False,
        "requires_input": True,  # SkillRunner 检测此字段，等待用户输入
        "issues_with_options": issues_with_options,
        "instruction": f"发现 {len(critical_issues)} 个关键问题，请选择修复方案",
    }

def _generate_fix_options(self, issue: dict) -> list[dict]:
    """为 critical 问题生成修复方案选项。

    每个问题提供 2-3 个修复方案：
    - 方案 A：直接修复（AI 自动修改）
    - 方案 B：标记忽略（用户确认可接受）
    - 方案 C：手动修复（用户自行处理）
    """
    return [
        {
            "id": "auto_fix",
            "label": "AI 自动修复",
            "description": f"自动修改相关段落以解决：{issue.get('message', '')}",
        },
        {
            "id": "ignore",
            "label": "标记为可接受",
            "description": "确认此问题不影响阅读体验，标记为已知",
        },
        {
            "id": "manual",
            "label": "稍后手动修复",
            "description": "记录到待办列表，稍后手动处理",
        },
    ]
```

### validate_input（Step 7）

```python
async def validate_input(self, step: StepState, data: dict) -> str | None:
    if step.step_id == "step_7":
        decisions = data.get("decisions", [])
        critical_count = len(
            self.context.get("critical_issues_with_options", [])
            if hasattr(self, 'context') else []
        )

        # decisions 格式：[{"issue_index": 0, "option_id": "auto_fix"}, ...]
        if not decisions:
            return "请对每个关键问题做出决策"

        # 验证每个决策的 option_id 合法
        valid_options = {"auto_fix", "ignore", "manual"}
        for d in decisions:
            if d.get("option_id") not in valid_options:
                return f"无效的修复方案：{d.get('option_id')}"

        return None
    # ... 其他步骤
```

### _finalize（Step 8）

```python
async def _finalize(self, context: dict) -> dict:
    """收尾：保存审查报告文件 + 处理用户决策。"""
    project_root = Path(context.get("project_root", "."))
    report = context.get("review_report", {})
    chapter_start = context.get("chapter_start", 1)
    chapter_end = context.get("chapter_end", chapter_start)

    # 1. 保存审查报告到文件
    report_dir = project_root / ".webnovel" / "审查报告"
    report_dir.mkdir(parents=True, exist_ok=True)

    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"review_{chapter_start}-{chapter_end}_{timestamp}.json"
    report_path = report_dir / report_filename
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 2. 处理 critical 问题决策
    decisions = context.get("critical_decisions", [])
    manual_todos = []
    for d in decisions:
        if d.get("option_id") == "manual":
            manual_todos.append(d.get("issue", {}))

    # 3. 如果有"稍后手动修复"的问题，写入待办
    if manual_todos:
        todo_path = project_root / ".webnovel" / "review_todos.json"
        existing_todos = []
        if todo_path.exists():
            try:
                existing_todos = json.loads(todo_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        existing_todos.extend(manual_todos)
        todo_path.write_text(
            json.dumps(existing_todos, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return {
        "report_saved": str(report_path),
        "manual_todos": len(manual_todos),
        "instruction": f"审查完成，报告已保存至 {report_filename}",
    }
```

### 用户决策数据结构

```python
# 前端提交的决策数据
{
    "decisions": [
        {
            "issue_index": 0,
            "option_id": "auto_fix",  # auto_fix | ignore | manual
            "issue": {  # 原始问题信息（前端回传）
                "severity": "critical",
                "message": "主角力量等级超出当前设定上限",
                "chapter": 3,
                "dimension": "设定一致性",
            },
        },
    ]
}
```

## TDD 验收

- Happy path：有 critical 问题 → Step 7 展示选项 → 用户选择 auto_fix → Step 8 保存报告
- Edge case 1：无 critical 问题 → Step 7 auto_resolved=True → 自动进入 Step 8
- Edge case 2：用户选择 "manual" → Step 8 写入 review_todos.json
- Error case：validate_input 收到无效 option_id → 返回错误信息
