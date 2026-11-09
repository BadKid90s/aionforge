# 定义目录

姿势、场景、风格、平台排版都是 JSON。**加新定义只改对应 JSON，不要改 Python。** 字段以 `schemas/` 为准。

| 文件 | 定义什么 | Schema |
| --- | --- | --- |
| `poses.json` | 镜头 `cameras`、身体姿势 `poses`、成片配方 `recipes`、套餐 `packs` | `schemas/poses.schema.json` |
| `scenes.json` | 拍摄场景（棚、窗光、街拍等） | `schemas/scene.schema.json` |
| `styles.json` | 视觉风格 / Campaign Style Lock | `schemas/style.schema.json` |
| `typography.json` | 6 大平台字体、胶囊标签与标准配色美学 | `schemas/typography.schema.json` |

`id` 全局用 kebab-case（`typography.json` 允许 snake_case 如 `douyin_xhs`），同一文件内不重复。`prompt` / `style_lock` 给图片模型用，中英都可，写成完整句子。

## 怎么加一条

**姿势配方**

1. 新镜头写入 `poses.json` → `cameras`。  
2. 新身体动作写入 `poses`。  
3. 可选：在 `recipes` 为某一对写整段 `prompt`，出图时优先用。  
出图按 `aionforge-vary` 从入池的 `cameras` × `poses` 随机配对。

**场景**

在 `scenes.json` → `scenes` 追加一条，填 `id` / `name` / `keywords` / `prompt`。裂变默认不换场景；用户要求换场景时按 `keywords` 匹配。

**风格**

在 `styles.json` → `styles` 追加一条。`palette` 必须填 6 位 Hex 色值；`style_lock` 必须是整段锁定文本，原样贴进每一张 Prompt。

**平台字体与排版**

在 `typography.json` → `platforms` 追加一条，填 `id` / `name` / `aesthetic` / `headline_font` / `body_font` / `badge_style` / `palette` / `prompt` / `avoid`。

多机位一律按 `aionforge-vary` 随机配对镜头与姿势。用户点名校园场景时用 `campus-quad` / `dorm-desk` / `campus-stairs`。模特按女大学生/青年女性来写。

加完后在 `scripts/` 目录执行：

```bash
uv run pytest -q tests/test_catalog.py
```
