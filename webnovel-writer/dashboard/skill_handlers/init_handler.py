"""InitSkillHandler — 6-step project initialization skill."""
from __future__ import annotations

from datetime import datetime

from dashboard.skill_handlers.init_schemas import INIT_STEP_SCHEMAS
from dashboard.skill_models import StepDefinition, StepState
from dashboard.skill_runner import SkillHandler


class InitSkillHandler(SkillHandler):
    """6-step project initialization skill.

    Step definitions:
    - step_1: 故事核与商业定位  (form)
    - step_2: 角色骨架与关系冲突  (form)
    - step_3: 金手指与兑现机制  (form)
    - step_4: 世界观与力量规则  (form)
    - step_5: 创意约束包  (confirm)
    - step_6: 一致性复述与确认  (confirm)
    """

    def __init__(self) -> None:
        super().__init__()
        self._creation_input: dict | None = None  # 用户在 step_6 提交的数据
        self._creation_result: dict | None = None  # _execute_project_creation 的结果

    def get_steps(self, mode: str | None = None) -> list[StepDefinition]:
        return [
            StepDefinition(id="step_1", name="故事核与商业定位", interaction="form", schema=INIT_STEP_SCHEMAS["step_1"]),
            StepDefinition(id="step_2", name="角色骨架与关系冲突", interaction="form", schema=INIT_STEP_SCHEMAS["step_2"]),
            StepDefinition(id="step_3", name="金手指与兑现机制", interaction="form", schema=INIT_STEP_SCHEMAS["step_3"]),
            StepDefinition(id="step_4", name="世界观与力量规则", interaction="form", schema=INIT_STEP_SCHEMAS["step_4"]),
            StepDefinition(id="step_5", name="创意约束包", interaction="confirm"),
            StepDefinition(id="step_6", name="一致性复述与确认", interaction="confirm"),
        ]

    async def execute_step(self, step: StepState, context: dict) -> dict:
        """Execute an auto step; return its output_data dict.

        Step 1-4 (form): merge submitted form data into context.
        step_5: generate 2-3 creativity packages based on context from steps 1-4.
        step_6: confirm summary (placeholder, implemented in task-104).
        """
        if step.step_id in ("step_1", "step_2", "step_3", "step_4"):
            context.update(step.input_data or {})
            return {"merged_fields": list((step.input_data or {}).keys())}
        if step.step_id == "step_5":
            # Extract key information from previous 4 steps
            packages = await self._generate_creativity_packages(
                title=context.get("title", ""),
                genres=context.get("genres", []),
                one_line_story=context.get("one_line_story", ""),
                core_conflict=context.get("core_conflict", ""),
                protagonist_desire=context.get("protagonist_desire", ""),
                protagonist_flaw=context.get("protagonist_flaw", ""),
                golden_finger_type=context.get("golden_finger_type", ""),
            )
            return {
                "packages": packages,
                "instruction": "请选择一套创意约束包，或提出修改意见",
            }
        if step.step_id == "step_6":
            # 预执行（无 input_data）：只返回摘要和门禁检查，不创建项目
            if not step.input_data:
                gate_result = self._check_sufficiency_gate(context)
                return {
                    "gate_passed": gate_result["passed"],
                    "missing": gate_result.get("missing", []),
                    "summary": self._build_summary(context),
                    "instruction": "请确认以上信息，确认后将创建项目",
                }

            # 真正执行（有 input_data，用户已确认）：创建项目
            self._creation_input = step.input_data
            self._creation_result = await self._execute_project_creation(
                {**context, **step.input_data}
            )

            if not self._creation_result.get("success"):
                raise RuntimeError(
                    self._creation_result.get("error", "项目创建失败")
                )

            return {
                "gate_passed": True,
                "summary": self._build_summary({**context, **step.input_data}),
                "project_root": self._creation_result.get("project_root"),
                "message": "项目创建成功",
            }

        # Unknown step_id: return empty dict rather than raising.
        return {}

    async def validate_input(self, step: StepState, data: dict) -> str | None:
        """Validate form input against step schema.

        Returns an error message if a required field is missing, or None if valid.
        """
        # Step 5: require selected_package_id
        if step.step_id == "step_5":
            if not data.get("selected_package_id"):
                return "请选择一套创意约束包"
            return None

        # Step 6: require user confirmation
        if step.step_id == "step_6":
            confirmed = data.get("confirmed", False)
            if not confirmed:
                return "请确认项目摘要"
            return None

        schema = INIT_STEP_SCHEMAS.get(step.step_id)
        if not schema:
            return None
        for field in schema["fields"]:
            if field.get("required") and not data.get(field["name"]):
                return f"{field['label']}不能为空"
        return None

    # -------------------------------------------------------------------------
    # Step 5: Creativity package generation
    # -------------------------------------------------------------------------

    async def _generate_creativity_packages(self, **kwargs) -> list[dict]:
        """Generate 2-3 creativity constraint packages.

        In a full implementation this would call an AI API.
        Falls back to a template package when no AI API is available.
        """
        # TODO: Integrate AI API call for dynamic package generation
        # For now, return fallback package to unblock the workflow
        return [self._fallback_package()]

    def _fallback_package(self) -> dict:
        """Fallback template package when AI API is unavailable."""
        return {
            "id": "pkg_fallback",
            "name": "通用约束包",
            "description": "基础创作约束，适用于大多数题材",
            "constraints": [
                {"type": "anti_trope", "content": "避免开局即无敌"},
                {"type": "must_have", "content": "每卷必须有明确的阶段性目标"},
                {"type": "rhythm", "content": "每 5 章至少一个小高潮"},
            ],
            "score": {
                "novelty": 5,
                "feasibility": 9,
                "reader_hook": 6,
                "consistency": 8,
                "differentiation": 4,
            },
        }

    # -------------------------------------------------------------------------
    # Step 6: Sufficiency gate & summary
    # -------------------------------------------------------------------------

    def _check_sufficiency_gate(self, context: dict) -> dict:
        """6 项必须全部通过。"""
        missing = []
        if not context.get("title"):
            missing.append("书名")
        if not context.get("genres"):
            missing.append("题材")
        if not context.get("target_words"):
            missing.append("目标字数")
        if not context.get("protagonist_desire"):
            missing.append("主角欲望")
        if not context.get("protagonist_flaw"):
            missing.append("主角缺陷")
        if not context.get("world_scale"):
            missing.append("世界规模")
        if not context.get("power_system"):
            missing.append("力量体系")
        if not context.get("selected_package_id"):
            missing.append("创意约束包")
        return {"passed": len(missing) == 0, "missing": missing}

    def _build_summary(self, context: dict) -> str:
        """生成项目摘要文本。"""
        return f"""书名：{context.get('title', '')}
题材：{', '.join(context.get('genres', []))}
目标规模：{context.get('target_words', 0)} 字 / {context.get('target_chapters', 0)} 章
一句话故事：{context.get('one_line_story', '')}
核心冲突：{context.get('core_conflict', '')}

主角：{context.get('protagonist_name', '')}
欲望：{context.get('protagonist_desire', '')}
缺陷：{context.get('protagonist_flaw', '')}

金手指：{context.get('golden_finger_name', '')}（{context.get('golden_finger_type', '')}）

世界观：{context.get('world_scale', '')}
力量体系：{context.get('power_system', '')}

创意约束包：{context.get('selected_package_id', '')}
"""

    # -------------------------------------------------------------------------
    # Project creation
    # -------------------------------------------------------------------------

    async def _execute_project_creation(self, context: dict) -> dict:
        """通过 ScriptAdapter 调用 init_project.py + 后处理 patch_outline + write_idea_bank。"""
        from dashboard.script_adapter import ScriptAdapter

        adapter = ScriptAdapter(project_root=context.get("project_root", ""))

        # 1. 调用 init_project.py
        result = await adapter.init_project(
            title=context.get("title", ""),
            genre=context.get("genres", [""])[0] if context.get("genres") else "",
            protagonist_name=context.get("protagonist_name", ""),
            target_words=context.get("target_words", 2000000),
            target_chapters=context.get("target_chapters", 600),
            golden_finger_name=context.get("golden_finger_name", ""),
            golden_finger_type=context.get("golden_finger_type", ""),
            golden_finger_style=context.get("golden_finger_style", ""),
            core_selling_points=context.get("one_line_story", ""),
            protagonist_structure=context.get("protagonist_structure", ""),
            heroine_config=context.get("romance_config", ""),
            heroine_names="",
            heroine_role="",
            co_protagonists="",
            co_protagonist_roles="",
            antagonist_tiers=context.get("villain_tiers", ""),
            world_scale=context.get("world_scale", ""),
            factions=context.get("faction_layout", ""),
            power_system_type=context.get("power_system", ""),
            social_class=context.get("social_hierarchy", ""),
            resource_distribution="",
            gf_visibility=context.get("golden_finger_visibility", ""),
            gf_irreversible_cost=context.get("golden_finger_cost", ""),
            protagonist_desire=context.get("protagonist_desire", ""),
            protagonist_flaw=context.get("protagonist_flaw", ""),
            protagonist_archetype="",
            antagonist_level="",
            target_reader=context.get("target_audience", ""),
            platform="",
            currency_system="",
            currency_exchange="",
            sect_hierarchy="",
            cultivation_chain="",
            cultivation_subtiers="",
        )

        if not result.get("success"):
            return result

        project_root = result.get("project_root", context.get("project_root", ""))

        # 2. 后处理：Patch 总纲
        await adapter.patch_outline(
            project_root=project_root,
            one_line_story=context.get("one_line_story", ""),
            core_conflict=context.get("core_conflict", ""),
            villain_tiers=context.get("villain_tiers", ""),
        )

        # 3. 写入 idea_bank.json
        selected_package = context.get("selected_package", {})
        if not selected_package:
            # 从 context 中构建 fallback 包（与 _fallback_package 一致）
            selected_package = {
                "id": context.get("selected_package_id", "pkg_unknown"),
                "name": "创意约束包",
                "description": "用户选择的创意约束包",
                "constraints": [],
                "score": {"novelty": 5, "feasibility": 9, "reader_hook": 6, "consistency": 8, "differentiation": 4},
            }
        await adapter.write_idea_bank(project_root=project_root, package=selected_package)

        return {"success": True, "project_root": project_root}
