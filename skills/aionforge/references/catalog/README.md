# 定义目录

姿势、场景、风格都是 JSON。**加新定义只改对应 JSON，不要改 Python。** 字段以 `schemas/` 为准。

| 文件 | 定义什么 | Schema |
| --- | --- | --- |
| `poses.json` | 镜头 `cameras`、身体姿势 `poses`、成片配方 `recipes`、套餐 `packs` | `schemas/poses.schema.json` |
| `scenes.json` | 拍摄场景（棚、窗光、街拍等） | `schemas/scene.schema.json` |
| `styles.json` | 视觉风格 / Campaign Style Lock | `schemas/style.schema.json` |

`id` 全局用 kebab-case，同一文件内不重复。`prompt` / `style_lock` 给图片模型用，中英都可，写成完整句子。

## 怎么加一条

**姿势配方**

1. 若是新镜头：在 `poses.json` → `cameras` 加对象。  
2. 若是新身体动作：在 `poses` 加对象。  
3. 在 `recipes` 用 `camera` + `pose` 组合成片，写整段 `prompt`。  
4. 把配方 `id` 放进某个 `packs.*.recipes`。

**场景**

在 `scenes.json` → `scenes` 追加一条，填 `id` / `name` / `keywords` / `prompt`。裂变默认不换场景；用户要求换场景时按 `keywords` 匹配。

**风格**

在 `styles.json` → `styles` 追加一条。`style_lock` 必须是整段锁定文本，原样贴进每一张 Prompt。

主营 T 恤 / 卫衣 / 长袖、客群青年女性时：套餐用 `packs.tee-hoodie-12`（纯 T 恤用 `tee-8`，纯卫衣用 `hoodie-10`）。场景优先 `campus-quad`、`dorm-desk`、`campus-stairs`。风格默认 `campus-youth`。模特按女大学生/青年女性来写，不要写成儿童。

加完后在 `scripts/` 目录执行：

```
uv run pytest -q tests/test_catalog.py
```
