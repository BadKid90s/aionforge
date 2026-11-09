# 女装图型清单

`pdp` 按下面规则写 `plan.json`。图型是菜单，不是固定槽位。用户指定图型时，用 `id` 做 `name` 前缀。全部用 `forge generate`。

做法对齐可组合套图：先覆盖买家问题，再从图型池里选，张数和顺序可改。参考 [wzj177/ecommerce-image-suite](https://github.com/wzj177/ecommerce-image-suite) 的 `--types` 菜单、[motiful/product-shots](https://github.com/motiful/product-shots) 的多角度池。

## 写计划优先级

目标张数：用户点名 > 主图默认 5、详情默认 6（用户说只要主图则详情为 0）。比例：主图按 `platforms.md`（国内默认 `1:1`），详情默认 `3:4`。模特镜头的场景/风格/机位用 `catalog/looks.json` 的套餐（默认 `studio`）。

1. **先映射参考图**：每一张单屏主图 / lookbook / 详情分屏，记下图型（上身、侧身、卖点信息、人台、微距、分屏…）、景别和动作，映射到下方菜单的 `id`，模特镜头再对 `looks.json` 里最接近的 shot。衣服用自家成衣，不抄参考图款式。
2. **不够再补**：已映射张数少于目标时，先补还没回答的买家问题（见「组装」），模特镜头按 `looks.json` 的 `studio`（或用户点名的 walk / lifestyle / detail）顺序补未占用的 shot。
3. **选锚点**：已排好的模特镜头里，选一张正面露脸的半身或七分做 `main-hero`（`tryon.md`），其余模特图用 `aionforge-vary` 从 hero 派生。
4. **卖点图 / 人台**：参考里有、或用户点名、或组装时还缺「卖点 / 净版」才加入。不要为了凑旧的 G1–G5 去替换已经映射的姿势槽。

## 图型菜单

需要某张时从表里选 `id` 和 Prompt 模板。同一套里同一 `id` 最多一次，除非用户点名要两张。

### 主图（默认 `1:1`）

| id | 买家问题 | Prompt 模板 | 构图要点 |
| --- | --- | --- | --- |
| `main-hero` | 这件衣服穿上是什么样 | 有模特用 `tryon.md`；无模特用 `ghost-mannequin.md` | 主体 75–85%，留白 ≥20%；有模特时本张作为后续 `source` |
| `main-three-quarter` | 侧面廓形、袖笼、衣摆 | `vary.md` | 45°，看见印花侧透视 |
| `main-back` | 后背、后领、衣长 | `vary.md`；有背面成衣则 `--ref garment_back=` | 90° 正侧或 110°–135° 侧背，不要 180° 正背面 |
| `main-detail` | 面料、领口、走线、五金 | 微距构图或 `infographic.md` | 特写占 ≥60%，侧光打肌理 |
| `main-selling-point` | 2–3 个核心卖点 | `infographic.md` | 服装 45–55%，留白 ≥45%，文字在留白区 |
| `main-ghost` / `main-flat` | 不靠模特看版型 | `ghost-mannequin.md` 或平铺 | 立体人台或平整全貌 |
| `main-scene` | 穿去哪儿 | `vary.md` | 场景来自 `facts.target_scenes` |

Amazon 首图（若用 `main-hero`）纯白 `#FFFFFF`、无字无徽章，见 `platforms.md`。

### 详情（默认 `3:4`）

详情回答主图没讲完的问题：版型、一衣多穿、做工、多角度。不要用整屏印花微距充数。

| id | 买家问题 | Prompt 模板 | 构图要点 |
| --- | --- | --- | --- |
| `detail-infographic` | 三个卖点一眼看懂 | `infographic.md`（按卖点选板式） | 留白 ≥45%，板式见 `aionforge-pdp` |
| `detail-multi-scene` | 一衣多穿 | `infographic.md` 多场景分屏 | 场景取自 `facts.target_scenes` |
| `detail-benefit` | 穿着利益（显瘦、亲肤、百搭） | `infographic.md` 的 `icon-list` | 左衣右签 |
| `detail-craft` | 领、袖、下摆、车线 | `infographic.md` 标注线或放大镜 | 对着 `selling_points[].visual_keywords` |
| `detail-three-angle` | 正 / 侧 / 背同框 | `infographic.md` 三角度骨架 | 背面栏不扭头露正脸；后背按 `garment_back` |
| `detail-ghost` | 净版立体 | `ghost-mannequin.md` | 无真人四肢 |
| `detail-scene` | 生活场景收尾 | `vary.md` | 全身或七分，场景来自 `target_scenes` |

信息图板式（放大镜 / 图标列表 / 标注线 / 60:40 分屏）在真正选了信息图时再按 `aionforge-pdp` 挑，不要每套详情都六种板式出一遍。

## 组装

用户点名图型或张数 → 照做。

有参考图 → 先映射，再按目标张数补缺口。

无参考、用户只要「一套主图 / 详情」→ 用目标张数，从菜单组一套，**每张只回答一个还没回答的买家问题**。建议（可增删、可换序）：

- **主图**：先保证上身多样性（hero + 不同姿势/角度）。有背面成衣或后背设计再加 `main-back`。`conversion_driver` 为 `craft` 时加一张 `main-detail` 或 `main-ghost`；为 `pain_point` 时加一张 `main-selling-point`。其余用姿势库上身镜头填满。
- **详情**：从详情菜单抽不同 `id`，优先补主图没覆盖的问题。`visual` 偏多场景 / 三角度 / 场景；`pain_point` 偏利益点 / 信息图；`craft` 偏做工 / 人台。不要六张都是信息图，也不要六张都是同一姿势换角度。

`plan.json` 每张写 `name`（`id` 或 `id-pose`）、`ratio`、一句话目标（点明本张回答哪个买家问题）。

## 多角度与节奏

1. 不要连续 3 张同一角度。补齐的镜头至少换角度或换姿势；已映射的参考保持原样。
2. 展示后背用 90° 或 110°–135° 侧背，不要 180° 死板正背面。
3. 详情背景在 `typography.json` 对应平台的 `palette.background` 与 `background_alt` 之间交替。
4. 从姿势库补的全身全景不超过该组一半；参考图是全身的保持全身。
