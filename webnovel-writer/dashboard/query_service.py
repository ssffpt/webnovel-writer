"""QueryService — 信息查询服务（非 Skill，即时查询）。"""

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
