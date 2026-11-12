---
name: aionforge-print
description: >
  阶段 1 印花准备流程：按「思考 → 事实锁定 → 生成 → 检查」四步闭环，从印花图案中提取透明底图案，
  客观体检并分析哪些适合印在 T 恤正面、哪些适合印在背面；背面主印花自动提取核心元素作为左胸小印花，
  产出可执行的正反面印花位置计划。
  用户说印花提取、分析哪些适合正面哪些适合背面、背面加左胸小印花、提取印花核心元素时使用。
  Use when the user runs /aionforge-print.
---

# 阶段 1：印花提取、正反面分析与左胸核心元素（print）

本流程负责把原始印花图案转化为**干净透明底主印花**、**背面配套的左胸核心小图标**，以及经用户确认的**正反面位置计划（`facts.print.placements`）**。
关于 T 恤实拍底色冲突调整与成衣合成，交由下一阶段 `aionforge-product` 按具体 T 恤颜色执行。

未加载入口时先读 `../aionforge/SKILL.md`。工具只按名称引用，参数见工具卡；本文件不写命令。

## 输入与输出

| 方向 | 内容 | 说明 |
| --- | --- | --- |
| **输入** | 一张或多张印花稿（`print`）、用户正反面或位置偏好（可选） | 平面白底稿、透明稿或实拍印花均可 |
| **输出文件** | `refs/<product>-print.png`、`refs/<product>-core.png`（背面主印花必配） | 均为 RGBA 透明底 PNG |
| **输出事实** | `facts.print` 中的 `source` / `palette` / `elements` / `analysis` / `placements` | 字段规范见 [contracts/facts.md](../aionforge/references/contracts/facts.md) |

---

## 四步闭环执行流程

### 第一步：思考（Think —— 清点、测量与正反面/核心元素分析）

1. **客观指标测量**：对输入的印花稿调用 [print metrics](../aionforge/references/tools/print-metrics.md)，获取尺寸、宽高比、主色调色板、边缘细节密度、平均笔画粗细与透明孔洞数。
2. **正反面适用性分析**（完整标准位置与评分规范见 [print/placement.md](../aionforge/references/print/placement.md)）：
   - **适合 T 恤正面胸前正中（`chest_center`）**：单一视觉焦点、构图紧凑、细节密度低、色数少（≤3 色）、笔画粗，固定采用成人 `28–32cm` 标准（距领口下 7–9cm）缩印后文字与结构依然清晰。
   - **适合 T 恤背面大幅展示（`back_center`）**：多元素插画、涂鸦、泼墨/渐变、细节密度高、色数多、包含大量依赖大面积阅读的小字或纵向大构图，固定采用成人 `28–32cm × 35cm` 标准（距后领线下 2–5cm）。
3. **背面主印花的左胸小印花思考**（规则见 [print/element.md](../aionforge/references/print/element.md)）：
   - **硬规则**：凡判定为**背面主印花**，正面左胸（`left_chest`）必须配套一枚**核心元素小印花（徽章）**，固定采用 `8–12cm` 标准落在正面平铺图右侧（穿着者左胸，距左肩缝 5.5–8cm、中线 4–6cm），绝不能把整张复杂背面大图直接缩小贴在左胸。
   - 从主印花中挑选 **1 个轮廓闭合、语义独立、不与长串文字粘连的核心图标**（如靶心、动物头像、标志性符号、花朵主体），构思 10–25 字的语义提取描述（只写图形名词与特征，不写坐标）。
   - 若整张印花是纯文字或无法拆出独立图标，必须向用户提出三选一：跳过左胸小标 / 换稿 / 仅提取简短主字标。

### 第二步：事实锁定（Lock —— 写入分析草案并确认门槛）

1. 初始化或打开商品工作区（[product init](../aionforge/references/tools/product-init.md)）。
2. 将分析结论整理成清晰表格呈现给用户确认：
   - 每张印花的**正面 / 背面建议**、评分理由、固定 `region`（`chest_center` / `back_center`）及对应行业标准尺寸（无需再手猜坐标比例）。
   - 背面主印花对应的**左胸核心小图标选型**（提取哪个元素，固定 `region: "left_chest"`）。
   - 提醒用户：背面主印花在下一阶段合成时，需要提供对应颜色的**背面 T 恤实拍图**。
3. **确认门槛**：用户确认正反面方案与左胸图标选型后，将 `analysis` 与 `placements` 锁定写入 `facts.json`。**用户确认前严禁进入下一阶段合成。**

### 第三步：生成（Generate —— 提取透明主印花与左胸核心图标）

1. **提取透明主印花**：
   - 调用 [cutout](../aionforge/references/tools/cutout.md)（复杂白边或残留底色可启用 AI 清洗模式，内部有镂空孔洞或纯白字标时走纯本地模式，详见 [prompts/extract.md](../aionforge/references/prompts/extract.md)），输出 `refs/<product>-print.png`。
2. **提取左胸核心小图标（当主印花在背面时）**：
   - 调用 [extract-core-element](../aionforge/references/tools/extract-core-element.md)，传入主印花与第一步构思的核心元素语义描述，输出透明底图标 `refs/<product>-core.png`。
   - 对提取出的左胸小图标跑一次 [print metrics](../aionforge/references/tools/print-metrics.md) 确认色数与笔画粗细。

### 第四步：检查（Verify —— 透明通道与图标完整性检验）

1. **客观校验**：对 `refs/<product>-print.png` 和 `refs/<product>-core.png` 分别调用 [verify](../aionforge/references/tools/verify.md) 的印花检查模式。
   - 必须带有效透明通道（RGBA）。
   - 边缘白边比例达标、无小于 4px 的孤立噪点碎块。
   - 左胸核心图标必须满足 `complete: true` 且四周留白比例 `margin_ratio ≥ 0.02`。
2. **视觉核对**：
   - 主印花文字逐字完整、无重绘变形、无镜像、无素材站水印。
   - 左胸小图标独立干净，没有混入多余杂字或被裁断边缘。
3. **回写交接**：检查全部通过后，更新 `facts.print.source`、`facts.print.elements` 和 `facts.print.placements`，交接给 `aionforge-product` 进行 T 恤实拍撞色适配与合成。

---

## 失败路由

| 现象 | 处置 |
| --- | --- |
| 主印花抠图后有白边或噪点 | 调整容差或开启去噪重跑 [cutout](../aionforge/references/tools/cutout.md) |
| 白色字标或字母内孔被误删 | 关闭封闭白区清理，改用纯本地抠图重跑 |
| 核心图标 `complete: false` 或带入杂字 | 修改语义描述（明确点名图形、强调不要文字）重跑一次 [extract-core-element](../aionforge/references/tools/extract-core-element.md)；仍失败则请用户指定 |
| 原稿带素材站水印 | 停止出成品，提示用户更换无水印源文件 |
