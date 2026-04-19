# Task 102: Init Step 1-4 表单采集

## 目标

实现 InitSkillHandler 的 Step 1-4 表单校验逻辑，定义每步的必填字段和校验规则。

## 涉及文件

- `webnovel-writer/dashboard/skill_handlers/init_handler.py`（修改）
- `webnovel-writer/dashboard/skill_handlers/init_schemas.py`（新建，表单 schema 定义）

## 依赖

- task-101（InitSkillHandler 骨架已存在）

## 规格

### init_schemas.py — 每步的字段定义

```python
INIT_STEP_SCHEMAS = {
    "step_1": {
        "title": "故事核与商业定位",
        "fields": [
            {"name": "title", "label": "书名", "type": "text", "required": True},
            {"name": "genres", "label": "题材", "type": "multi_select", "required": True,
             "hint": "支持复合题材，至少选一个"},
            {"name": "target_words", "label": "目标字数", "type": "number", "default": 2000000},
            {"name": "target_chapters", "label": "目标章节数", "type": "number", "default": 600},
            {"name": "one_line_story", "label": "一句话故事", "type": "text", "required": True,
             "hint": "用一句话概括你的故事核心"},
            {"name": "core_conflict", "label": "核心冲突", "type": "textarea", "required": True},
            {"name": "target_audience", "label": "目标读者", "type": "text"},
        ],
    },
    "step_2": {
        "title": "角色骨架与关系冲突",
        "fields": [
            {"name": "protagonist_name", "label": "主角姓名", "type": "text", "required": True},
            {"name": "protagonist_desire", "label": "主角欲望", "type": "textarea", "required": True,
             "hint": "主角最想要什么？"},
            {"name": "protagonist_flaw", "label": "主角缺陷", "type": "textarea", "required": True,
             "hint": "主角最大的性格缺陷"},
            {"name": "protagonist_structure", "label": "主角成长结构", "type": "select",
             "options": ["正向成长弧", "堕落弧", "平坦弧", "复杂弧"]},
            {"name": "romance_config", "label": "感情线配置", "type": "select",
             "options": ["无感情线", "单女主", "后宫", "暧昧不明"]},
            {"name": "villain_tiers", "label": "反派分层", "type": "textarea",
             "hint": "小反派→中反派→大反派，每层简述"},
        ],
    },
    "step_3": {
        "title": "金手指与兑现机制",
        "fields": [
            {"name": "golden_finger_type", "label": "金手指类型", "type": "select", "required": True,
             "options": ["系统流", "重生", "传承", "异能", "无金手指", "其他"]},
            {"name": "golden_finger_name", "label": "金手指名称", "type": "text", "required": True},
            {"name": "golden_finger_style", "label": "风格", "type": "select",
             "options": ["科技感", "古典", "神秘", "搞笑", "暗黑"]},
            {"name": "golden_finger_visibility", "label": "可见度", "type": "select",
             "options": ["仅主角可见", "部分人可见", "公开"]},
            {"name": "golden_finger_cost", "label": "不可逆代价", "type": "textarea",
             "hint": "使用金手指的代价是什么？"},
            {"name": "golden_finger_growth", "label": "成长节奏", "type": "select",
             "options": ["线性成长", "阶梯式", "指数爆发", "先抑后扬"]},
        ],
    },
    "step_4": {
        "title": "世界观与力量规则",
        "fields": [
            {"name": "world_scale", "label": "世界规模", "type": "select", "required": True,
             "options": ["单城市", "单大陆", "多大陆", "星际", "多位面"]},
            {"name": "power_system", "label": "力量体系", "type": "textarea", "required": True,
             "hint": "描述修炼/力量等级体系"},
            {"name": "faction_layout", "label": "势力格局", "type": "textarea",
             "hint": "主要势力及其关系"},
            {"name": "social_hierarchy", "label": "社会阶层", "type": "textarea",
             "hint": "社会等级结构"},
        ],
    },
}
```

### validate_input 实现

修改 `init_handler.py` 的 `validate_input()`：

```python
async def validate_input(self, step: StepState, data: dict) -> str | None:
    schema = INIT_STEP_SCHEMAS.get(step.step_id)
    if not schema:
        return None
    for field in schema["fields"]:
        if field.get("required") and not data.get(field["name"]):
            return f"{field['label']}不能为空"
    return None
```

### execute_step 扩展

Step 1-4 是纯 form 步骤，不需要 execute_step。但 execute_step 被调用时（form 步骤提交后），将用户输入存入 context：

```python
# 在 validate_input 通过后，SkillRunner 会自动将 input_data 存入 step_state
# 同时 InitSkillHandler 在 execute_step 中将关键数据合并到 context
async def execute_step(self, step: StepState, context: dict) -> dict:
    if step.step_id in ("step_1", "step_2", "step_3", "step_4"):
        # 将表单数据合并到 context，供后续步骤使用
        context.update(step.input_data or {})
        return {"merged_fields": list((step.input_data or {}).keys())}
    # step_5, step_6 逻辑在 task-103/104 中实现
    ...
```

## TDD 验收

- Happy path：Step 1 提交完整数据 → validate_input 返回 None → context 包含 title/genres 等
- Edge case 1：Step 1 缺少 title → validate_input 返回 "书名不能为空"
- Edge case 2：Step 2 缺少 protagonist_desire → 返回 "主角欲望不能为空"
- Error case：Step 3 golden_finger_type 为空 → 返回 "金手指类型不能为空"
