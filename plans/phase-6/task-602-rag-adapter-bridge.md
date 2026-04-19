# Task 602: ScriptAdapter 封装 rag_adapter.py

## 目标

在 ScriptAdapter 中封装 `scripts/data_modules/rag_adapter.py` 的调用，提供向量索引构建和检索的 Python API。

## 涉及文件

- `webnovel-writer/dashboard/script_adapter.py`（修改，新增 RAG 相关方法）

## 依赖

- task-601（RAG 配置 API 已实现，.env 中有 Embedding 配置）
- task-301（ScriptAdapter 已有基础方法）

## 前置知识

`scripts/data_modules/rag_adapter.py` 是 CLI 时代的 RAG 封装，提供：
- `build-index` — 构建向量索引（扫描正文+设定+摘要 → 切片 → Embedding → 存储）
- `search` — 向量检索（query → Embedding → 相似度搜索 → Rerank → 返回结果）
- `add-doc` — 增量添加文档到索引

索引存储在 `.webnovel/rag/` 目录。

## 规格

### 新增方法

```python
class ScriptAdapter:
    # ... 已有方法 ...

    async def rag_build_index(
        self,
        on_progress: callable = None,
    ) -> dict:
        """构建向量索引。

        扫描项目中的正文、设定集、摘要等文件，切片后生成向量索引。
        这是耗时操作（可能几分钟），通过 on_progress 回调推送进度。

        Args:
            on_progress: 可选回调 (progress: float, message: str) -> None

        Returns:
            {
                "success": bool,
                "doc_count": int,
                "build_time_seconds": float,
                "error": str | None,
            }
        """
        script = _SCRIPTS_DIR / "data_modules" / "rag_adapter.py"
        cmd = [
            sys.executable, str(script),
            "build-index",
            str(self.project_root),
            "--format", "json",
        ]

        import time
        start_time = time.time()

        # 使用 subprocess.Popen 以便读取实时输出
        process = await asyncio.to_thread(
            subprocess.Popen,
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )

        # 读取输出（简化：等待完成）
        stdout, stderr = await asyncio.to_thread(process.communicate, timeout=600)
        build_time = time.time() - start_time

        if process.returncode != 0:
            return {
                "success": False,
                "doc_count": 0,
                "build_time_seconds": round(build_time, 1),
                "error": stderr or stdout,
            }

        # 解析结果
        try:
            result = json.loads(stdout)
            doc_count = result.get("doc_count", 0)
        except json.JSONDecodeError:
            doc_count = 0

        # 写入索引元数据
        self._write_index_meta(doc_count, build_time)

        return {
            "success": True,
            "doc_count": doc_count,
            "build_time_seconds": round(build_time, 1),
            "error": None,
        }

    async def rag_search(
        self,
        query: str,
        top_k: int = 10,
    ) -> dict:
        """向量检索。

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            {
                "success": bool,
                "results": [
                    {
                        "text": str,
                        "source": str,      # 来源文件
                        "score": float,      # 相似度分数
                        "metadata": dict,    # 章节号、类型等
                    },
                ],
                "error": str | None,
            }
        """
        script = _SCRIPTS_DIR / "data_modules" / "rag_adapter.py"
        cmd = [
            sys.executable, str(script),
            "search",
            str(self.project_root),
            "--query", query,
            "--top-k", str(top_k),
            "--format", "json",
        ]

        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, text=True,
            encoding="utf-8", timeout=30,
        )

        if result.returncode != 0:
            return {"success": False, "results": [], "error": result.stderr}

        try:
            data = json.loads(result.stdout)
            return {"success": True, "results": data.get("results", []), "error": None}
        except json.JSONDecodeError:
            return {"success": True, "results": [], "error": "无法解析搜索结果"}

    async def rag_add_doc(self, doc_path: str, doc_type: str = "chapter") -> dict:
        """增量添加文档到索引。

        Args:
            doc_path: 文档路径
            doc_type: 文档类型（chapter/setting/summary）

        Returns:
            {"success": bool, "chunks_added": int}
        """
        script = _SCRIPTS_DIR / "data_modules" / "rag_adapter.py"
        cmd = [
            sys.executable, str(script),
            "add-doc",
            str(self.project_root),
            "--path", doc_path,
            "--type", doc_type,
            "--format", "json",
        ]

        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, text=True,
            encoding="utf-8", timeout=60,
        )

        if result.returncode != 0:
            return {"success": False, "chunks_added": 0, "error": result.stderr}

        try:
            data = json.loads(result.stdout)
            return {"success": True, "chunks_added": data.get("chunks_added", 0)}
        except json.JSONDecodeError:
            return {"success": True, "chunks_added": 0}

    def rag_is_available(self) -> bool:
        """检查 RAG 是否可用（有配置 + 有索引）。"""
        env_path = self.project_root / ".env"
        if not env_path.exists():
            return False

        env_content = env_path.read_text(encoding="utf-8")
        has_config = "RAG_EMBEDDING_MODEL" in env_content and "RAG_EMBEDDING_API_KEY" in env_content

        index_meta = self.project_root / ".webnovel" / "rag" / "index_meta.json"
        has_index = index_meta.exists()

        return has_config and has_index

    def _write_index_meta(self, doc_count: int, build_time: float) -> None:
        """写入索引元数据。"""
        from datetime import datetime
        meta_dir = self.project_root / ".webnovel" / "rag"
        meta_dir.mkdir(parents=True, exist_ok=True)
        meta_path = meta_dir / "index_meta.json"
        meta = {
            "doc_count": doc_count,
            "build_time_seconds": round(build_time, 1),
            "built_at": datetime.now().isoformat(),
        }
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
```

## TDD 验收

- Happy path：rag_build_index 调用成功 → 返回 doc_count > 0 → index_meta.json 已写入
- Edge case 1：rag_is_available 无 .env → 返回 False
- Edge case 2：rag_search 返回空结果 → results=[] 不报错
- Error case：rag_adapter.py 不存在 → 返回 success=False + error 信息
