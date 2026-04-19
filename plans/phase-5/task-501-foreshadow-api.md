# Task 501: 伏笔查询 API（紧急度计算）

## 目标

实现伏笔查询后端 API，支持三层分类和紧急度计算。

## 涉及文件

- `webnovel-writer/dashboard/query_service.py`（新建）

## 依赖

- Phase 0 已完成（FastAPI app 可用）

## 前置知识

伏笔数据来源：
- `state.json` 中的 `foreshadowing` 列表（由 Plan Step 5 卷骨架写入）
- `index.db` 中可能有的 foreshadowing 表（由 Data Agent 写入）

紧急度公式（来自 spec.md）：
```
urgency = weight × (current_chapter - plant_chapter) / expected_payoff_window
```

三层分类：
- 章级伏笔（payoff_window <= 5 章）
- 卷级伏笔（payoff_window <= 30 章）
- 全书伏笔（payoff_window > 30 章）

紧急度颜色：
- Critical（红）：urgency >= 0.8
- Warning（黄）：urgency >= 0.5
- Normal（绿）：urgency < 0.5

## 规格

### query_service.py

```python
"""QueryService — 信息查询服务（非 Skill，即时查询）。"""

import json
import sqlite3
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
        status = f.get("status", "planted")

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
            **f,
            "urgency": round(urgency, 2),
            "urgency_level": urgency_level,
            "tier": tier,
            "payoff_window": payoff_window,
            "chapters_remaining": max(0, reveal_chapter - current_chapter),
        }
```

### API 端点

在 `app.py` 中注册：

```python
from .query_service import QueryService

@app.get("/api/query/foreshadowing")
async def query_foreshadowing(project_root: str):
    service = QueryService(project_root)
    return service.query_foreshadowing()
```

### 伏笔数据结构

```python
# state.json 中的伏笔记录
{
    "id": "foreshadow_1",
    "description": "神秘老者的真实身份",
    "plant_chapter": 3,
    "reveal_chapter": 25,
    "status": "planted",       # planted | revealed
    "weight": 1.5,             # 重要度权重（默认 1.0）
    "tags": ["角色", "身份"],
}

# API 返回的增强伏笔
{
    "id": "foreshadow_1",
    "description": "神秘老者的真实身份",
    "plant_chapter": 3,
    "reveal_chapter": 25,
    "status": "planted",
    "weight": 1.5,
    "tags": ["角色", "身份"],
    "urgency": 0.72,           # 计算得出
    "urgency_level": "warning", # critical/warning/normal
    "tier": "volume",          # chapter/volume/book
    "payoff_window": 22,
    "chapters_remaining": 10,
}
```

## TDD 验收

- Happy path：state.json 有 5 条伏笔 → query_foreshadowing 返回 5 条 → 按紧急度排序 → by_tier 分类正确
- Edge case 1：current_chapter > reveal_chapter → urgency=1.0 → urgency_level="critical"
- Edge case 2：status="revealed" → urgency=0.0 → urgency_level="normal"
- Error case：state.json 不存在 → 返回空列表，stats 全为 0
