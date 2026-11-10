# 定义目录

**加新展示图只改 `looks.json`，加平台排版只改 `typography.json`，不要改 Python。**

| 文件 | 定义什么 | Schema |
| --- | --- | --- |
| `looks.json` | 女装展示套餐。每条 shot 按万象公式把场景、风格、镜头、动作写在同一段 `prompt` | `schemas/looks.schema.json` |
| `typography.json` | 6 大平台字体、胶囊标签与配色 | `schemas/typography.schema.json` |

`id` 用 kebab-case（`typography.json` 允许 `douyin_xhs`），同一文件内不重复。

## 加一条展示图

在 `looks.json` 对应 pack 的 `shots` 追加一条，`prompt` 必须含【场景】【风格】【镜头语言】【主体动作】。出图整段粘贴。

用户说自拍 / 对镜用 `mirror`，户外 / 街拍 / 草坪用 `outdoor`，咖啡 / 吧台 / 居家用 `cafe`，半身人像 / 扶发 / 抱臂用 `portrait`，车内用 `car`，平铺 / 挂拍 / 净版用 `flat`，走 / 动态用 `walk`，窗光 / 室内用 `lifestyle`，特写 / 面料用 `detail`，其余用 `studio`。

加完后：

```bash
uv run pytest -q tests/test_catalog.py
```
