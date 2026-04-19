# Task 301: ScriptAdapter 实现

## 目标

实现 ScriptAdapter，封装 scripts/ 目录下 CLI 工具的 Python API 调用层。Write 流程需要调用 extract_chapter_context.py 和 data_modules/。

## 涉及文件

- `webnovel-writer/dashboard/script_adapter.py`（修改，在 task-104 骨架基础上扩展）

## 依赖

- Phase 0 已完成
- task-104 已创建 ScriptAdapter 骨架（init_project / patch_outline / write_idea_bank）

## 前置知识

task-104 中已有的 ScriptAdapter 骨架：

```python
_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"

class ScriptAdapter:
    def __init__(self, project_root: str = ""):
        self.project_root = Path(project_root) if project_root else Path(".")

    async def init_project(self, **kwargs) -> dict: ...
    async def patch_outline(self, project_root: str, **kwargs) -> None: ...
    async def write_idea_bank(self, project_root: str, package: dict) -> None: ...
```

scripts/ 目录下的关键工具：
- `extract_chapter_context.py` — 提取章节上下文（前文摘要、设定、伏笔等）
- `data_modules/entity_extractor.py` — 实体提取
- `data_modules/summary_generator.py` — 章节摘要生成
- `data_modules/state_updater.py` — state.json 更新
- `data_modules/scene_slicer.py` — 场景切片

## 规格

### 新增方法

```python
class ScriptAdapter:
    # ... 已有方法 ...

    async def extract_chapter_context(
        self,
        chapter_num: int,
        context_window: int = 5,
    ) -> dict:
        """封装 extract_chapter_context.py 调用。

        Args:
            chapter_num: 目标章节编号
            context_window: 前文窗口大小（默认前 5 章）

        Returns:
            {
                "outline": str,          # 本章大纲
                "settings": str,         # 相关设定
                "previous_summaries": list[str],  # 前 N 章摘要
                "foreshadowing": list[dict],      # 待回收伏笔
                "character_states": dict,          # 角色当前状态
                "constraints": str,               # core-constraints
            }
        """
        script = _SCRIPTS_DIR / "extract_chapter_context.py"
        cmd = [
            sys.executable, str(script),
            str(self.project_root),
            str(chapter_num),
            "--context-window", str(context_window),
            "--format", "json",
        ]

        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, text=True,
            encoding="utf-8", timeout=60,
        )

        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr or result.stdout,
                "fallback": True,
            }

        try:
            return {"success": True, **json.loads(result.stdout)}
        except json.JSONDecodeError:
            # stdout 不是 JSON，作为纯文本返回
            return {"success": True, "raw_context": result.stdout, "fallback": True}

    async def extract_entities(self, chapter_path: str) -> dict:
        """封装 data_modules/entity_extractor.py 调用。

        Returns:
            {
                "entities": [
                    {"name": "张三", "type": "character", "attributes": {...}},
                    ...
                ]
            }
        """
        script = _SCRIPTS_DIR / "data_modules" / "entity_extractor.py"
        cmd = [sys.executable, str(script), chapter_path, "--format", "json"]

        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, text=True,
            encoding="utf-8", timeout=120,
        )

        if result.returncode != 0:
            return {"success": False, "error": result.stderr, "entities": []}

        try:
            return {"success": True, **json.loads(result.stdout)}
        except json.JSONDecodeError:
            return {"success": True, "entities": [], "raw": result.stdout}

    async def generate_summary(self, chapter_path: str) -> dict:
        """封装 data_modules/summary_generator.py 调用。

        Returns:
            {"summary": str, "key_events": list[str]}
        """
        script = _SCRIPTS_DIR / "data_modules" / "summary_generator.py"
        cmd = [sys.executable, str(script), chapter_path, "--format", "json"]

        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, text=True,
            encoding="utf-8", timeout=120,
        )

        if result.returncode != 0:
            return {"success": False, "error": result.stderr, "summary": ""}

        try:
            return {"success": True, **json.loads(result.stdout)}
        except json.JSONDecodeError:
            return {"success": True, "summary": result.stdout.strip()}

    async def update_state(self, updates: dict) -> dict:
        """封装 data_modules/state_updater.py 调用。

        Args:
            updates: 要更新的字段 dict

        Returns:
            {"success": bool, "updated_fields": list[str]}
        """
        script = _SCRIPTS_DIR / "data_modules" / "state_updater.py"
        # 通过 stdin 传入 JSON
        updates_json = json.dumps(updates, ensure_ascii=False)
        cmd = [sys.executable, str(script), str(self.project_root)]

        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, text=True,
            input=updates_json, encoding="utf-8", timeout=30,
        )

        if result.returncode != 0:
            return {"success": False, "error": result.stderr}
        return {"success": True, "updated_fields": list(updates.keys())}

    async def git_commit(self, message: str) -> dict:
        """执行 git add + commit。

        Returns:
            {"success": bool, "commit_hash": str | None, "error": str | None}
        """
        cmd_add = ["git", "-C", str(self.project_root), "add", "-A"]
        cmd_commit = ["git", "-C", str(self.project_root), "commit", "-m", message]

        result_add = await asyncio.to_thread(
            subprocess.run, cmd_add, capture_output=True, text=True, encoding="utf-8",
        )
        if result_add.returncode != 0:
            return {"success": False, "error": f"git add failed: {result_add.stderr}"}

        result_commit = await asyncio.to_thread(
            subprocess.run, cmd_commit, capture_output=True, text=True, encoding="utf-8",
        )
        if result_commit.returncode != 0:
            # nothing to commit 不算失败
            if "nothing to commit" in result_commit.stdout:
                return {"success": True, "commit_hash": None, "message": "nothing to commit"}
            return {"success": False, "error": result_commit.stderr}

        # 提取 commit hash
        import re
        match = re.search(r'\[[\w/]+ ([a-f0-9]+)\]', result_commit.stdout)
        commit_hash = match.group(1) if match else None

        return {"success": True, "commit_hash": commit_hash}

    async def load_file_context(
        self,
        chapter_num: int,
        context_window: int = 5,
    ) -> dict:
        """RAG 降级模式：直接从文件系统加载上下文。

        当 extract_chapter_context.py 不可用或无 RAG 时使用。
        从文件系统读取总纲 + 设定集 + 前 N 章摘要。

        Returns: 与 extract_chapter_context 相同的结构
        """
        project_root = self.project_root

        # 总纲
        outline_path = project_root / "大纲" / "总纲.md"
        outline = outline_path.read_text(encoding="utf-8") if outline_path.exists() else ""

        # 设定集
        setting_dir = project_root / "设定集"
        settings_text = ""
        if setting_dir.exists():
            for f in sorted(setting_dir.glob("*.md")):
                settings_text += f"\n\n## {f.stem}\n\n{f.read_text(encoding='utf-8')}"

        # 前 N 章摘要
        summaries = []
        summary_dir = project_root / ".webnovel" / "summaries"
        if summary_dir.exists():
            start = max(1, chapter_num - context_window)
            for i in range(start, chapter_num):
                sp = summary_dir / f"chapter_{i}.txt"
                if sp.exists():
                    summaries.append(sp.read_text(encoding="utf-8"))

        # 本章大纲（从卷目录中查找）
        chapter_outline = ""
        outline_dir = project_root / "大纲"
        if outline_dir.exists():
            for vol_dir in outline_dir.iterdir():
                if vol_dir.is_dir():
                    ch_file = vol_dir / f"第{chapter_num}章.json"
                    if ch_file.exists():
                        chapter_outline = ch_file.read_text(encoding="utf-8")
                        break

        return {
            "success": True,
            "fallback": True,
            "outline": chapter_outline or outline,
            "settings": settings_text,
            "previous_summaries": summaries,
            "foreshadowing": [],
            "character_states": {},
            "constraints": "",
        }
```

## TDD 验收

- Happy path：extract_chapter_context 调用成功 → 返回 JSON 结构包含 outline/settings/previous_summaries
- Edge case 1：script 返回非 JSON → fallback=True，raw_context 包含原始输出
- Edge case 2：load_file_context 降级模式 → 从文件系统读取 → 返回相同结构
- Error case：script 返回非零退出码 → success=False，error 包含 stderr
