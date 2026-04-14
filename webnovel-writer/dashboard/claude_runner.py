from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Any

_CHAPTER_RE = re.compile(r"第0*(\d+)章")
_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "webnovel.py"


def run_action(action: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Phase 2 任务执行适配层。

    当前优先复用项目内已经稳定存在的统一 CLI：
    - 一律先跑 preflight，确保 project_root 可用
    - 章节类动作额外调用 extract-context，形成真实命令链
    - 大纲/设定类动作先走 preflight + 路径校验，保留统一任务生命周期与日志输出

    说明：仓库当前并未暴露可直接非交互调用的 `/webnovel-write` / `/webnovel-plan` / `/webnovel-review`
    等完整技能入口，因此这里先实现“半真实命令映射”，后续可再替换为真正的命令桥接。
    """
    context = context or {}
    action_type = action.get("type", "unknown")
    label = action.get("label") or action_type
    params = action.get("params") or {}
    project_root = Path(context.get("projectRoot") or ".").resolve()
    selected_path = params.get("path") or context.get("selectedPath")

    if action_type == "force_fail":
        return {
            "success": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": f"{label} 执行失败",
            "result": None,
        }

    preflight = _run_cli(project_root, "preflight")
    if preflight.returncode != 0:
        return _failure(label, preflight, summary="preflight 校验失败")

    if action_type in {"write_chapter", "review_chapter"}:
        chapter_num = _extract_chapter_num(selected_path)
        if chapter_num is None:
            return {
                "success": False,
                "exit_code": 2,
                "stdout": preflight.stdout,
                "stderr": f"无法从路径解析章节号: {selected_path}",
                "result": None,
            }
        extract = _run_cli(project_root, "extract-context", "--chapter", str(chapter_num), "--format", "json")
        if extract.returncode != 0:
            return _failure(label, extract, summary="章节上下文提取失败", inherited_stdout=preflight.stdout)
        return {
            "success": True,
            "exit_code": 0,
            "stdout": _join_stdout(preflight.stdout, extract.stdout),
            "stderr": "",
            "result": {
                "actionType": action_type,
                "label": label,
                "params": params,
                "context": context,
                "summary": f"{label} 已完成（已执行 preflight + extract-context）",
                "chapter": chapter_num,
            },
        }

    if action_type in {"plan_outline", "inspect_setting"}:
        if selected_path:
            target = project_root / selected_path
            exists = target.exists()
            stdout = _join_stdout(preflight.stdout, f"target_exists={exists}\ntarget={target}")
            if not exists:
                return {
                    "success": False,
                    "exit_code": 3,
                    "stdout": stdout,
                    "stderr": f"目标文件不存在: {selected_path}",
                    "result": None,
                }
            return {
                "success": True,
                "exit_code": 0,
                "stdout": stdout,
                "stderr": "",
                "result": {
                    "actionType": action_type,
                    "label": label,
                    "params": params,
                    "context": context,
                    "summary": f"{label} 已完成（已执行 preflight + 文件校验）",
                    "targetPath": selected_path,
                },
            }

    return {
        "success": True,
        "exit_code": 0,
        "stdout": preflight.stdout,
        "stderr": "",
        "result": {
            "actionType": action_type,
            "label": label,
            "params": params,
            "context": context,
            "summary": f"{label} 已完成（已执行 preflight）",
        },
    }


def _run_cli(project_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(_SCRIPT_PATH), "--project-root", str(project_root), *args]
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")


def _extract_chapter_num(path: str | None) -> int | None:
    if not path:
        return None
    match = _CHAPTER_RE.search(path)
    return int(match.group(1)) if match else None


def _failure(label: str, result: subprocess.CompletedProcess[str], *, summary: str, inherited_stdout: str = "") -> dict[str, Any]:
    return {
        "success": False,
        "exit_code": result.returncode,
        "stdout": _join_stdout(inherited_stdout, result.stdout),
        "stderr": result.stderr,
        "result": {
            "actionType": label,
            "summary": summary,
        },
    }


def _join_stdout(*parts: str) -> str:
    return "\n".join(part.strip() for part in parts if part and part.strip())
