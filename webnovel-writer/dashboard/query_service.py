"""QueryService — 信息查询服务（非 Skill，即时查询）。"""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime


class QueryService:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.state_path = self.project_root / ".webnovel" / "state.json"
        self.db_path = self.project_root / ".webnovel" / "index.db"

    def _load_state(self) -> dict:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        return {}

    def _get_current_chapter(self) -> int:
        state = self._load_state()
        return state.get("last_written_chapter", 0)

    # ─── 伏笔查询 ───

    def query_foreshadowing(self) -> dict:
        """查询所有伏笔，计算紧急度，三层分类。

        Returns:
            {
                "foreshadowing": [...],
                "stats": {
                    "total": int,
                    "planted": int,
                    "revealed": int,
                    "overdue": int,
                    "recovery_rate": float,
                },
                "by_tier": {
                    "chapter": [...],
                    "volume": [...],
                    "book": [...],
                },
            }
        """
        state = self._load_state()
        foreshadowing_list = state.get("foreshadowing", [])
        current_chapter = self._get_current_chapter()

        results = []
        for f in foreshadowing_list:
            item = self._enrich_foreshadowing(f, current_chapter)
            results.append(item)

        # 按紧急度排序
        results.sort(key=lambda x: x["urgency"], reverse=True)

        # 三层分类
        by_tier = {"chapter": [], "volume": [], "book": []}
        for item in results:
            by_tier[item["tier"]].append(item)

        # 统计
        planted = sum(1 for r in results if r["status"] == "planted")
        revealed = sum(1 for r in results if r["status"] == "revealed")
        overdue = sum(1 for r in results if r["urgency"] >= 0.8 and r["status"] == "planted")

        return {
            "foreshadowing": results,
            "stats": {
                "total": len(results),
                "planted": planted,
                "revealed": revealed,
                "overdue": overdue,
                "recovery_rate": revealed / max(len(results), 1),
            },
            "by_tier": by_tier,
        }

    # ─── 节奏分析 ───

    def query_rhythm(self, volume_number: int | None = None) -> dict:
        """查询节奏分析数据。

        Args:
            volume_number: 可选，指定卷号（如 1）。不指定则返回所有卷。

        Returns:
            {
                "success": True,
                "rhythm_data": {
                    "volume_N": {
                        "total_chapters": int,
                        "beat_distribution": {"hook": int, "development": int, "climax": int, "resolution": int, "setup": int},
                        "avg_emotion_intensity": float,
                        "pacing_score": float,
                        "pacing_label": str,
                        "emotion_curve": [{"chapter": int, "intensity": float}, ...],
                        "climax_chapters": [int, ...],
                    },
                    ...
                }
            }
        """
        rhythm_path = self.project_root / ".webnovel" / "rhythm_data.json"
        if not rhythm_path.exists():
            return {"success": True, "rhythm_data": {}}

        try:
            raw = json.loads(rhythm_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"success": True, "rhythm_data": {}}

        result: dict[str, dict] = {}

        for vol_key, vol_data in raw.items():
            # 过滤指定卷号
            if volume_number is not None:
                # vol_key 形如 "volume_1" → 提取编号
                try:
                    num = int(vol_key.split("_")[-1])
                except ValueError:
                    continue
                if num != volume_number:
                    continue

            chapters = vol_data.get("chapters", [])
            beat_types = vol_data.get("beat_types", [])
            intensities = vol_data.get("emotion_intensity", [])
            pacing_score = vol_data.get("pacing_score", 0.0)

            # beat_distribution
            dist = {"hook": 0, "development": 0, "climax": 0, "resolution": 0, "setup": 0}
            for bt in beat_types:
                if bt in dist:
                    dist[bt] += 1

            # avg_emotion_intensity
            if intensities:
                avg_intensity = sum(intensities) / len(intensities)
            else:
                avg_intensity = 0.0

            # pacing_label
            if pacing_score >= 0.7:
                pacing_label = "快节奏"
            elif pacing_score >= 0.4:
                pacing_label = "中等节奏"
            else:
                pacing_label = "慢节奏"

            # emotion_curve
            emotion_curve = [
                {"chapter": ch, "intensity": intensity}
                for ch, intensity in zip(chapters, intensities)
            ]

            # climax_chapters: intensity >= 8
            climax_chapters = [
                ch for ch, intensity in zip(chapters, intensities) if intensity >= 8
            ]

            result[vol_key] = {
                "total_chapters": len(chapters),
                "beat_distribution": dist,
                "avg_emotion_intensity": round(avg_intensity, 2),
                "pacing_score": pacing_score,
                "pacing_label": pacing_label,
                "emotion_curve": emotion_curve,
                "climax_chapters": climax_chapters,
            }

        return {"success": True, "rhythm_data": result}

# ─── 金手指查询 ───

    def query_golden_finger(self, book_id: str | None = None) -> dict:
        """查询金手指状态。

        Returns:
            {
                "success": True,
                "golden_finger": {
                    "id": str,
                    "name": str,
                    "type": str,
                    "level": int,
                    "max_level": int,
                    "progress_percent": float,
                    "current_effects": [str, ...],
                    "cooldown_status": {
                        "active": bool,
                        "remaining_chapters": int | None,
                        "recent_chapter": int | None,
                    },
                    "activation_count": int,
                    "evolution_stages": [int, ...],
                } | None,
            }
        """
        gf_path = self.project_root / ".webnovel" / "golden_finger_tracker.json"
        if not gf_path.exists():
            return {"success": True, "golden_finger": None}

        try:
            raw = json.loads(gf_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"success": True, "golden_finger": None}

        current_level = raw.get("current_level", 1)
        max_level = raw.get("max_level", 1)
        recent = raw.get("recent_activations", [])
        activation_count = len(raw.get("activation_history", []))

        # cooldown_status
        if recent:
            last = recent[0]
            remaining = last.get("cooldown_remaining", 0)
            cooldown_status = {
                "active": remaining > 0,
                "remaining_chapters": remaining if remaining > 0 else 0,
                "recent_chapter": last.get("chapter"),
            }
        else:
            cooldown_status = {
                "active": False,
                "remaining_chapters": None,
                "recent_chapter": None,
            }

        # evolution_stages: [3, 6, 9] — max_level 内的节点
        evolution_stages = [i for i in range(1, max_level + 1) if i % 3 == 0 and i < max_level]

        return {
            "success": True,
            "golden_finger": {
                "id": raw.get("gf_id", ""),
                "name": raw.get("gf_name", ""),
                "type": raw.get("gf_type", "unknown"),
                "level": current_level,
                "max_level": max_level,
                "progress_percent": round(current_level / max_level * 100, 1),
                "current_effects": raw.get("current_effects", []),
                "cooldown_status": cooldown_status,
                "activation_count": activation_count,
                "evolution_stages": evolution_stages,
            },
        }

    # ─── 债务查询 ───

    def query_debt(self, book_id: str | None = None) -> dict:
        """查询伏笔/债务状态。

        Returns:
            {
                "success": True,
                "debt_summary": {
                    "total_unresolved": int,
                    "total_resolved": int,
                    "resolution_rate": float,
                    "critical_debts": [...],
                    "recently_resolved": [...],
                }
            }
        """
        debt_path = self.project_root / ".webnovel" / "debt_tracker.json"
        if not debt_path.exists():
            return {
                "success": True,
                "debt_summary": {
                    "total_unresolved": 0,
                    "total_resolved": 0,
                    "resolution_rate": 0.0,
                    "critical_debts": [],
                    "recently_resolved": [],
                },
            }

        try:
            raw = json.loads(debt_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {
                "success": True,
                "debt_summary": {
                    "total_unresolved": 0,
                    "total_resolved": 0,
                    "resolution_rate": 0.0,
                    "critical_debts": [],
                    "recently_resolved": [],
                },
            }

        unresolved = raw.get("unresolved_plot_debts", [])
        resolved = raw.get("resolved_plot_debts", [])
        current_chapter = self._get_current_chapter()

        total_unresolved = len(unresolved)
        total_resolved = len(resolved)
        total = total_unresolved + total_resolved
        resolution_rate = round(total_resolved / max(total, 1) * 100, 1)

        # critical_debts: weight >= 4 且 unresolved
        critical_debts = []
        for d in unresolved:
            weight = d.get("weight", 0)
            if weight >= 4:
                expected = d.get("expected_payoff_chapter", 0)
                overdue = max(0, current_chapter - expected)
                # urgency = weight * overdue_factor (overdue_factor = 1.0 if overdue else 1.0)
                overdue_factor = 1.0
                critical_debts.append({
                    "id": d.get("id", ""),
                    "plant_chapter": d.get("plant_chapter", 0),
                    "expected_payoff_chapter": expected,
                    "overdue_chapters": overdue,
                    "urgency": round(weight * overdue_factor, 2),
                })

        # Sort critical by urgency desc
        critical_debts.sort(key=lambda x: x["urgency"], reverse=True)

        # recently_resolved: top 5 by payoff_chapter desc
        recently_resolved = sorted(
            resolved, key=lambda x: x.get("payoff_chapter", 0), reverse=True
        )[:5]

        return {
            "success": True,
            "debt_summary": {
                "total_unresolved": total_unresolved,
                "total_resolved": total_resolved,
                "resolution_rate": resolution_rate,
                "critical_debts": critical_debts,
                "recently_resolved": recently_resolved,
            },
        }

    def _enrich_foreshadowing(self, f: dict, current_chapter: int) -> dict:
        """为伏笔计算紧急度和分类。"""
        plant_chapter = f.get("plant_chapter", 0)
        reveal_chapter = f.get("reveal_chapter", plant_chapter + 10)
        payoff_window = reveal_chapter - plant_chapter
        weight = f.get("weight", 1.0)
        status = f.get("status", "planted") if isinstance(f.get("status"), str) else "planted"

        # 紧急度计算
        if status == "revealed":
            urgency = 0.0
        elif current_chapter >= reveal_chapter:
            urgency = 1.0  # 已超期
        else:
            elapsed = max(0, current_chapter - plant_chapter)
            urgency = weight * elapsed / max(payoff_window, 1)

        # 三层分类
        if payoff_window <= 5:
            tier = "chapter"
        elif payoff_window <= 30:
            tier = "volume"
        else:
            tier = "book"

        # 紧急度等级
        if urgency >= 0.8:
            urgency_level = "critical"
        elif urgency >= 0.5:
            urgency_level = "warning"
        else:
            urgency_level = "normal"

        return {
            "id": f.get("id"),
            "title": f.get("title"),
            "plant_chapter": plant_chapter,
            "reveal_chapter": reveal_chapter,
            "weight": weight,
            "status": status,
            "urgency": round(urgency, 2),
            "urgency_level": urgency_level,
            "tier": tier,
            "payoff_window": payoff_window,
            "chapters_remaining": max(0, reveal_chapter - current_chapter),
        }
