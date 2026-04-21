"""PlanSkillHandler — 8-step (9 definition) volume-level planning skill."""
from __future__ import annotations

import json
from pathlib import Path

from dashboard.skill_models import StepDefinition, StepState
from dashboard.skill_runner import SkillHandler


# Schema for the Step 3 form — returned as output_data when entering step_3.
PLAN_STEP_3_SCHEMA = {
    "title": "选择卷",
    "fields": [
        {
            "name": "volume_name",
            "label": "卷名",
            "type": "text",
            "required": True,
            "hint": "如：第一卷·初入江湖",
        },
        {
            "name": "chapter_start",
            "label": "起始章",
            "type": "number",
            "required": True,
        },
        {
            "name": "chapter_end",
            "label": "结束章",
            "type": "number",
            "required": True,
        },
        {
            "name": "volume_theme",
            "label": "本卷主题",
            "type": "textarea",
            "hint": "本卷的核心主题或目标",
        },
        {
            "name": "special_requirements",
            "label": "特殊需求",
            "type": "textarea",
            "hint": "对本卷的特殊要求（可选）",
        },
    ],
}


class PlanSkillHandler(SkillHandler):
    """8-step (step_1–step_8, with step_4_5) volume-level planning skill.

    Step definitions:
    - step_1:    加载项目数据          (auto)
    - step_2:    构建设定基线          (auto)
    - step_3:    选择卷               (form)
    - step_4:    生成卷节拍表          (confirm)
    - step_4_5:  生成卷时间线表        (confirm)
    - step_5:    生成卷骨架            (confirm)
    - step_6:    生成章节大纲          (auto)
    - step_7:    回写设定集            (auto)
    - step_8:    验证与保存            (auto)
    """

    def get_steps(self, mode: str | None = None) -> list[StepDefinition]:
        return [
            StepDefinition(id="step_1",   name="加载项目数据",   interaction="auto"),
            StepDefinition(id="step_2",  name="构建设定基线",  interaction="auto"),
            StepDefinition(id="step_3",  name="选择卷",        interaction="form"),
            StepDefinition(id="step_4",   name="生成卷节拍表",  interaction="confirm"),
            StepDefinition(id="step_4_5", name="生成卷时间线表", interaction="confirm"),
            StepDefinition(id="step_5",   name="生成卷骨架",   interaction="confirm"),
            StepDefinition(id="step_6",   name="生成章节大纲",  interaction="auto"),
            StepDefinition(id="step_7",   name="回写设定集",    interaction="auto"),
            StepDefinition(id="step_8",   name="验证与保存",    interaction="auto"),
        ]

    async def execute_step(self, step: StepState, context: dict) -> dict:
        if step.step_id == "step_1":
            return await self._load_project_data(context)
        if step.step_id == "step_2":
            return await self._build_setting_baseline(context)
        if step.step_id == "step_4":
            return await self._generate_beat_sheet(context)
        if step.step_id == "step_4_5":
            return await self._generate_timeline(context)
        if step.step_id == "step_5":
            return await self._generate_volume_skeleton(context)
        if step.step_id == "step_6":
            return await self._generate_chapter_outlines(step, context)
        if step.step_id == "step_7":
            return await self._writeback_settings(step, context)
        if step.step_id == "step_8":
            return await self._validate_and_save(step, context)
        # step_3 is a form — handled by submit_input flow; execute_step not called.
        return {}

    async def validate_input(self, step: StepState, data: dict) -> str | None:
        if step.step_id == "step_3":
            return self._validate_volume_selection(data)
        if step.step_id == "step_4":
            return self._validate_confirm(data, "节拍表")
        if step.step_id == "step_4_5":
            return self._validate_confirm(data, "时间线")
        if step.step_id == "step_5":
            return self._validate_confirm(data, "卷骨架")
        if step.step_id == "step_7":
            return self._validate_blocker_decisions(data)
        return None

    # ------------------------------------------------------------------
    # Step 1: Load project data
    # ------------------------------------------------------------------

    async def _load_project_data(self, context: dict) -> dict:
        """Read state.json / 总纲 / 设定集 / idea_bank into context."""
        project_root = Path(context.get("project_root", "."))

        # 1. state.json
        state_path = project_root / ".webnovel" / "state.json"
        state_data: dict = {}
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
        settings: dict[str, str] = {}
        if setting_dir.exists():
            for f in setting_dir.glob("*.md"):
                settings[f.stem] = f.read_text(encoding="utf-8")
        context["settings"] = settings

        # 4. idea_bank
        idea_bank_path = project_root / ".webnovel" / "idea_bank.json"
        idea_bank: dict = {}
        if idea_bank_path.exists():
            idea_bank = json.loads(idea_bank_path.read_text(encoding="utf-8"))
        context["idea_bank"] = idea_bank

        # 5. Existing volumes (scan 大纲 directory)
        volumes: list[str] = []
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

    # ------------------------------------------------------------------
    # Step 2: Build setting baseline
    # ------------------------------------------------------------------

    async def _build_setting_baseline(self, context: dict) -> dict:
        """Create missing required setting templates (incremental, never overwrites)."""
        project_root = Path(context.get("project_root", "."))
        setting_dir = project_root / "设定集"
        setting_dir.mkdir(parents=True, exist_ok=True)

        required_settings = ["力量体系.md", "世界观.md", "主要角色.md"]
        created: list[str] = []

        for filename in required_settings:
            filepath = setting_dir / filename
            if not filepath.exists():
                template = f"# {filepath.stem}\n\n> 待补充\n"
                filepath.write_text(template, encoding="utf-8")
                created.append(filename)

        context["setting_baseline_ready"] = True
        context["missing_settings_created"] = created

        if created:
            instruction = f"已创建缺失设定模板：{', '.join(created)}"
        else:
            instruction = "设定基线构建完成"

        return {
            "baseline_ready": True,
            "missing_created": created,
            "instruction": instruction,
        }

    # ------------------------------------------------------------------
    # Step 3: Volume selection validation
    # ------------------------------------------------------------------

    def _validate_volume_selection(self, data: dict) -> str | None:
        """Validate the volume selection form fields."""
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

    # ------------------------------------------------------------------
    # Step 4: Generate beat sheet
    # ------------------------------------------------------------------

    async def _generate_beat_sheet(self, context: dict) -> dict:
        """Generate volume beat sheet (fallback mode without AI)."""
        chapter_start = int(context.get("chapter_start", 1))
        chapter_end = int(context.get("chapter_end", 12))
        total_chapters = chapter_end - chapter_start + 1
        volume_theme = context.get("volume_theme", "")

        beats = self._fallback_beat_sheet(total_chapters, chapter_start, volume_theme)
        context["beat_sheet"] = beats

        return {
            "beats": beats,
            "total_chapters": total_chapters,
            "instruction": "请确认以下节拍表，或提出修改意见",
        }

    def _fallback_beat_sheet(
        self, total_chapters: int, chapter_start: int, theme: str
    ) -> list[dict]:
        """Fallback template beat sheet (three-act structure)."""
        beats = []
        act1_end = total_chapters // 4
        act2_end = act1_end + total_chapters // 2

        for i in range(total_chapters):
            chapter_num = chapter_start + i
            if i < act1_end:
                act = "开端"
                emotion = "期待"
            elif i < act2_end:
                act = "发展"
                emotion = "紧张"
            else:
                act = "高潮"
                emotion = "爆发"

            beat = {
                "chapter": chapter_num,
                "act": act,
                "event": f"第{chapter_num}章事件（待 AI 生成）",
                "emotion_curve": emotion,
                "is_climax": i == total_chapters - 1 or i == act1_end - 1,
                "hook_type": "cliffhanger" if i % 3 == 2 else "curiosity",
            }
            beats.append(beat)

        return beats

    # ------------------------------------------------------------------
    # Step 4.5: Generate timeline
    # ------------------------------------------------------------------

    async def _generate_timeline(self, context: dict) -> dict:
        """Generate volume timeline (fallback mode without AI)."""
        beats = context.get("beat_sheet", [])
        chapter_start = int(context.get("chapter_start", 1))
        chapter_end = int(context.get("chapter_end", 12))

        if not beats:
            beats = [
                {
                    "chapter": i,
                    "act": "待定",
                    "event": f"第{i}章事件（待 AI 生成）",
                    "emotion_curve": "待定",
                }
                for i in range(chapter_start, chapter_end + 1)
            ]

        timeline = self._fallback_timeline(beats)
        context["timeline"] = timeline

        return {
            "timeline": timeline,
            "instruction": "请确认以下时间线，或提出修改意见",
        }

    def _fallback_timeline(self, beats: list[dict]) -> list[dict]:
        """Fallback template timeline based on beat sheet."""
        timeline = []
        for i, beat in enumerate(beats):
            event = {
                "day": i + 1,
                "chapter": beat["chapter"],
                "location": "待定",
                "characters": ["主角"],
                "event": beat["event"],
                "strand": "主线",
            }
            timeline.append(event)
        return timeline

    # ------------------------------------------------------------------
    # Step 5: Generate volume skeleton
    # ------------------------------------------------------------------

    async def _generate_volume_skeleton(self, context: dict) -> dict:
        """Generate volume skeleton (strand planning, highlight density, foreshadowing, constraint triggers).

        Fallback mode without AI: generates template skeleton based on beat_sheet and timeline.
        """
        beats = context.get("beat_sheet", [])
        timeline = context.get("timeline", [])
        idea_bank = context.get("idea_bank", {})
        chapter_start = int(context.get("chapter_start", 1))
        chapter_end = int(context.get("chapter_end", 12))
        total_chapters = chapter_end - chapter_start + 1

        skeleton = self._fallback_skeleton(beats, timeline, idea_bank, chapter_start, total_chapters)
        context["volume_skeleton"] = skeleton

        return {
            "skeleton": skeleton,
            "instruction": "请确认以下卷骨架，或提出修改意见",
        }

    def _fallback_skeleton(
        self,
        beats: list[dict],
        timeline: list[dict],
        idea_bank: dict,
        chapter_start: int,
        total_chapters: int,
    ) -> dict:
        """Fallback template volume skeleton (without AI)."""
        # 1. Strand planning
        strands = [
            {
                "name": "主线",
                "description": "核心剧情推进",
                "chapters": list(range(chapter_start, chapter_start + total_chapters)),
            },
            {
                "name": "感情线",
                "description": "感情关系发展",
                "chapters": list(range(chapter_start, chapter_start + total_chapters, 3)),
            },
        ]

        # 2. Hook points (highlight density: every 4 chapters a highlight)
        hook_points = []
        for i in range(0, total_chapters, 4):
            ch = chapter_start + i
            hook_points.append({
                "chapter": ch,
                "type": "大高潮" if (i // 4) % 3 == 2 else "小高潮",
                "description": f"第{ch}章爽点（待 AI 生成）",
            })

        # 3. Foreshadowing layout
        foreshadowing = []
        if beats:
            # Distribute foreshadowing across the volume
            num_foreshadows = min(len(beats), 3)
            for i in range(num_foreshadows):
                plant_idx = i * len(beats) // max(num_foreshadows, 1)
                reveal_idx = plant_idx + len(beats) // 2
                if reveal_idx >= len(beats):
                    reveal_idx = len(beats) - 1
                foreshadowing.append({
                    "id": f"foreshadow_{i + 1}",
                    "plant_chapter": beats[plant_idx]["chapter"],
                    "reveal_chapter": beats[reveal_idx]["chapter"],
                    "description": "伏笔（待 AI 生成）",
                    "urgency": "low",
                })
        else:
            foreshadowing.append({
                "id": "foreshadow_1",
                "plant_chapter": chapter_start,
                "reveal_chapter": chapter_start + total_chapters - 1,
                "description": "伏笔（待 AI 生成）",
                "urgency": "low",
            })

        # 4. Constraint triggers (from idea_bank constraints)
        constraints = idea_bank.get("creativity_package", {}).get("constraints", [])
        constraint_triggers = []
        for i, c in enumerate(constraints):
            trigger_ch = chapter_start + (i * total_chapters // max(len(constraints), 1))
            constraint_triggers.append({
                "constraint": c.get("content", ""),
                "trigger_chapter": trigger_ch,
                "how": f"在第{trigger_ch}章触发此约束（待 AI 生成）",
            })

        return {
            "strands": strands,
            "hook_points": hook_points,
            "foreshadowing": foreshadowing,
            "constraint_triggers": constraint_triggers,
        }

    # ------------------------------------------------------------------
    # Step 6: Generate chapter outlines
    # ------------------------------------------------------------------

    async def _generate_chapter_outlines(self, step: StepState, context: dict) -> dict:
        """分批生成章节大纲（fallback 模式，无 AI 时生成模板大纲）。

        每章大纲包含 16 个字段。
        分批生成（每批 4 章），通过 step.progress 推送进度。
        """
        chapter_start = int(context.get("chapter_start", 1))
        chapter_end = int(context.get("chapter_end", 12))
        beats = context.get("beat_sheet", [])
        skeleton = context.get("volume_skeleton", {})
        total_chapters = chapter_end - chapter_start + 1

        BATCH_SIZE = 4
        chapter_outlines = []

        for batch_start in range(0, total_chapters, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total_chapters)
            batch_chapters = list(range(
                chapter_start + batch_start,
                chapter_start + batch_end,
            ))

            # 更新进度（SkillRunner 检测到变化时通过 SSE 推送）
            step.progress = batch_start / total_chapters

            # 获取本批次对应的节拍
            batch_beats = [b for b in beats if b["chapter"] in batch_chapters]

            # 降级模式：生成模板大纲
            batch_outlines = self._fallback_chapter_outlines(batch_chapters, batch_beats, skeleton)
            chapter_outlines.extend(batch_outlines)

        step.progress = 1.0
        context["chapter_outlines"] = chapter_outlines

        return {
            "chapter_outlines": chapter_outlines,
            "total_generated": len(chapter_outlines),
            "instruction": f"已生成 {len(chapter_outlines)} 章大纲",
        }

    def _fallback_chapter_outlines(
        self,
        chapters: list[int],
        beats: list[dict],
        skeleton: dict,
    ) -> list[dict]:
        """无 AI 时的降级模板章节大纲。"""
        outlines = []
        hook_chapters = {hp["chapter"] for hp in skeleton.get("hook_points", [])}
        strand_chapters: dict[int, str] = {}
        for strand in skeleton.get("strands", []):
            for ch in strand.get("chapters", []):
                strand_chapters[ch] = strand.get("name", "主线")

        for i, ch_num in enumerate(chapters):
            beat = beats[i] if i < len(beats) else {}
            strand = strand_chapters.get(ch_num, "主线")
            is_climax = (
                ch_num in hook_chapters
                or beat.get("is_climax", False)
            )
            outline = {
                "chapter": ch_num,
                "title": f"第{ch_num}章",
                "pov": "主角",
                "location": "待定",
                "time": f"第{ch_num}天",
                "summary": beat.get("event", f"第{ch_num}章剧情（待 AI 生成）"),
                "opening_hook": "悬念开场（待生成）",
                "closing_hook": "章末钩子（待生成）",
                "key_events": [beat.get("event", "主要事件")] if beat else ["主要事件"],
                "character_goals": ["主角目标（待生成）"],
                "conflict": "本章冲突（待生成）",
                "emotion_arc": beat.get("emotion_curve", "平稳"),
                "strand": strand,
                "foreshadowing_plant": [],
                "foreshadowing_reveal": [],
                "is_climax": is_climax,
                "word_target": 2200,
            }
            outlines.append(outline)

        return outlines

    # ------------------------------------------------------------------
    # Step 7: Write back settings
    # ------------------------------------------------------------------

    async def _writeback_settings(self, step: StepState, context: dict) -> dict:
        """Write new facts from chapter_outlines back into the settings files.

        Detects conflicts and marks them as BLOCKER. Degraded mode (no AI) returns
        empty additions.
        """
        project_root = Path(context.get("project_root", "."))
        setting_dir = project_root / "设定集"
        chapter_outlines = context.get("chapter_outlines", [])
        existing_settings = context.get("settings", {})

        # Extract new facts (degraded: empty — AI extraction not yet wired)
        new_facts = self._extract_new_facts(chapter_outlines)

        blockers: list[dict] = []
        additions: list[dict] = []

        for fact in new_facts:
            target_file = fact.get("target_file", "")
            if fact.get("conflicts_with"):
                blockers.append({
                    "fact": fact.get("content", ""),
                    "target_file": target_file,
                    "conflict": fact.get("conflicts_with", ""),
                    "suggestion": fact.get("resolution", "请手动决策"),
                })
            else:
                additions.append(fact)

        # Write non-conflicting facts
        for fact in additions:
            target_path = setting_dir / f"{fact['target_file']}.md"
            if target_path.exists():
                current = target_path.read_text(encoding="utf-8")
                target_path.write_text(
                    current + f"\n\n### {fact['label']}\n\n{fact['content']}\n",
                    encoding="utf-8",
                )

        context["writeback_additions"] = additions
        context["writeback_blockers"] = blockers

        result = {
            "additions_count": len(additions),
            "blockers": blockers,
            "has_blockers": len(blockers) > 0,
            "instruction": "设定集回写完成" if not blockers else "检测到设定冲突，请决策",
        }

        if blockers:
            result["requires_input"] = True

        return result

    def _extract_new_facts(self, chapter_outlines: list[dict]) -> list[dict]:
        """Extract new setting facts from chapter outlines (degraded mode: empty list)."""
        # TODO: wire AI extraction
        return []

    def _validate_blocker_decisions(self, data: dict) -> str | None:
        """Validate that all blockers have a corresponding decision."""
        blockers = data.get("blocker_decisions", [])
        if not blockers:
            return "请对每个冲突做出决策"
        return None

    # ------------------------------------------------------------------
    # Step 8: Validate and save
    # ------------------------------------------------------------------

    async def _validate_and_save(self, step: StepState, context: dict) -> dict:
        """Run 7-item validation; if all pass, persist plan files to disk."""
        from dashboard.skill_handlers.plan_validator import PlanValidator

        validator = PlanValidator(context)
        results = validator.run_all_checks()

        all_passed = all(r["passed"] for r in results)

        if all_passed:
            await self._save_plan_files(context)

        context["validation_results"] = results
        context["plan_saved"] = all_passed

        return {
            "validation_results": results,
            "all_passed": all_passed,
            "instruction": "验证全部通过，文件已保存" if all_passed else "以下验证项未通过",
        }

    async def _save_plan_files(self, context: dict) -> None:
        """Write beat sheet, timeline, skeleton, and chapter outlines to disk."""
        project_root = Path(context.get("project_root", "."))
        volume_name = context.get("volume_name", "第一卷")
        chapter_outlines = context.get("chapter_outlines", [])
        beat_sheet = context.get("beat_sheet", [])
        timeline = context.get("timeline", [])
        skeleton = context.get("volume_skeleton", {})

        # Create volume directory
        volume_dir = project_root / "大纲" / volume_name
        volume_dir.mkdir(parents=True, exist_ok=True)

        # 1. Beat sheet
        beat_path = volume_dir / "节拍表.json"
        beat_path.write_text(
            json.dumps(beat_sheet, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # 2. Timeline
        timeline_path = volume_dir / "时间线.json"
        timeline_path.write_text(
            json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # 3. Volume skeleton
        skeleton_path = volume_dir / "卷骨架.json"
        skeleton_path.write_text(
            json.dumps(skeleton, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # 4. Chapter outlines
        for outline in chapter_outlines:
            ch_num = outline["chapter"]
            ch_path = volume_dir / f"第{ch_num}章.json"
            ch_path.write_text(
                json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8"
            )

        # 5. Update state.json
        state_path = project_root / ".webnovel" / "state.json"
        state: dict = {}
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding="utf-8"))
        state.setdefault("volumes", {})
        state["volumes"][volume_name] = {
            "status": "planned",
            "chapter_start": context.get("chapter_start"),
            "chapter_end": context.get("chapter_end"),
            "chapters_count": len(chapter_outlines),
        }
        state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ------------------------------------------------------------------
    # Shared confirm validation
    # ------------------------------------------------------------------

    def _validate_confirm(self, data: dict, label: str) -> str | None:
        """Shared validation for confirm-mode steps."""
        confirmed = data.get("confirmed", False)
        if not confirmed:
            feedback = data.get("feedback", "")
            if not feedback:
                return f"请确认{label}或提出修改意见"
        return None
