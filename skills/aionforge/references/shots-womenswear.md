# 女装图型清单

`pdp` 默认按此顺序取前 N 张。用户指定图型时，用 id 对齐 `plan.json` 的 `name` 前缀。全部用 `forge generate`。

## 主图（默认 1:1）

| id | 名称 | Prompt | 目标 |
| --- | --- | --- | --- |
| `main-hero` | 正面主视觉 | 有模特用 tryon 模板 | 服装全身居中，占 80–90%，背景干净 |
| `main-back` | 背面结构 | 有模特用 tryon 模板 | 肩线、后背、下摆完整 |
| `main-three-quarter` | 45° 侧身 | tryon 模板 | 廓形与垂坠 |
| `main-detail` | 细节主图 | 自写构图 | 领口 / 袖口 / 印花微距 |
| `main-flat` | 平铺正视 | 自写构图 | 正面平铺，袖口下摆铺平 |

## 详情（默认 3:4）

| id | 名称 | Prompt | 目标 |
| --- | --- | --- | --- |
| `detail-fabric` | 面料质感 | 自写构图 | 微距，侧光打纹理 |
| `detail-craft` | 工艺细节 | 自写构图 | 走线、纽扣、拉链 |
| `detail-print` | 图案印花 | 自写构图 | 印花完整出现一次 |
| `detail-silhouette` | 版型垂坠 | tryon 模板 | 全身或七分，衣摆自然 |
| `detail-scene` | 场景展示 | tryon 模板 | 场景来自 facts.target_scenes |
| `detail-styling` | 多角度穿搭 | tryon 或自写 | 同一件衣服两种搭配或正侧对比 |

默认详情顺序：fabric → craft → print → silhouette → scene → styling。无印花则跳过 `detail-print`，补一张工艺或版型。
