"""题材与金手指 API 服务层。

数据源：
- genres/ 子目录名 → key（6 个核心题材的英文标识符）
- templates/genres/*.md 文件名 → label（37 个中文题材显示名）+ template
- references/genre-profiles.md → profile_id（13 个追读力配置 ID）
- templates/golden-finger-templates.md → 金手指类型列表
"""

from __future__ import annotations

import re
from pathlib import Path

# genres/ 子目录名 → 中文名 映射
_KEY_LABEL_MAP: dict[str, str] = {
    "xuanhuan": "修仙",
    "dog-blood-romance": "狗血言情",
    "rules-mystery": "规则怪谈",
    "zhihu-short": "知乎短篇",
    "period-drama": "古言",
    "realistic": "现实题材",
}

# 金手指中文名 → 英文 key
_GF_KEY_MAP: dict[str, str] = {
    "系统面板": "system",
    "随身空间": "space",
    "重生穿越": "rebirth",
    "签到打卡": "checkin",
    "器灵导师": "spirit",
    "血脉觉醒": "bloodline",
    "异能觉醒": "ability",
}


def list_genres(package_root: Path) -> dict:
    """合并三个数据源返回题材列表。

    主数据源为 templates/genres/*.md（37 个），genres/ 子目录提供 key，
    genre-profiles.md 提供 profile_id 关联。
    """
    genres_dir = package_root / "genres"
    templates_dir = package_root / "templates" / "genres"
    profiles_path = package_root / "references" / "genre-profiles.md"

    # 1. 从 templates/genres/ 扫描所有 .md 文件 → 主列表
    template_files = sorted(templates_dir.glob("*.md")) if templates_dir.is_dir() else []

    # 2. 构建 label → genres/ key 的反向映射
    label_to_key: dict[str, str] = {}
    for key, label in _KEY_LABEL_MAP.items():
        label_to_key[label] = key

    # 3. 解析 genre-profiles.md，提取 profile id → name 映射
    profile_id_to_name: dict[str, str] = {}
    if profiles_path.is_file():
        text = profiles_path.read_text(encoding="utf-8")
        current_id = None
        for line in text.splitlines():
            m_id = re.match(r"^id:\s*(\S+)", line)
            if m_id:
                current_id = m_id.group(1)
            m_name = re.match(r"^name:\s*(.+)", line)
            if m_name and current_id:
                profile_id_to_name[current_id] = m_name.group(1).strip()
                current_id = None

    # 构建 name → profile_id 反向映射（模糊匹配用）
    # profile name 如 "修仙/玄幻" 需要匹配到 label "修仙"
    name_to_profile_id: dict[str, str] = {}
    for pid, pname in profile_id_to_name.items():
        name_to_profile_id[pname] = pid

    # 4. 组装结果
    genres: list[dict] = []
    for f in template_files:
        label = f.stem  # 文件名去掉 .md 即为中文显示名
        # key：优先用 genres/ 子目录映射，否则用 label 本身
        key = label_to_key.get(label, label)
        # template
        template = f.name
        # profile_id：在 profile names 中模糊匹配
        profile_id = _match_profile_id(label, name_to_profile_id)

        genres.append({
            "key": key,
            "label": label,
            "template": template,
            "profile_id": profile_id,
        })

    return {"genres": genres}


def _match_profile_id(label: str, name_to_profile_id: dict[str, str]) -> str | None:
    """将 label 模糊匹配到 profile name，返回 profile_id。

    匹配规则：profile name 按斜杠拆分，任一部分与 label 完全匹配即可。
    例如 "修仙/玄幻" 匹配 label "修仙"。
    """
    for pname, pid in name_to_profile_id.items():
        parts = re.split(r"[/／、]", pname)
        if label in parts:
            return pid
    return None


def list_golden_finger_types(package_root: Path) -> dict:
    """解析 golden-finger-templates.md 返回金手指类型列表。"""
    gf_path = package_root / "templates" / "golden-finger-templates.md"
    types: list[dict] = []

    if gf_path.is_file():
        text = gf_path.read_text(encoding="utf-8")

        # 优先从"类型速查表" Markdown 表格提取
        in_table = False
        for line in text.splitlines():
            stripped = line.strip()
            if "类型速查表" in stripped or "类型" in stripped and "|---" in stripped:
                in_table = True
                continue
            if in_table and stripped.startswith("|"):
                cells = [c.strip() for c in stripped.split("|")]
                # 过滤空和分隔行
                cells = [c for c in cells if c]
                if not cells or cells[0] == "类型" or all(set(c) <= {"-", ":"} for c in cells):
                    continue
                type_name = cells[0]
                key = _GF_KEY_MAP.get(type_name)
                if key:
                    types.append({"key": key, "label": type_name})
            elif in_table and not stripped.startswith("|"):
                in_table = False

    # 如果表格解析未找到，尝试从二级标题提取
    if not types and gf_path.is_file():
        text = gf_path.read_text(encoding="utf-8")
        for line in text.splitlines():
            m = re.match(r"^##\s+(.+?)(?:流|型)?$", line)
            if m:
                type_name = m.group(1).strip()
                key = _GF_KEY_MAP.get(type_name)
                if key:
                    types.append({"key": key, "label": type_name})

    # 始终追加"无金手指"选项
    types.append({"key": "none", "label": "无金手指"})

    return {"types": types}
