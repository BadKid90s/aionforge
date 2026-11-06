# 女装图型清单与多角度防疲劳规则

`pdp` 默认按此顺序规划主图与详情图。用户指定图型时，用 `id` 对齐 `plan.json` 的 `name` 前缀。全部用 `forge generate`。

## 主图序列（默认 `1:1`，G1–G5 高转化骨架）

| id | 槽位 | 名称 | Prompt 模板 | 目标与构图规则 |
| --- | --- | --- | --- | --- |
| `main-hero` | G1 | 正面首图（视觉锚） | 有模特用 `tryon.md`；无模特用 `ghost-mannequin.md` | 服装全身/主体居中占 `75–85%`，留白 `≥ 20%`，背景干净；**有模特时本张作为后续镜头的 `source` 锚点图** |
| `main-selling-point` | G2 | 核心卖点图 | `infographic.md`（放大镜气泡 / 胶囊标签 / 标注线） | 服装占 `45–55%`，留白 `≥ 45%`，展示 2–3 个核心卖点短签，严禁遮挡领口与印花 |
| `main-three-quarter` | G3 | 45° 侧身廓形 | `vary.md`（以 `main-hero` 为 `source`）或 `tryon.md` | 45° 四分之三侧面，突出腰线、袖笼与衣摆垂坠 |
| `main-back` | G3/G4 | 侧面 / 侧背结构 | 传 `--ref garment_back=<背面成衣> --ref source=<main-hero>` | **采用 90° 侧面或 110°–135° 侧背角度，不要 180° 完全背面**；兼顾展示侧面袖笼、后领、后背垂坠与自然侧脸轮廓 |
| `main-detail` | G4 | 领袖/面料微距证据 | 自写微距构图或 `infographic.md` | 领口 / 袖口 / 走线 / 面料织纹微距，侧光打肌理，特写占 `60%` 以上 |
| `main-ghost` / `main-flat` | G5 | 3D 隐形人台 / 平铺收口 | `ghost-mannequin.md` 或平铺构图 | 净版展示整件衣服立体版型或平整全貌，建立标准品相预期 |

默认 5 张主图顺序：`main-hero` → `main-selling-point` → `main-three-quarter` → `main-back`（侧面/侧背）或 `main-detail` → `main-ghost`（或 `main-flat`）。Amazon 首图（`main-hero`）强制纯白底 `#FFFFFF` 且 100% 无文字无徽章。

## 详情页序列（默认 `3:4`，纯摄影 + 信息图 + 拼图组合，不单独做图案印花大特写）

**详情页 ≠ 单纯换角度拍同一种照片，也不要单独拿一张整屏放大图案印花特写充数。** 详情页必须把「多角度上身穿搭」、「版型/功能卖点信息图（`infographic.md`）」与「领袖做工/面料垂感」穿插排布：

| id | 名称 | Prompt 模板 | 目标与构图规则 |
| --- | --- | --- | --- |
| `detail-infographic` | 核心卖点信息图 | `infographic.md`（按卖点选：①放大镜气泡 / ②图标列表 / ③杂志标注线 / ④60:40非对称分屏） | 首屏承接，留白 `≥ 45%`，用平台排版美学（`typography.md`）直观拆解 3 大卖点 |
| `detail-multi-scene` | 一衣多穿多场景分屏 | `infographic.md`（多场景分屏骨架） | 双栏或三栏对比不同场景穿搭（严禁写死固定场景，必须取自 `facts.target_scenes`） |
| `detail-benefit` | 实穿利益点列表图 | `infographic.md`（板式 ② 左衣/上身右签 `icon-list`） | 左侧展示模特半身/七分松弛感穿搭，右侧纵向排列 3 个极简图标 + 莫兰迪胶囊标签（透气亲肤、遮肉显瘦、高腰百搭） |
| `detail-craft` | 领袖下摆做工拆解图 | `infographic.md`（板式 ③ 杂志标注线或 ① 放大镜气泡） | 聚焦领口罗纹、肩袖剪裁、下摆双针走线与面料垂坠，不做单纯图案放大特写 |
| `detail-three-angle` | 三角度同框拼图 | `infographic.md`（三角度拼图骨架） | 左/中/右三等宽竖栏同框展示「正面 / 微侧（45°） / 背面」，细白线分隔（背面栏只展示后脑长发与纯白后背，严禁扭头露正脸） |
| `detail-ghost` / `detail-scene` | 3D 隐形人台 / 场景氛围 | `ghost-mannequin.md` 或 `vary.md` | 净版 3D 立体陈列或户外生活感全身/半身抓拍收尾 |

默认 6 张详情顺序：`detail-infographic` → `detail-multi-scene` → `detail-benefit` → `detail-craft` → `detail-three-angle` → `detail-ghost`（或 `detail-scene`）。

## 多角度、景别与背景节奏防疲劳规则

1. **禁止连续 3 张相同角度**：AI 默认倾向生成正面或微侧 3/4 角。主图序列（5 张）必须包含 **≥ 3 种角度**（其中至少 1 张特写/微距）；详情序列（6+ 张）必须包含 **≥ 4 种角度**。
2. **不要 180° 完全背面**：展示侧面或后背版型时，一律采用 **90° 正侧面或 110°–135° 侧背角度**（自然露出侧颜轮廓与肩袖侧面线条），避免死板的 180° 完全正背面或扭头畸变。
3. **详情页不单独出图案印花大特写**：详情页聚焦版型包容度、一衣多搭、面料透气亲肤与领袖车线做工，不要用单张图案印花微距占满一屏。
4. **全景全身占比 ≤ 50%**：整套图中全身全景镜头不得超过一半，必须穿插七分景、半身景、分屏拼图与工艺标注图。
5. **详情页双背景色交替**：连续详情图在 `styles.json` 的主背景色 `palette.background` 与副背景色 `palette.background_alt` 之间交替使用，消除买家纵向滑动时的视觉疲劳。
