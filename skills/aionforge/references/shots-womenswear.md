# 女装图型清单与多角度防疲劳规则

`pdp` 默认按此顺序规划主图與详情图。用户指定图型时，用 `id` 对齐 `plan.json` 的 `name` 前缀。全部用 `forge generate`。

## 主图序列（默认 `1:1`，G1–G5 高转化骨架）

| id | 槽位 | 名称 | Prompt 模板 | 目标与构图规则 |
| --- | --- | --- | --- | --- |
| `main-hero` | G1 | 正面首图（视觉锚） | 有模特用 `tryon.md`；无模特用 `ghost-mannequin.md` | 服装全身/主体居中占 `75–85%`，留白 `≥ 20%`，背景干净；**有模特时本张作为后续镜头的 `source` 锚点图** |
| `main-selling-point` | G2 | 核心卖点图 | `infographic.md`（放大镜气泡 / 胶囊标签 / 标注线） | 服装占 `45–55%`，留白 `≥ 45%`，展示 2–3 个核心卖点短签，严禁遮挡领口与印花 |
| `main-three-quarter` | G3 | 45° 侧身廓形 | `vary.md`（以 `main-hero` 为 `source`）或 `tryon.md` | 45° 四分之三侧面，突出腰线、袖笼与衣摆垂坠 |
| `main-back` | G3/G4 | 背面结构 | 有 `garment_back` 时传背面成衣参考 | 肩线、后领、后背剪裁与下摆完整；无背面图且有模特时可改用 `main-detail` |
| `main-detail` | G4 | 细节微距证据 | 自写微距构图或 `infographic.md` | 领口 / 袖口 / 刺绣 / 印花微距，侧光打织纹，特写占 `60%` 以上 |
| `main-ghost` / `main-flat` | G5 | 3D 隐形人台 / 平铺收口 | `ghost-mannequin.md` 或平铺构图 | 净版展示整件衣服立体版型或平整全貌，建立标准品相预期 |

默认 5 张主图顺序：`main-hero` → `main-selling-point` → `main-three-quarter`（或 `main-back`）→ `main-detail` → `main-ghost`（或 `main-flat`）。Amazon 首图（`main-hero`）强制纯白底 `#FFFFFF` 且 100% 无文字无徽章。

## 详情页序列（默认 `3:4`，纯摄影 + 信息图 + 拼图组合）

**详情页 ≠ 单纯换角度拍同一种照片。** 详情页必须把「多角度实拍」与「电商卖点信息图（`infographic.md`）」穿插排布：

| id | 名称 | Prompt 模板 | 目标与构图规则 |
| --- | --- | --- | --- |
| `detail-infographic` | 核心卖点信息图 | `infographic.md`（按卖点选：①放大镜气泡 / ②图标列表 / ③杂志标注线 / ④60:40非对称分屏） | 首屏承接，留白 `≥ 45%`，用平台排版美学（`typography.md`）直观拆解 3 大卖点 |
| `detail-fabric` | 面料质感微距 | 自写微距或 `infographic.md` | 微距特写，侧光凸显针织/真丝/精梳棉纹理；有 `garment_back` 时可用背面纹理 |
| `detail-craft` | 工艺细节特写 | 自写构图或 `infographic.md`（放大镜气泡） | 走线、纽扣、拉链、荷叶边、领口包边特写 |
| `detail-print` | 图案印花特写 | 自写构图（无印花则跳过） | 印花完整出现一次，文字与色彩 100% 还原 |
| `detail-silhouette` | 版型垂坠与包容度 | `vary.md` 或 `tryon.md` | 全身或七分，展示动态走姿或微侧廓形，衣摆自然 |
| `detail-three-angle` | 三角度 360° 拼图 | `infographic.md`（三角度拼图骨架） | 左/中/右三等宽竖栏同框展示「正面 / 侧面 / 背面」，细白线分隔（单张成衣输入时极佳补充） |
| `detail-scene` | 场景穿搭展示 | `vary.md`（以 `main-hero` 为 `source`） | 场景来自 `facts.target_scenes`，展现真实穿搭代入感 |
| `detail-multi-scene` | 一衣多穿多场景分屏 | `infographic.md`（多场景分屏骨架） | 双栏或三栏对比不同场景穿搭（严禁写死固定场景，必须取自 `facts.target_scenes`） |

默认 6 张详情顺序：
- **有印花款**：`detail-infographic` → `detail-fabric` → `detail-print` → `detail-craft` → `detail-silhouette` → `detail-scene`（或 `detail-multi-scene`）
- **无印花款**：跳过 `detail-print`，补 `detail-three-angle`（三角度 360° 拼图）或 `detail-multi-scene`

## 多角度、景别与背景节奏防疲劳规则

1. **禁止连续 3 张相同角度**：AI 默认倾向生成正面或微侧 3/4 角。主图序列（5 张）必须包含 **≥ 3 种角度**（其中至少 1 张特写/微距）；详情序列（6+ 张）必须包含 **≥ 4 种角度**（其中至少 2 张特写/微距）。
2. **全景全身占比 ≤ 50%**：整套图中全身全景镜头不得超过一半，必须穿插七分景、半身景、局部特写与面料微距。
3. **详情页双背景色交替**：连续详情图在 `styles.json` 的主背景色 `palette.background` 与副背景色 `palette.background_alt` 之间交替使用，消除买家纵向滑动时的视觉疲劳。
