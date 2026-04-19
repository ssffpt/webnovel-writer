# Task 201: PlanSkillHandler 骨架 + Step 1-3

## 目标

实现 PlanSkillHandler，定义 8 步（含 4.5）卷级规划流程的步骤结构，实现 Step 1-3 的逻辑。

## 涉及文件

- `webnovel-writer/dashboard/skill_handlers/plan_handler.py`（新建）

## 依赖

- Phase 0 已完成：SkillHandler 抽象类在 `skill_runner.py`，SkillRegistry 在 `skill_registry.py`

## 前置知识

SkillHandler 接口（来自 Phase 0 task-002）：

```python
from abc import ABC, abstractmethod
from ..skill_models import StepDefinition, StepState

class SkillHandler(ABC):
    @abstractmethod
    def get_steps(self, mode: str | None = None) -> list[StepDefinition]:
        """返回该 Skill 的步骤定义列表。"""

    @abstractmethod
    async def execute_step(self, step: StepState, context: dict) -> dict:
        """执行一个 auto 步骤，返回 output_data。"""

    @abstractmethod
    async def validate_input(self, step: StepState, data: dict) -> str | None:
        """校验 form/confirm 步骤的用户输入，返回 None 表示通过，否则返回错误信息。"""
```

StepDefinition（来自 Phase 0 task-001）：

```python
@dataclass
class StepDefinition:
    id: str                    # "step_1", "step_2" 等
    name: str                  # "加载项目数据"
    interaction: str           # "auto" | "form" | "confirm"
    skippable: bool = False
```

## 规格

### PlanSkillHandler

```python
import json
from pathlib import Path
from ..skill_runner import SkillHandler
from ..skill_models import StepDefinition, StepState


class PlanSkillHandler(SkillHandler):
    def get_steps(self, mode: str | None = None) -> list[StepDefinition]:
        return [
            StepDefinition(id="step_1", name="加载项目数据", interaction="auto"),
            StepDefinition(id="step_2", name="构建设定基线", interaction="auto"),
            StepDefinition(id="step_3", name="选择卷", interaction="form"),
            StepDefinition(id="step_4", name="生成卷节拍表", interaction="confirm"),
            StepDefinition(id="step_4_5", name="生成卷时间线表", interaction="confirm"),
            StepDefinition(id="step_5", name="生成卷骨架", interaction="confirm"),
            StepDefinition(id="step_6", name="生成章节大纲", interaction="auto"),
            StepDefinition(id="step_7", name="回写设定集", interaction="auto"),
            StepDefinition(id="step_8", name="验证与保存", interaction="auto"),
        ]

    async def execute_step(self, step: StepState, context: dict) -> dict:
        if step.step_id == "step_1":
            return await self._load_project_data(context)
        if step.step_id == "step_2":
            return await self._build_setting_baseline(context)
        # step_3 是 form，不走 execute_step
        # step_4 ~ step_8 在后续 task 中实现
        return {}

    async def validate_input(self, step: StepState, data: dict) -> str | None:
        if step.step_id == "step_3":
            return self._validate_volume_selection(data)
        # step_4/4.5/5 的 confirm 校验在 task-202/203 中实现
        return None

    # ─── Step 1: 加载项目数据 ───

    async def _load_project_data(self, context: dict) -> dict:
        """读取 state.json / 总纲 / 设定集 / idea_bank，存入 context。"""
        project_root = Path(context.get("project_root", "."))

        # 1. state.json
        state_path = project_root / ".webnovel" / "state.json"
        state_data = {}
        if state_path.exists():
            state_data = json.loads(state_path.read_text(encoding="utf-8"))
        context["state"] = state_data

        # 2. 总纲
        outline_path = project_root / "大纲" / "总纲.md"
        outline_content = ""
        if outline_path.exists():
            outline_content = outline_path.read_text(encoding="utf-8")
        context["outline"] = outline_content

        # 3. 设定集
        setting_dir = project_root / "设定集"
        settings = {}
        if setting_dir.exists():
            for f in setting_dir.glob("*.md"):
                settings[f.stem] = f.read_text(encoding="utf-8")
        context["settings"] = settings

        # 4. idea_bank
        idea_bank_path = project_root / ".webnovel" / "idea_bank.json"
        idea_bank = {}
        if idea_bank_path.exists():
            idea_bank = json.loads(idea_bank_path.read_text(encoding="utf-8"))
        context["idea_bank"] = idea_bank

        # 5. 已有卷列表（从大纲目录扫描）
        volumes = []
        outline_dir = project_root / "大纲"
        if outline_dir.exists():
            for d in sorted(outline_dir.iterdir()):
                if d.is_dir() and d.name.startswith("第"):
                    volumes.append(d.name)
        context["existing_volumes"] = volumes

        return {
            "loaded": True,
            "volumes_count": len(volumes),
            "has_outline": bool(outline_content),
            "settings_count": len(settings),
            "instruction": f"项目数据加载完成，已有 {len(volumes)} 卷",
        }

    # ─── Step 2: 构建设定基线 ───

    async def _build_setting_baseline(self, context: dict) -> dict:
        """增量补齐设定集，不清空重写。检查必要设定文件是否存在。"""
        project_root = Path(context.get("project_root", "."))
        setting_dir = project_root / "设定集"
        setting_dir.mkdir(parents=True, exist_ok=True)

        # 必要设定文件列表
        required_settings = ["力量体系.md", "世界观.md", "主要角色.md"]
        missing = []
        created = []

        for filename in required_settings:
            filepath = setting_dir / filename
            if not filepath.exists():
                missing.append(filename)
                # 创建空模板
                template = f"# {filepath.stem}\n\n> 待补充\n"
                filepath.write_text(template, encoding="utf-8")
                created.append(filename)

        context["setting_baseline_ready"] = True
        context["missing_settings_created"] = created

        return {
            "baseline_ready": True,
            "missing_created": created,
            "instruction": "设定基线构建完成" if not created else f"已创建缺失设定模板：{', '.join(created)}",
        }

    # ─── Step 3: 选择卷（form 校验） ───

    def _validate_volume_selection(self, data: dict) -> str | None:
        """校验卷选择表单。"""
        volume_name = data.get("volume_name", "").strip()
        if not volume_name:
            return "卷名不能为空"

        chapter_start = data.get("chapter_start")
        chapter_end = data.get("chapter_end")
        if chapter_start is None or chapter_end is None:
            return "请指定章节范围（起始章和结束章）"

        try:
            start = int(chapter_start)
            end = int(chapter_end)
        except (ValueError, TypeError):
            return "章节范围必须是数字"

        if start >= end:
            return "起始章必须小于结束章"
        if end - start > 50:
            return "单卷章节数不宜超过 50 章"

        return None
```

### Step 3 表单 Schema（供前端渲染）

execute_step 对 step_3 不执行（form 步骤），但 SkillRunner 进入 step_3 时会将 schema 作为 output_data 返回给前端：

```python
PLAN_STEP_3_SCHEMA = {
    "title": "选择卷",
    "fields": [
        {"name": "volume_name", "label": "卷名", "type": "text", "required": True,
         "hint": "如：第一卷·初入江湖"},
        {"name": "chapter_start", "label": "起始章", "type": "number", "required": True},
        {"name": "chapter_end", "label": "结束章", "type": "number", "required": True},
        {"name": "volume_theme", "label": "本卷主题", "type": "textarea",
         "hint": "本卷的核心主题或目标"},
        {"name": "special_requirements", "label": "特殊需求", "type": "textarea",
         "hint": "对本卷的特殊要求（可选）"},
    ],
}
```

### 注册

在 `skill_registry.py` 的 `default_registry` 中注册：

```python
from .skill_handlers.plan_handler import PlanSkillHandler
default_registry.register("plan", PlanSkillHandler)
```

## TDD 验收

- Happy path：`default_registry.get_handler("plan")` → 返回 PlanSkillHandler → `get_steps()` 返回 9 个 StepDefinition
- Edge case 1：Step 1 加载不存在的项目目录 → 返回空数据但不报错（loaded=True, volumes_count=0）
- Edge case 2：Step 3 validate_input 缺少 volume_name → 返回 "卷名不能为空"
- Error case：Step 3 chapter_start >= chapter_end → 返回 "起始章必须小于结束章"
