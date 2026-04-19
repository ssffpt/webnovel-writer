# Task 103: Init Step 5 创意约束包生成

## 目标

实现 Step 5 的 auto 部分：基于前 4 步采集的信息，调用 AI API 生成 2-3 套创意约束包供用户选择。

## 涉及文件

- `webnovel-writer/dashboard/skill_handlers/init_handler.py`（修改 execute_step）

## 依赖

- task-102（Step 1-4 数据已在 context 中）

## 前置知识

Step 5 是 `confirm` 类型。SkillRunner 的处理流程：
1. 进入 Step 5 → 调用 `execute_step()` 生成 output_data
2. output_data 返回给前端展示（创意包卡片）
3. 前端用户选择后 → 调用 `submit_input()` 提交选择
4. `validate_input()` 校验 → 通过后 advance

## 规格

### execute_step（Step 5）

```python
async def execute_step(self, step: StepState, context: dict) -> dict:
    if step.step_id == "step_5":
        # 从 context 中提取前 4 步的关键信息
        title = context.get("title", "")
        genres = context.get("genres", [])
        one_line_story = context.get("one_line_story", "")
        core_conflict = context.get("core_conflict", "")
        protagonist_desire = context.get("protagonist_desire", "")
        protagonist_flaw = context.get("protagonist_flaw", "")
        golden_finger_type = context.get("golden_finger_type", "")

        # 调用 AI API 生成创意约束包
        packages = await self._generate_creativity_packages(
            title=title,
            genres=genres,
            one_line_story=one_line_story,
            core_conflict=core_conflict,
            protagonist_desire=protagonist_desire,
            protagonist_flaw=protagonist_flaw,
            golden_finger_type=golden_finger_type,
        )

        return {
            "packages": packages,  # 2-3 套创意包
            "instruction": "请选择一套创意约束包，或提出修改意见",
        }
```

### 创意约束包结构

每套创意包包含：

```python
{
    "id": "pkg_1",
    "name": "反套路包A",
    "description": "简述这套约束的核心思路",
    "constraints": [
        {"type": "anti_trope", "content": "禁止XXX套路"},
        {"type": "must_have", "content": "必须包含XXX"},
        {"type": "rhythm", "content": "每N章必须XXX"},
    ],
    "score": {  # 五维评分（AI 自评）
        "novelty": 8,       # 新颖度
        "feasibility": 7,   # 可执行性
        "reader_hook": 9,   # 读者吸引力
        "consistency": 8,   # 内在一致性
        "differentiation": 7,  # 差异化
    },
}
```

### _generate_creativity_packages 方法

```python
async def _generate_creativity_packages(self, **kwargs) -> list[dict]:
    """调用 AI API 生成创意约束包。

    Prompt 要点：
    - 基于题材 + 故事核 + 角色设定 + 金手指类型
    - 参考反套路库（如果有）
    - 生成 2-3 套差异化方案
    - 每套包含 3-5 条约束
    - 附带五维自评分

    降级模式（无 AI API 时）：返回一套通用模板包。
    """
    # 实际 AI 调用实现
    # 如果 AI API 不可用，返回降级模板
    return [self._fallback_package()]

def _fallback_package(self) -> dict:
    """无 AI 时的降级模板。"""
    return {
        "id": "pkg_fallback",
        "name": "通用约束包",
        "description": "基础创作约束，适用于大多数题材",
        "constraints": [
            {"type": "anti_trope", "content": "避免开局即无敌"},
            {"type": "must_have", "content": "每卷必须有明确的阶段性目标"},
            {"type": "rhythm", "content": "每 5 章至少一个小高潮"},
        ],
        "score": {"novelty": 5, "feasibility": 9, "reader_hook": 6, "consistency": 8, "differentiation": 4},
    }
```

### validate_input（Step 5）

```python
# 用户提交选择
async def validate_input(self, step: StepState, data: dict) -> str | None:
    if step.step_id == "step_5":
        selected_id = data.get("selected_package_id")
        if not selected_id:
            return "请选择一套创意约束包"
        # 将选择存入 context
        return None
    ...
```

## TDD 验收

- Happy path：context 包含完整前 4 步数据 → execute_step 返回 2-3 个 packages → 每个 package 有 id/name/constraints/score
- Edge case 1：AI API 不可用 → 返回 fallback_package → 流程不阻断
- Edge case 2：validate_input 收到 selected_package_id → 返回 None
- Error case：validate_input 未收到 selected_package_id → 返回错误信息
