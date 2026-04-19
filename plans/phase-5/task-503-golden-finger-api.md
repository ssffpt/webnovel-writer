# Task 503: 金手指状态 + 债务查询 API

## 目标

实现金手指状态查询和伏笔债务查询后端 API。

## 涉及文件

- `webnovel-writer/dashboard/query_service.py`（修改，新增方法）

## 依赖

- task-502（QueryService 已有 query_foreshadowing / query_rhythm）

## 前置知识

金手指数据来源：
- `state.json` 中的 `golden_finger` 对象（Init Step 3 写入）
- 设定集中的 `力量体系.md`

债务 = 超期未回收的伏笔，是 query_foreshadowing 的子集视图。

## 规格

### 新增方法

```python
class QueryService:
    # ... 已有方法 ...

    def query_golden_finger(self) -> dict:
        """查询金手指当前状态。

        Returns:
            {
                "golden_finger": {
                    "name": "xxx系统",
                    "type": "系统流",
                    "current_level": 3,
                    "skills": [...],
                    "upgrade_conditions": [...],
                    "growth_style": "阶梯式",
                    "visibility": "仅主角可见",
                    "cost": "每次使用消耗寿命",
                    "development_suggestions": [...],
                },
                "history": [...],  # 等级变化历史
            }
        """
        state = self._load_state()
        gf = state.get("golden_finger", {})

        if not gf:
            # 尝试从 init context 中读取
            gf = self._load_golden_finger_from_init()

        # 发展建议
        suggestions = self._generate_gf_suggestions(gf, state)

        return {
            "golden_finger": {
                **gf,
                "development_suggestions": suggestions,
            },
            "history": state.get("golden_finger_history", []),
        }

    def _load_golden_finger_from_init(self) -> dict:
        """从 init 数据中加载金手指信息。"""
        # 尝试从 state.json 的 init_context 中读取
        state = self._load_state()
        init_ctx = state.get("init_context", {})
        return {
            "name": init_ctx.get("golden_finger_name", ""),
            "type": init_ctx.get("golden_finger_type", ""),
            "growth_style": init_ctx.get("golden_finger_growth", ""),
            "visibility": init_ctx.get("golden_finger_visibility", ""),
            "cost": init_ctx.get("golden_finger_cost", ""),
            "current_level": 1,
            "skills": [],
            "upgrade_conditions": [],
        }

    def _generate_gf_suggestions(self, gf: dict, state: dict) -> list[str]:
        """根据当前进度生成金手指发展建议。"""
        suggestions = []
        current_chapter = state.get("last_written_chapter", 0)
        level = gf.get("current_level", 1)

        if current_chapter > 20 and level <= 1:
            suggestions.append("已写 20+ 章但金手指仍为初始等级，考虑安排升级事件")
        if gf.get("growth_style") == "阶梯式" and current_chapter % 30 == 0:
            suggestions.append("阶梯式成长节点到达，建议安排等级突破")

        return suggestions

    def query_debts(self) -> dict:
        """查询伏笔债务（超期未回收的伏笔），按紧急度排序。

        Returns:
            {
                "debts": [
                    {
                        "id": "foreshadow_1",
                        "description": "...",
                        "plant_chapter": 3,
                        "reveal_chapter": 10,
                        "overdue_by": 5,
                        "urgency": 1.0,
                        "urgency_level": "critical",
                        "suggested_action": "在最近章节安排揭示",
                    },
                ],
                "stats": {
                    "total_debts": int,
                    "critical_debts": int,
                    "avg_overdue": float,
                },
            }
        """
        foreshadowing_data = self.query_foreshadowing()
        all_items = foreshadowing_data.get("foreshadowing", [])
        current_chapter = self._get_current_chapter()

        # 筛选超期未回收的
        debts = []
        for item in all_items:
            if item["status"] == "planted" and current_chapter > item.get("reveal_chapter", 999):
                overdue_by = current_chapter - item["reveal_chapter"]
                debt = {
                    **item,
                    "overdue_by": overdue_by,
                    "suggested_action": self._suggest_debt_action(item, overdue_by),
                }
                debts.append(debt)

        # 按紧急度排序
        debts.sort(key=lambda x: x["urgency"], reverse=True)

        critical_debts = sum(1 for d in debts if d["urgency_level"] == "critical")
        avg_overdue = sum(d["overdue_by"] for d in debts) / max(len(debts), 1)

        return {
            "debts": debts,
            "stats": {
                "total_debts": len(debts),
                "critical_debts": critical_debts,
                "avg_overdue": round(avg_overdue, 1),
            },
        }

    def _suggest_debt_action(self, item: dict, overdue_by: int) -> str:
        """为超期伏笔生成建议操作。"""
        if overdue_by > 20:
            return "严重超期，建议在下一章立即安排揭示或转化为新伏笔"
        elif overdue_by > 10:
            return "明显超期，建议在近 3 章内安排揭示"
        else:
            return "轻微超期，可在本卷内安排揭示"
```

### API 端点

```python
@app.get("/api/query/golden-finger")
async def query_golden_finger(project_root: str):
    service = QueryService(project_root)
    return service.query_golden_finger()

@app.get("/api/query/debts")
async def query_debts(project_root: str):
    service = QueryService(project_root)
    return service.query_debts()
```

## TDD 验收

- Happy path：state.json 有 golden_finger 数据 → 返回完整金手指状态 + 发展建议
- Edge case 1：golden_finger 为空 → 从 init_context 降级读取
- Edge case 2：3 条伏笔超期 → debts 返回 3 条 → 按紧急度排序
- Error case：state.json 不存在 → golden_finger 返回空，debts 返回空列表
