# Task 403: Step 4 审查报告生成 + Step 5-6 落库

## 目标

实现 ReviewSkillHandler 的 Step 4（生成审查报告，confirm）、Step 5（保存审查指标到 index.db）、Step 6（写回审查记录到 state.json）。

## 涉及文件

- `webnovel-writer/dashboard/skill_handlers/review_handler.py`（修改 execute_step）
- `webnovel-writer/dashboard/skill_handlers/review_storage.py`（新建，落库逻辑）

## 依赖

- task-402（Step 3 完成后 context 包含 all_chapter_results / review_summary）

## 前置知识

context 中已有的数据（来自 Step 3）：
- `context["all_chapter_results"]` — {章节号: [6维结果]} dict
- `context["review_summary"]` — 汇总（avg_score/dimension_avg/critical_issues/all_issues）
- `context["project_root"]` — 项目根目录
- `context["chapter_start"]` / `context["chapter_end"]` — 审查范围

index.db 是 SQLite 数据库，位于 `{project_root}/.webnovel/index.db`，用于存储审查指标历史。

## 规格

### execute_step（Step 4/5/6）

```python
async def execute_step(self, step: StepState, context: dict) -> dict:
    if step.step_id == "step_4":
        return await self._generate_report(context)
    if step.step_id == "step_5":
        return await self._save_metrics(context)
    if step.step_id == "step_6":
        return await self._writeback_state(context)
    # ... 其他步骤
```

### _generate_report（Step 4）

```python
async def _generate_report(self, context: dict) -> dict:
    """生成结构化审查报告。

    报告包含：
    1. 总评分（6 维雷达图数据）
    2. 各章详细评分
    3. 问题列表（按优先级排序）
    4. 改进建议
    """
    summary = context.get("review_summary", {})
    all_results = context.get("all_chapter_results", {})

    # 生成报告结构
    report = {
        "overall": {
            "avg_score": summary.get("avg_score", 0),
            "dimension_scores": summary.get("dimension_avg", {}),
            "total_issues": summary.get("total_issues", 0),
            "verdict": self._get_verdict(summary.get("avg_score", 0)),
        },
        "chapters": {},
        "priority_fixes": [],
        "suggestions": [],
    }

    # 各章详情
    for ch_num, results in all_results.items():
        ch_score = sum(r["score"] for r in results) / len(results) if results else 0
        report["chapters"][ch_num] = {
            "score": round(ch_score, 1),
            "dimensions": {r["dimension"]: r["score"] for r in results},
            "issues_count": sum(len(r.get("issues", [])) for r in results),
        }

    # 优先修复列表（critical + high）
    critical = summary.get("critical_issues", [])
    high = summary.get("high_issues", [])
    report["priority_fixes"] = critical + high

    # 改进建议
    report["suggestions"] = self._generate_suggestions(summary)

    context["review_report"] = report

    return {
        "report": report,
        "instruction": "请确认审查报告",
    }

def _get_verdict(self, avg_score: float) -> str:
    """根据平均分给出总评。"""
    if avg_score >= 8.5:
        return "优秀"
    elif avg_score >= 7.0:
        return "良好"
    elif avg_score >= 6.0:
        return "合格"
    else:
        return "需要修改"

def _generate_suggestions(self, summary: dict) -> list[str]:
    """根据审查结果生成改进建议。"""
    suggestions = []
    dim_avg = summary.get("dimension_avg", {})

    if dim_avg.get("爽点密度", 10) < 6:
        suggestions.append("增加情节转折和情绪波动，提升爽点密度")
    if dim_avg.get("设定一致性", 10) < 6:
        suggestions.append("检查设定矛盾，确保力量体系和世界观一致")
    if dim_avg.get("节奏比例", 10) < 6:
        suggestions.append("调整对话/描写/动作比例，避免大段纯叙述")
    if dim_avg.get("人物OOC", 10) < 6:
        suggestions.append("检查角色行为是否符合已建立的性格特征")
    if dim_avg.get("叙事连贯性", 10) < 6:
        suggestions.append("检查前后文逻辑，消除跳跃和矛盾")
    if dim_avg.get("追读力", 10) < 6:
        suggestions.append("强化章末钩子，增加悬念和期待感")

    return suggestions
```

### review_storage.py

```python
"""ReviewStorage — 审查指标落库。"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime


class ReviewStorage:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.db_path = self.project_root / ".webnovel" / "index.db"

    def save_metrics(self, chapter_results: dict, summary: dict) -> dict:
        """将审查指标写入 index.db。

        表结构：
        CREATE TABLE IF NOT EXISTS review_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chapter INTEGER NOT NULL,
            dimension TEXT NOT NULL,
            score REAL NOT NULL,
            issues_count INTEGER DEFAULT 0,
            reviewed_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS review_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chapter_start INTEGER NOT NULL,
            chapter_end INTEGER NOT NULL,
            avg_score REAL NOT NULL,
            total_issues INTEGER DEFAULT 0,
            reviewed_at TEXT NOT NULL
        );
        """
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # 创建表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter INTEGER NOT NULL,
                dimension TEXT NOT NULL,
                score REAL NOT NULL,
                issues_count INTEGER DEFAULT 0,
                reviewed_at TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter_start INTEGER NOT NULL,
                chapter_end INTEGER NOT NULL,
                avg_score REAL NOT NULL,
                total_issues INTEGER DEFAULT 0,
                reviewed_at TEXT NOT NULL
            )
        """)

        now = datetime.now().isoformat()

        # 写入各章各维度指标
        for ch_num, results in chapter_results.items():
            for r in results:
                cursor.execute(
                    "INSERT INTO review_metrics (chapter, dimension, score, issues_count, reviewed_at) VALUES (?, ?, ?, ?, ?)",
                    (int(ch_num), r["dimension"], r["score"], len(r.get("issues", [])), now),
                )

        # 写入审查会话
        chapters = sorted(chapter_results.keys())
        cursor.execute(
            "INSERT INTO review_sessions (chapter_start, chapter_end, avg_score, total_issues, reviewed_at) VALUES (?, ?, ?, ?, ?)",
            (min(chapters), max(chapters), summary.get("avg_score", 0), summary.get("total_issues", 0), now),
        )

        conn.commit()
        session_id = cursor.lastrowid
        conn.close()

        return {"session_id": session_id, "metrics_saved": True}

    def writeback_state(self, chapter_results: dict) -> dict:
        """更新 state.json 中的审查记录。"""
        state_path = self.project_root / ".webnovel" / "state.json"
        state = {}
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass

        if "chapters" not in state:
            state["chapters"] = {}

        now = datetime.now().isoformat()

        for ch_num, results in chapter_results.items():
            ch_key = str(ch_num)
            if ch_key not in state["chapters"]:
                state["chapters"][ch_key] = {}

            ch_score = sum(r["score"] for r in results) / len(results) if results else 0
            state["chapters"][ch_key]["review_score"] = round(ch_score, 1)
            state["chapters"][ch_key]["reviewed_at"] = now
            state["chapters"][ch_key]["review_dimensions"] = {
                r["dimension"]: r["score"] for r in results
            }

        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

        return {"state_updated": True, "chapters_updated": list(chapter_results.keys())}
```

### _save_metrics / _writeback_state（Step 5/6）

```python
async def _save_metrics(self, context: dict) -> dict:
    """Step 5: 保存审查指标到 index.db。"""
    from .review_storage import ReviewStorage

    storage = ReviewStorage(context.get("project_root", "."))
    result = storage.save_metrics(
        context.get("all_chapter_results", {}),
        context.get("review_summary", {}),
    )

    return {
        "metrics_saved": True,
        "session_id": result.get("session_id"),
        "instruction": "审查指标已保存",
    }

async def _writeback_state(self, context: dict) -> dict:
    """Step 6: 写回审查记录到 state.json。"""
    from .review_storage import ReviewStorage

    storage = ReviewStorage(context.get("project_root", "."))
    result = storage.writeback_state(context.get("all_chapter_results", {}))

    return {
        "state_updated": True,
        "chapters_updated": result.get("chapters_updated", []),
        "instruction": "审查记录已写回 state.json",
    }
```

### 审查报告数据结构

```python
{
    "overall": {
        "avg_score": 7.5,
        "dimension_scores": {
            "爽点密度": 7.0,
            "设定一致性": 8.5,
            "节奏比例": 7.0,
            "人物OOC": 8.0,
            "叙事连贯性": 7.5,
            "追读力": 7.0,
        },
        "total_issues": 5,
        "verdict": "良好",
    },
    "chapters": {
        1: {"score": 7.8, "dimensions": {...}, "issues_count": 2},
        2: {"score": 7.2, "dimensions": {...}, "issues_count": 3},
    },
    "priority_fixes": [...],  # critical + high 问题
    "suggestions": ["增加情节转折...", ...],
}
```

## TDD 验收

- Happy path：Step 4 生成报告 → 用户确认 → Step 5 写入 index.db → Step 6 更新 state.json
- Edge case 1：avg_score >= 8.5 → verdict="优秀"
- Edge case 2：index.db 不存在 → 自动创建表和文件
- Error case：state.json 格式错误 → 覆盖写入新数据，不崩溃
