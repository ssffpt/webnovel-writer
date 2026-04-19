# Task 402: Step 3 并行审查（复用 Phase 3 检查器）

## 目标

实现 ReviewSkillHandler 的 Step 3（并行调用检查员），复用 Phase 3 task-305 的六维检查器，支持多章范围审查。

## 涉及文件

- `webnovel-writer/dashboard/skill_handlers/review_handler.py`（修改 execute_step）

## 依赖

- task-401（ReviewSkillHandler 骨架 + Step 1-2 完成）
- Phase 3 task-305（review_checkers.py 中的 6 个检查器已实现）

## 前置知识

Phase 3 task-305 中已实现的检查器（在 `review_checkers.py` 中）：

```python
from .review_checkers import (
    HookDensityChecker,
    SettingConsistencyChecker,
    RhythmRatioChecker,
    CharacterOOCChecker,
    NarrativeCoherenceChecker,
    ReadabilityChecker,
)
```

每个检查器接口：
```python
class BaseChecker(ABC):
    def __init__(self, text: str, task_brief: dict, contract: dict): ...
    async def check(self) -> dict:  # 返回 {dimension, score, passed, issues}
```

context 中已有的数据（来自 Step 1-2）：
- `context["references"]` — 参考资料（constraints/outline/settings）
- `context["review_chapters"]` — {章节号: 正文} dict
- `context["chapter_outlines"]` — {章节号: 大纲} dict

## 规格

### execute_step（Step 3）

```python
import asyncio

async def execute_step(self, step: StepState, context: dict) -> dict:
    if step.step_id == "step_3":
        return await self._run_parallel_review(step, context)
    # ... 其他步骤
```

### _run_parallel_review

```python
async def _run_parallel_review(self, step: StepState, context: dict) -> dict:
    """对每章执行六维并行审查。

    多章审查时，逐章执行（每章内部 6 维并行）。
    通过 step.progress 推送整体进度。
    """
    from .review_checkers import (
        HookDensityChecker,
        SettingConsistencyChecker,
        RhythmRatioChecker,
        CharacterOOCChecker,
        NarrativeCoherenceChecker,
        ReadabilityChecker,
    )

    chapters = context.get("review_chapters", {})
    references = context.get("references", {})
    chapter_outlines = context.get("chapter_outlines", {})

    # 构建 task_brief 和 contract（从 references 转换）
    task_brief = {
        "relevant_settings": "\n".join(references.get("settings", {}).values()),
        "chapter_outline": "",  # 每章单独设置
        "previous_summaries": [],
        "pending_foreshadowing": [],
        "character_states": {},
        "core_constraints": references.get("core_constraints", ""),
        "style_reference": "",
    }

    contract = {
        "setting_constraints": self._extract_constraints_from_references(references),
        "foreshadowing_obligations": [],
        "timeline_anchor": "",
        "character_boundaries": {},
    }

    all_chapter_results = {}
    chapter_nums = sorted(chapters.keys())
    total = len(chapter_nums)

    for i, ch_num in enumerate(chapter_nums):
        text = chapters[ch_num]

        # 更新本章大纲到 task_brief
        ch_outline = chapter_outlines.get(ch_num, {})
        task_brief["chapter_outline"] = json.dumps(ch_outline, ensure_ascii=False) if ch_outline else ""

        # 6 维并行
        checkers = [
            HookDensityChecker(text, task_brief, contract),
            SettingConsistencyChecker(text, task_brief, contract),
            RhythmRatioChecker(text, task_brief, contract),
            CharacterOOCChecker(text, task_brief, contract),
            NarrativeCoherenceChecker(text, task_brief, contract),
            ReadabilityChecker(text, task_brief, contract),
        ]

        results = await asyncio.gather(
            *[checker.check() for checker in checkers],
            return_exceptions=True,
        )

        chapter_results = []
        for j, result in enumerate(results):
            if isinstance(result, Exception):
                chapter_results.append({
                    "dimension": checkers[j].dimension,
                    "score": 0,
                    "passed": False,
                    "issues": [{"severity": "error", "message": str(result)}],
                })
            else:
                chapter_results.append(result)

        all_chapter_results[ch_num] = chapter_results

        # 更新进度
        step.progress = (i + 1) / total

    # 汇总
    context["all_chapter_results"] = all_chapter_results
    summary = self._summarize_review(all_chapter_results)
    context["review_summary"] = summary

    return {
        "all_chapter_results": all_chapter_results,
        "summary": summary,
        "instruction": f"审查完成：{total} 章，平均分 {summary['avg_score']:.1f}/10",
    }

def _summarize_review(self, all_results: dict) -> dict:
    """汇总多章审查结果。"""
    all_scores = []
    all_issues = []
    dimension_scores = {}

    for ch_num, results in all_results.items():
        for r in results:
            dim = r["dimension"]
            all_scores.append(r["score"])
            dimension_scores.setdefault(dim, []).append(r["score"])
            for issue in r.get("issues", []):
                issue["chapter"] = ch_num
                issue["dimension"] = dim
                all_issues.append(issue)

    # 按严重度排序
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "error": 0}
    all_issues.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 4))

    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
    dimension_avg = {
        dim: sum(scores) / len(scores)
        for dim, scores in dimension_scores.items()
    }

    return {
        "avg_score": round(avg_score, 1),
        "dimension_avg": {k: round(v, 1) for k, v in dimension_avg.items()},
        "total_issues": len(all_issues),
        "critical_issues": [i for i in all_issues if i.get("severity") == "critical"],
        "high_issues": [i for i in all_issues if i.get("severity") == "high"],
        "all_issues": all_issues,
    }

def _extract_constraints_from_references(self, references: dict) -> list[str]:
    """从参考资料中提取硬约束。"""
    constraints = []
    core = references.get("core_constraints", "")
    for line in core.split("\n"):
        line = line.strip()
        if line.startswith("- "):
            constraints.append(line[2:])

    for c in references.get("creativity_constraints", []):
        constraints.append(c.get("content", ""))

    return constraints
```

### 进度推送

多章审查时，SSE 事件示例：

```json
{
  "type": "skill.step",
  "skillId": "xxx",
  "step": {"id": "step_3", "name": "并行审查", "status": "running", "progress": 0.33},
  "log": "正在审查第 1/3 章..."
}
```

## TDD 验收

- Happy path：3 章审查 → 每章 6 维并行 → all_chapter_results 包含 3 个 key → 每个 key 有 6 个维度结果
- Edge case 1：单章审查 → all_chapter_results 只有 1 个 key → progress 直接到 1.0
- Edge case 2：某个检查器抛异常 → 该维度 score=0，其余正常
- Error case：review_chapters 为空 → 返回空结果，不报错
