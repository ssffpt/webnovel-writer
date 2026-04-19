# Task 104: Init Step 6 一致性复述 + 充分性闸门 + 执行

## 目标

实现 Step 6：生成项目摘要供用户确认，通过充分性闸门后调用 init_project.py 创建项目。

## 涉及文件

- `webnovel-writer/dashboard/skill_handlers/init_handler.py`（修改 execute_step）
- `webnovel-writer/dashboard/script_adapter.py`（新建，封装 init_project.py 调用）

## 依赖

- task-103（Step 5 完成后 context 包含 selected_package）

## 规格

### execute_step（Step 6）

```python
async def execute_step(self, step: StepState, context: dict) -> dict:
    if step.step_id == "step_6":
        # 1. 充分性闸门检查
        gate_result = self._check_sufficiency_gate(context)
        if not gate_result["passed"]:
            return {
                "gate_passed": False,
                "missing_items": gate_result["missing"],
                "instruction": "以下必填项尚未完成，请返回补填",
            }

        # 2. 生成一致性摘要
        summary = self._build_summary(context)

        return {
            "gate_passed": True,
            "summary": summary,
            "instruction": "请确认以下项目摘要，确认后将创建项目",
        }
```

### 充分性闸门

```python
def _check_sufficiency_gate(self, context: dict) -> dict:
    """6 项必须全部通过。"""
    missing = []
    # 1. 书名 + 题材
    if not context.get("title"):
        missing.append("书名")
    if not context.get("genres"):
        missing.append("题材")
    # 2. 目标规模
    if not context.get("target_words"):
        missing.append("目标字数")
    # 3. 主角欲望 + 缺陷
    if not context.get("protagonist_desire"):
        missing.append("主角欲望")
    if not context.get("protagonist_flaw"):
        missing.append("主角缺陷")
    # 4. 世界观 + 力量体系
    if not context.get("world_scale"):
        missing.append("世界规模")
    if not context.get("power_system"):
        missing.append("力量体系")
    # 5. 创意约束包
    if not context.get("selected_package_id"):
        missing.append("创意约束包")
    # 6. 用户确认（在 validate_input 中处理）

    return {"passed": len(missing) == 0, "missing": missing}
```

### validate_input（Step 6 — 用户确认后执行创建）

```python
async def validate_input(self, step: StepState, data: dict) -> str | None:
    if step.step_id == "step_6":
        confirmed = data.get("confirmed", False)
        if not confirmed:
            return "请确认项目摘要"

        # 确认后执行项目创建
        context = step.input_data  # SkillRunner 会传入完整 context
        result = await self._execute_project_creation(context)
        if not result.get("success"):
            return f"项目创建失败：{result.get('error', '未知错误')}"

        return None
```

### _execute_project_creation

```python
async def _execute_project_creation(self, context: dict) -> dict:
    """通过 ScriptAdapter 调用 init_project.py + 后处理。"""
    from ..script_adapter import ScriptAdapter
    adapter = ScriptAdapter(project_root=context.get("project_root", ""))

    # 1. 调用 init_project.py
    result = await adapter.init_project(
        title=context["title"],
        genre=context["genres"][0] if context.get("genres") else "",
        protagonist_name=context.get("protagonist_name", ""),
        target_words=context.get("target_words", 2000000),
        target_chapters=context.get("target_chapters", 600),
        golden_finger_name=context.get("golden_finger_name", ""),
        golden_finger_type=context.get("golden_finger_type", ""),
        core_selling_points=context.get("one_line_story", ""),
    )

    if not result.get("success"):
        return result

    # 2. 后处理：Patch 总纲
    await adapter.patch_outline(
        project_root=result["project_root"],
        one_line_story=context.get("one_line_story", ""),
        core_conflict=context.get("core_conflict", ""),
        creativity_package=context.get("selected_package", {}),
        villain_tiers=context.get("villain_tiers", ""),
    )

    # 3. 写入 idea_bank.json
    await adapter.write_idea_bank(
        project_root=result["project_root"],
        package=context.get("selected_package", {}),
    )

    return result
```

### script_adapter.py 骨架

```python
"""ScriptAdapter — scripts/ 的 Python API 封装层。"""

import asyncio
import subprocess
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"


class ScriptAdapter:
    def __init__(self, project_root: str = ""):
        self.project_root = Path(project_root) if project_root else Path(".")

    async def init_project(self, **kwargs) -> dict:
        """封装 init_project.py 调用。"""
        script = _SCRIPTS_DIR / "init_project.py"
        cmd = [sys.executable, str(script), str(self.project_root), kwargs["title"], kwargs.get("genre", "")]
        # 添加可选参数
        if kwargs.get("protagonist_name"):
            cmd += ["--protagonist-name", kwargs["protagonist_name"]]
        if kwargs.get("target_words"):
            cmd += ["--target-words", str(kwargs["target_words"])]
        if kwargs.get("target_chapters"):
            cmd += ["--target-chapters", str(kwargs["target_chapters"])]
        if kwargs.get("golden_finger_name"):
            cmd += ["--golden-finger-name", kwargs["golden_finger_name"]]
        if kwargs.get("golden_finger_type"):
            cmd += ["--golden-finger-type", kwargs["golden_finger_type"]]

        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, text=True, encoding="utf-8"
        )
        if result.returncode != 0:
            return {"success": False, "error": result.stderr or result.stdout}
        return {"success": True, "project_root": str(self.project_root)}

    async def patch_outline(self, project_root: str, **kwargs) -> None:
        """后处理：补齐总纲内容。"""
        # 读取总纲 → 追加内容 → 写回
        outline_path = Path(project_root) / "大纲" / "总纲.md"
        if not outline_path.exists():
            return
        content = outline_path.read_text(encoding="utf-8")
        # 追加缺失的部分
        patches = []
        if kwargs.get("one_line_story") and "故事一句话" not in content:
            patches.append(f"\n## 故事一句话\n\n{kwargs['one_line_story']}\n")
        if kwargs.get("core_conflict") and "核心冲突" not in content:
            patches.append(f"\n## 核心冲突\n\n{kwargs['core_conflict']}\n")
        if kwargs.get("villain_tiers") and "反派分层" not in content:
            patches.append(f"\n## 反派分层\n\n{kwargs['villain_tiers']}\n")
        if patches:
            outline_path.write_text(content + "".join(patches), encoding="utf-8")

    async def write_idea_bank(self, project_root: str, package: dict) -> None:
        """写入 .webnovel/idea_bank.json。"""
        import json
        idea_bank_path = Path(project_root) / ".webnovel" / "idea_bank.json"
        idea_bank_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"creativity_package": package, "created_at": ""}
        idea_bank_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
```

## TDD 验收

- Happy path：context 完整 → 闸门通过 → 摘要生成 → 用户确认 → init_project.py 调用成功 → 总纲 Patch → idea_bank 写入
- Edge case 1：context 缺少 protagonist_desire → 闸门不通过 → 返回 missing_items 包含"主角欲望"
- Edge case 2：init_project.py 返回非零退出码 → validate_input 返回错误信息
- Error case：用户未确认（confirmed=False）→ validate_input 返回"请确认项目摘要"
