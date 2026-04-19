# Task 401: ReviewSkillHandler 骨架 + Step 1-2

## 目标

实现 ReviewSkillHandler，定义 8 步审查流程的步骤结构，实现 Step 1（加载参考）和 Step 2（加载项目状态）。

## 涉及文件

- `webnovel-writer/dashboard/skill_handlers/review_handler.py`（新建）

## 依赖

- Phase 0 已完成：SkillHandler 抽象类、SkillRegistry

## 前置知识

SkillHandler 接口（来自 Phase 0 task-002）：

```python
class SkillHandler(ABC):
    @abstractmethod
    def get_steps(self, mode: str | None = None) -> list[StepDefinition]:
        """返回该 Skill 的步骤定义列表。"""

    @abstractmethod
    async def execute_step(self, step: StepState, context: dict) -> dict:
        """执行一个 auto 步骤，返回 output_data。"""

    @abstractmethod
    async def validate_input(self, step: StepState, data: dict) -> str | None:
        """校验 form/confirm 步骤的用户输入。"""
```

Review 的 8 步流程（来自 spec.md）：
| Step | 名称 | 交互模式 |
|------|------|---------|
| 1 | 加载参考 | auto |
| 2 | 加载项目状态 | auto |
| 3 | 并行调用检查员 | auto |
| 4 | 生成审查报告 | confirm |
| 5 | 保存审查指标 | auto |
| 6 | 写回审查记录 | auto |
| 7 | 处理关键问题 | confirm |
| 8 | 收尾 | auto |

## 规格

### ReviewSkillHandler

```python
import json
from pathlib import Path
from ..skill_runner import SkillHandler
from ..skill_models import StepDefinition, StepState


class ReviewSkillHandler(SkillHandler):
    def get_steps(self, mode: str | None = None) -> list[StepDefinition]:
        return [
            StepDefinition(id="step_1", name="加载参考", interaction="auto"),
            StepDefinition(id="step_2", name="加载项目状态", interaction="auto"),
            StepDefinition(id="step_3", name="并行审查", interaction="auto"),
            StepDefinition(id="step_4", name="生成审查报告", interaction="confirm"),
            StepDefinition(id="step_5", name="保存审查指标", interaction="auto"),
            StepDefinition(id="step_6", name="写回审查记录", interaction="auto"),
            StepDefinition(id="step_7", name="处理关键问题", interaction="confirm"),
            StepDefinition(id="step_8", name="收尾", interaction="auto"),
        ]

    async def execute_step(self, step: StepState, context: dict) -> dict:
        if step.step_id == "step_1":
            return await self._load_references(context)
        if step.step_id == "step_2":
            return await self._load_project_state(context)
        # step_3 ~ step_8 在后续 task 中实现
        return {}

    async def validate_input(self, step: StepState, data: dict) -> str | None:
        if step.step_id == "step_4":
            # 用户确认审查报告
            if not data.get("confirmed", False):
                return "请确认审查报告"
            return None
        if step.step_id == "step_7":
            # 用户对 critical 问题做出决策
            decisions = data.get("decisions", [])
            if not decisions:
                return "请对关键问题做出决策"
            return None
        return None

    # ─── Step 1: 加载参考 ───

    async def _load_references(self, context: dict) -> dict:
        """加载审查参考资料：core-constraints、创意约束包、风格基准。"""
        project_root = Path(context.get("project_root", "."))

        # 1. core-constraints
        constraints_path = project_root / ".webnovel" / "core-constraints.md"
        constraints = ""
        if constraints_path.exists():
            constraints = constraints_path.read_text(encoding="utf-8")

        # 2. 创意约束包
        idea_bank_path = project_root / ".webnovel" / "idea_bank.json"
        creativity_constraints = []
        if idea_bank_path.exists():
            try:
                idea_bank = json.loads(idea_bank_path.read_text(encoding="utf-8"))
                pkg = idea_bank.get("creativity_package", {})
                creativity_constraints = pkg.get("constraints", [])
            except json.JSONDecodeError:
                pass

        # 3. 总纲（作为一致性参考）
        outline_path = project_root / "大纲" / "总纲.md"
        outline = ""
        if outline_path.exists():
            outline = outline_path.read_text(encoding="utf-8")

        # 4. 设定集
        setting_dir = project_root / "设定集"
        settings = {}
        if setting_dir.exists():
            for f in setting_dir.glob("*.md"):
                settings[f.stem] = f.read_text(encoding="utf-8")

        context["references"] = {
            "core_constraints": constraints,
            "creativity_constraints": creativity_constraints,
            "outline": outline,
            "settings": settings,
        }

        return {
            "loaded": True,
            "has_constraints": bool(constraints),
            "creativity_constraints_count": len(creativity_constraints),
            "settings_count": len(settings),
            "instruction": "参考资料加载完成",
        }

    # ─── Step 2: 加载项目状态 ───

    async def _load_project_state(self, context: dict) -> dict:
        """加载 state.json + 目标章节正文。"""
        project_root = Path(context.get("project_root", "."))
        chapter_start = int(context.get("chapter_start", 1))
        chapter_end = int(context.get("chapter_end", chapter_start))

        # 1. state.json
        state_path = project_root / ".webnovel" / "state.json"
        state = {}
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        context["project_state"] = state

        # 2. 加载目标章节正文
        chapters = {}
        chapter_dir = project_root / "正文"
        for ch_num in range(chapter_start, chapter_end + 1):
            ch_path = chapter_dir / f"第{ch_num}章.md"
            if ch_path.exists():
                chapters[ch_num] = ch_path.read_text(encoding="utf-8")

        context["review_chapters"] = chapters

        # 3. 加载章节大纲（用于一致性对比）
        chapter_outlines = {}
        outline_dir = project_root / "大纲"
        if outline_dir.exists():
            for vol_dir in outline_dir.iterdir():
                if vol_dir.is_dir():
                    for ch_num in range(chapter_start, chapter_end + 1):
                        ch_file = vol_dir / f"第{ch_num}章.json"
                        if ch_file.exists():
                            try:
                                chapter_outlines[ch_num] = json.loads(
                                    ch_file.read_text(encoding="utf-8")
                                )
                            except json.JSONDecodeError:
                                pass
        context["chapter_outlines"] = chapter_outlines

        return {
            "chapters_loaded": len(chapters),
            "chapters_missing": [
                ch for ch in range(chapter_start, chapter_end + 1)
                if ch not in chapters
            ],
            "has_outlines": len(chapter_outlines) > 0,
            "instruction": f"已加载 {len(chapters)} 章正文",
        }
```

### 启动参数

前端启动 review Skill 时传入的参数：

```python
# POST /api/skill/review/start 的 body
{
    "project_root": "/path/to/project",
    "chapter_start": 1,     # 审查起始章
    "chapter_end": 3,       # 审查结束章（支持范围审查）
}
```

### 注册

```python
from .skill_handlers.review_handler import ReviewSkillHandler
default_registry.register("review", ReviewSkillHandler)
```

## TDD 验收

- Happy path：`get_steps()` 返回 8 个 StepDefinition → Step 1 加载参考成功 → Step 2 加载章节正文
- Edge case 1：core-constraints.md 不存在 → has_constraints=False，不报错
- Edge case 2：审查范围内某章不存在 → chapters_missing 列出缺失章节，不阻断
- Error case：state.json 格式错误 → 返回空 state，不抛异常
