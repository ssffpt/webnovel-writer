# Task 502: 节奏分析 API（Strand 连续/断档）

## 目标

实现节奏分析后端 API，检测各 Strand 的连续性和断档情况。

## 涉及文件

- `webnovel-writer/dashboard/query_service.py`（修改，新增方法）

## 依赖

- task-501（QueryService 已创建）

## 前置知识

Strand 数据来源：
- 章节大纲中的 `strand` 字段（Plan Step 6 生成）
- `index.db` 中的 scenes 表（Data Agent 写入的场景切片）

节奏分析维度：
- 各 Strand 的章节分布（哪些章节涉及哪条线）
- 连续性检测：某条线连续 N 章未出现 → 断档
- 断档阈值：主线 > 3 章断档为警告，支线 > 5 章断档为警告

## 规格

### 新增方法

```python
class QueryService:
    # ... 已有方法 ...

    def query_rhythm(self) -> dict:
        """节奏分析：Strand 连续/断档检测。

        Returns:
            {
                "strands": [
                    {
                        "name": "主线",
                        "chapters": [1, 2, 3, 5, 6],
                        "total_chapters": 5,
                        "gaps": [{"start": 3, "end": 5, "length": 1}],
                        "max_gap": 1,
                        "status": "normal",  # normal / warning / critical
                    },
                ],
                "timeline": [
                    {"chapter": 1, "strands": ["主线", "感情线"]},
                    {"chapter": 2, "strands": ["主线"]},
                ],
                "warnings": [...],
            }
        """
        state = self._load_state()
        chapter_outlines = self._load_all_chapter_outlines()

        # 从章节大纲中提取 Strand 分布
        strand_chapters = {}  # {strand_name: [chapter_nums]}
        timeline = []

        for ch_num in sorted(chapter_outlines.keys()):
            outline = chapter_outlines[ch_num]
            strand = outline.get("strand", "主线")
            strand_chapters.setdefault(strand, []).append(ch_num)
            timeline.append({"chapter": ch_num, "strands": [strand]})

        # 分析各 Strand
        strands_analysis = []
        warnings = []

        for strand_name, chapters in strand_chapters.items():
            gaps = self._detect_gaps(chapters)
            max_gap = max((g["length"] for g in gaps), default=0)

            # 断档阈值
            threshold = 3 if strand_name == "主线" else 5
            if max_gap > threshold * 2:
                status = "critical"
            elif max_gap > threshold:
                status = "warning"
            else:
                status = "normal"

            strand_info = {
                "name": strand_name,
                "chapters": chapters,
                "total_chapters": len(chapters),
                "gaps": gaps,
                "max_gap": max_gap,
                "status": status,
            }
            strands_analysis.append(strand_info)

            if status != "normal":
                for gap in gaps:
                    if gap["length"] > threshold:
                        warnings.append({
                            "strand": strand_name,
                            "gap_start": gap["start"],
                            "gap_end": gap["end"],
                            "gap_length": gap["length"],
                            "severity": status,
                            "message": f"「{strand_name}」在第{gap['start']}-{gap['end']}章断档 {gap['length']} 章",
                        })

        return {
            "strands": strands_analysis,
            "timeline": timeline,
            "warnings": warnings,
        }

    def _detect_gaps(self, chapters: list[int]) -> list[dict]:
        """检测章节序列中的断档。"""
        if len(chapters) < 2:
            return []

        gaps = []
        sorted_chs = sorted(chapters)
        for i in range(1, len(sorted_chs)):
            gap_length = sorted_chs[i] - sorted_chs[i - 1] - 1
            if gap_length > 0:
                gaps.append({
                    "start": sorted_chs[i - 1],
                    "end": sorted_chs[i],
                    "length": gap_length,
                })
        return gaps

    def _load_all_chapter_outlines(self) -> dict:
        """加载所有章节大纲。"""
        outlines = {}
        outline_dir = self.project_root / "大纲"
        if not outline_dir.exists():
            return outlines

        for vol_dir in outline_dir.iterdir():
            if vol_dir.is_dir():
                for ch_file in vol_dir.glob("第*章.json"):
                    try:
                        data = json.loads(ch_file.read_text(encoding="utf-8"))
                        ch_num = data.get("chapter")
                        if ch_num is not None:
                            outlines[ch_num] = data
                    except (json.JSONDecodeError, KeyError):
                        pass

        return outlines
```

### API 端点

```python
@app.get("/api/query/rhythm")
async def query_rhythm(project_root: str):
    service = QueryService(project_root)
    return service.query_rhythm()
```

## TDD 验收

- Happy path：10 章大纲含主线+感情线 → 返回 2 个 strand → timeline 有 10 条 → gaps 正确检测
- Edge case 1：主线连续 5 章断档 → status="critical" → warnings 包含断档信息
- Edge case 2：无章节大纲 → 返回空 strands/timeline/warnings
- Error case：某章大纲 JSON 格式错误 → 跳过该章，不崩溃
