# Task 505: OverviewPage 创作仪表盘

## 目标

在 OverviewPage 新增创作仪表盘，展示总字数/章节进度/审查覆盖率/伏笔回收率。

## 涉及文件

- `webnovel-writer/dashboard/frontend/src/workbench/OverviewPage.jsx`（修改）
- `webnovel-writer/dashboard/frontend/src/api.js`（修改，新增仪表盘 API）

## 依赖

- task-504（查询 API 已全部可用）

## 前置知识

OverviewPage 当前结构：项目概况 + StepProgressBar + 下一步建议。

仪表盘数据来源：
- 总字数 / 章节进度 → state.json
- 审查覆盖率 → state.json 中各章的 reviewed_at 字段
- 伏笔回收率 → query_foreshadowing API

## 规格

### 后端 API

在 `query_service.py` 中新增：

```python
class QueryService:
    # ... 已有方法 ...

    def query_dashboard(self) -> dict:
        """创作仪表盘数据。

        Returns:
            {
                "word_count": {
                    "total": 45000,
                    "target": 2000000,
                    "progress": 0.0225,
                },
                "chapters": {
                    "written": 20,
                    "planned": 600,
                    "progress": 0.033,
                },
                "review": {
                    "reviewed": 15,
                    "total_written": 20,
                    "coverage": 0.75,
                    "avg_score": 7.5,
                },
                "foreshadowing": {
                    "total": 12,
                    "revealed": 5,
                    "recovery_rate": 0.417,
                    "overdue": 2,
                },
                "recent_activity": [...],
            }
        """
        state = self._load_state()
        chapters = state.get("chapters", {})

        # 字数统计
        total_words = sum(ch.get("word_count", 0) for ch in chapters.values())
        target_words = state.get("target_words", 2000000)

        # 章节进度
        written = len([ch for ch in chapters.values() if ch.get("status") == "written"])
        planned = state.get("target_chapters", 600)

        # 审查覆盖率
        reviewed = len([ch for ch in chapters.values() if ch.get("reviewed_at")])
        avg_score = 0
        review_scores = [ch.get("review_score", 0) for ch in chapters.values() if ch.get("review_score")]
        if review_scores:
            avg_score = sum(review_scores) / len(review_scores)

        # 伏笔回收率
        fs_data = self.query_foreshadowing()
        fs_stats = fs_data.get("stats", {})

        # 最近活动
        recent = self._get_recent_activity(state)

        return {
            "word_count": {
                "total": total_words,
                "target": target_words,
                "progress": round(total_words / max(target_words, 1), 4),
            },
            "chapters": {
                "written": written,
                "planned": planned,
                "progress": round(written / max(planned, 1), 4),
            },
            "review": {
                "reviewed": reviewed,
                "total_written": written,
                "coverage": round(reviewed / max(written, 1), 2),
                "avg_score": round(avg_score, 1),
            },
            "foreshadowing": {
                "total": fs_stats.get("total", 0),
                "revealed": fs_stats.get("revealed", 0),
                "recovery_rate": round(fs_stats.get("recovery_rate", 0), 2),
                "overdue": fs_stats.get("overdue", 0),
            },
            "recent_activity": recent,
        }

    def _get_recent_activity(self, state: dict) -> list[dict]:
        """获取最近活动（最近 5 条）。"""
        activities = []
        chapters = state.get("chapters", {})

        for ch_key, ch_data in chapters.items():
            if ch_data.get("reviewed_at"):
                activities.append({
                    "type": "review",
                    "chapter": int(ch_key),
                    "time": ch_data["reviewed_at"],
                    "detail": f"第{ch_key}章审查完成，评分 {ch_data.get('review_score', '-')}",
                })
            if ch_data.get("status") == "written":
                activities.append({
                    "type": "write",
                    "chapter": int(ch_key),
                    "time": ch_data.get("written_at", ""),
                    "detail": f"第{ch_key}章写作完成，{ch_data.get('word_count', 0)} 字",
                })

        # 按时间倒序，取最近 5 条
        activities.sort(key=lambda x: x.get("time", ""), reverse=True)
        return activities[:5]
```

API 端点：

```python
@app.get("/api/query/dashboard")
async def query_dashboard(project_root: str):
    service = QueryService(project_root)
    return service.query_dashboard()
```

### 前端 api.js 新增

```javascript
export async function queryDashboard(projectRoot) {
  const res = await fetch(`/api/query/dashboard?project_root=${encodeURIComponent(projectRoot)}`)
  return res.json()
}
```

### OverviewPage 改造

```jsx
import { useState, useEffect } from 'react'
import { queryDashboard } from '../api'

// 在 OverviewPage 中新增仪表盘区域
function Dashboard({ projectRoot }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    queryDashboard(projectRoot).then(setData)
  }, [projectRoot])

  if (!data) return <p>加载中...</p>

  return (
    <div className="dashboard">
      <h3>创作仪表盘</h3>

      <div className="dashboard-grid">
        {/* 总字数 */}
        <DashboardCard
          title="总字数"
          value={formatNumber(data.word_count.total)}
          target={formatNumber(data.word_count.target)}
          progress={data.word_count.progress}
        />

        {/* 章节进度 */}
        <DashboardCard
          title="章节进度"
          value={`${data.chapters.written} 章`}
          target={`${data.chapters.planned} 章`}
          progress={data.chapters.progress}
        />

        {/* 审查覆盖率 */}
        <DashboardCard
          title="审查覆盖率"
          value={`${(data.review.coverage * 100).toFixed(0)}%`}
          subtitle={`平均分 ${data.review.avg_score}`}
          progress={data.review.coverage}
          color={data.review.coverage >= 0.8 ? 'green' : data.review.coverage >= 0.5 ? 'yellow' : 'red'}
        />

        {/* 伏笔回收率 */}
        <DashboardCard
          title="伏笔回收率"
          value={`${(data.foreshadowing.recovery_rate * 100).toFixed(0)}%`}
          subtitle={`${data.foreshadowing.overdue} 条超期`}
          progress={data.foreshadowing.recovery_rate}
          color={data.foreshadowing.overdue > 0 ? 'red' : 'green'}
        />
      </div>

      {/* 最近活动 */}
      {data.recent_activity?.length > 0 && (
        <div className="recent-activity">
          <h4>最近活动</h4>
          {data.recent_activity.map((a, i) => (
            <div key={i} className={`activity-item type-${a.type}`}>
              <span className="activity-type">{a.type === 'write' ? '写作' : '审查'}</span>
              <span className="activity-detail">{a.detail}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function DashboardCard({ title, value, target, subtitle, progress, color }) {
  const barColor = color || (progress >= 0.5 ? 'green' : progress >= 0.2 ? 'yellow' : 'red')

  return (
    <div className="dashboard-card">
      <div className="card-title">{title}</div>
      <div className="card-value">{value}</div>
      {target && <div className="card-target">/ {target}</div>}
      {subtitle && <div className="card-subtitle">{subtitle}</div>}
      <div className="progress-bar">
        <div
          className={`progress-fill color-${barColor}`}
          style={{ width: `${Math.min(progress * 100, 100)}%` }}
        />
      </div>
    </div>
  )
}

function formatNumber(num) {
  if (num >= 10000) return `${(num / 10000).toFixed(1)} 万`
  return num.toString()
}
```

### OverviewPage 集成位置

```jsx
// OverviewPage.jsx 中
export default function OverviewPage({ projectRoot }) {
  return (
    <div className="overview-page">
      {/* 原有的项目概况 */}
      <ProjectInfo ... />

      {/* 新增：创作仪表盘 */}
      <Dashboard projectRoot={projectRoot} />

      {/* 原有的 StepProgressBar（改为反映真实创作阶段） */}
      <CreationProgress ... />

      {/* 原有的下一步建议 */}
      <NextStepSuggestions ... />
    </div>
  )
}
```

## TDD 验收

- Happy path：OverviewPage 显示仪表盘 → 4 个指标卡片正确渲染 → 进度条颜色正确
- Edge case 1：无章节数据 → 所有指标为 0，进度条为空
- Edge case 2：审查覆盖率 100% → 进度条满格绿色
- Error case：API 返回错误 → 显示"加载中..."不崩溃
