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
        """将审查指标写入 index.db。"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

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

        for ch_num, results in chapter_results.items():
            for r in results:
                cursor.execute(
                    "INSERT INTO review_metrics (chapter, dimension, score, issues_count, reviewed_at) VALUES (?, ?, ?, ?, ?)",
                    (int(ch_num), r["dimension"], r["score"], len(r.get("issues", [])), now),
                )

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
