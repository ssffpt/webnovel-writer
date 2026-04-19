# Task 601: RAG 配置 API + .env 管理

## 目标

实现 RAG 配置后端 API，管理 Embedding/Rerank 模型配置，存储到 `.env` 文件。

## 涉及文件

- `webnovel-writer/dashboard/rag_config_service.py`（新建）
- `webnovel-writer/dashboard/app.py`（修改，注册 API 端点）

## 依赖

- Phase 0 已完成（FastAPI app 可用）

## 前置知识

RAG 依赖两个外部模型：
- Embedding 模型（如 text-embedding-3-small）— 将文本转为向量
- Rerank 模型（可选）— 对检索结果重排序

配置存储在项目根目录的 `.env` 文件中：
```
RAG_EMBEDDING_MODEL=text-embedding-3-small
RAG_EMBEDDING_API_KEY=sk-xxx
RAG_EMBEDDING_BASE_URL=https://api.openai.com/v1
RAG_RERANK_MODEL=rerank-v3
RAG_RERANK_API_KEY=sk-xxx
RAG_RERANK_BASE_URL=https://api.cohere.ai/v1
```

## 规格

### rag_config_service.py

```python
"""RAGConfigService — RAG 配置管理。"""

import os
from pathlib import Path


class RAGConfigService:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.env_path = self.project_root / ".env"

    def get_config(self) -> dict:
        """读取当前 RAG 配置。

        Returns:
            {
                "configured": bool,
                "embedding": {
                    "model": str,
                    "base_url": str,
                    "has_api_key": bool,  # 不返回实际 key
                },
                "rerank": {
                    "model": str,
                    "base_url": str,
                    "has_api_key": bool,
                },
                "index_status": {
                    "exists": bool,
                    "doc_count": int,
                    "last_built": str | None,
                },
            }
        """
        env_vars = self._load_env()

        embedding_model = env_vars.get("RAG_EMBEDDING_MODEL", "")
        embedding_key = env_vars.get("RAG_EMBEDDING_API_KEY", "")
        rerank_model = env_vars.get("RAG_RERANK_MODEL", "")
        rerank_key = env_vars.get("RAG_RERANK_API_KEY", "")

        configured = bool(embedding_model and embedding_key)

        # 检查索引状态
        index_status = self._check_index_status()

        return {
            "configured": configured,
            "embedding": {
                "model": embedding_model,
                "base_url": env_vars.get("RAG_EMBEDDING_BASE_URL", ""),
                "has_api_key": bool(embedding_key),
            },
            "rerank": {
                "model": rerank_model,
                "base_url": env_vars.get("RAG_RERANK_BASE_URL", ""),
                "has_api_key": bool(rerank_key),
            },
            "index_status": index_status,
        }

    def save_config(self, config: dict) -> dict:
        """保存 RAG 配置到 .env。

        Args:
            config: {
                "embedding_model": str,
                "embedding_api_key": str,
                "embedding_base_url": str,
                "rerank_model": str,
                "rerank_api_key": str,
                "rerank_base_url": str,
            }

        Returns:
            {"success": bool, "message": str}
        """
        env_vars = self._load_env()

        # 更新 RAG 相关变量
        rag_keys = {
            "RAG_EMBEDDING_MODEL": config.get("embedding_model", ""),
            "RAG_EMBEDDING_API_KEY": config.get("embedding_api_key", ""),
            "RAG_EMBEDDING_BASE_URL": config.get("embedding_base_url", ""),
            "RAG_RERANK_MODEL": config.get("rerank_model", ""),
            "RAG_RERANK_API_KEY": config.get("rerank_api_key", ""),
            "RAG_RERANK_BASE_URL": config.get("rerank_base_url", ""),
        }

        for key, value in rag_keys.items():
            if value:  # 只更新非空值
                env_vars[key] = value

        self._save_env(env_vars)

        return {"success": True, "message": "RAG 配置已保存"}

    def test_connection(self) -> dict:
        """测试 Embedding API 连接。

        Returns:
            {"success": bool, "message": str, "latency_ms": int | None}
        """
        env_vars = self._load_env()
        model = env_vars.get("RAG_EMBEDDING_MODEL", "")
        api_key = env_vars.get("RAG_EMBEDDING_API_KEY", "")
        base_url = env_vars.get("RAG_EMBEDDING_BASE_URL", "")

        if not model or not api_key:
            return {"success": False, "message": "未配置 Embedding 模型或 API Key"}

        # 简单测试：尝试 embed 一个短文本
        import time
        try:
            import httpx
            start = time.time()
            resp = httpx.post(
                f"{base_url}/embeddings",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "input": "测试连接"},
                timeout=10,
            )
            latency = int((time.time() - start) * 1000)

            if resp.status_code == 200:
                return {"success": True, "message": "连接成功", "latency_ms": latency}
            else:
                return {"success": False, "message": f"API 返回 {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "message": f"连接失败: {str(e)}"}

    def _check_index_status(self) -> dict:
        """检查向量索引状态。"""
        import json
        rag_dir = self.project_root / ".webnovel" / "rag"
        index_meta = rag_dir / "index_meta.json"

        if not index_meta.exists():
            return {"exists": False, "doc_count": 0, "last_built": None}

        try:
            meta = json.loads(index_meta.read_text(encoding="utf-8"))
            return {
                "exists": True,
                "doc_count": meta.get("doc_count", 0),
                "last_built": meta.get("built_at", None),
            }
        except json.JSONDecodeError:
            return {"exists": False, "doc_count": 0, "last_built": None}

    def _load_env(self) -> dict:
        """读取 .env 文件为 dict。"""
        env_vars = {}
        if self.env_path.exists():
            for line in self.env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
        return env_vars

    def _save_env(self, env_vars: dict) -> None:
        """将 dict 写回 .env 文件，保留注释和非 RAG 变量。"""
        lines = []
        existing_keys = set()

        # 保留原有内容，更新已有 key
        if self.env_path.exists():
            for line in self.env_path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    key = stripped.partition("=")[0].strip()
                    if key in env_vars:
                        lines.append(f"{key}={env_vars[key]}")
                        existing_keys.add(key)
                    else:
                        lines.append(line)
                else:
                    lines.append(line)

        # 追加新 key
        for key, value in env_vars.items():
            if key not in existing_keys and value:
                lines.append(f"{key}={value}")

        self.env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
```

### API 端点

```python
from .rag_config_service import RAGConfigService

@app.get("/api/rag/config")
async def get_rag_config(project_root: str):
    service = RAGConfigService(project_root)
    return service.get_config()

@app.post("/api/rag/config")
async def save_rag_config(project_root: str, config: dict):
    service = RAGConfigService(project_root)
    return service.save_config(config)

@app.post("/api/rag/test")
async def test_rag_connection(project_root: str):
    service = RAGConfigService(project_root)
    return service.test_connection()
```

## TDD 验收

- Happy path：save_config 写入 .env → get_config 读取 → configured=True → has_api_key=True
- Edge case 1：.env 不存在 → get_config 返回 configured=False，不报错
- Edge case 2：save_config 只更新 RAG 变量，保留 .env 中其他变量不变
- Error case：test_connection 无网络 → 返回 success=False + 错误信息
