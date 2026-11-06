# 工作流：女装主图 + 详情（pdp）

日常主力工作流。输入至少一张成衣图（支持正面 + 背面双图）。采用**「两阶段模特锚点锁定」**与**「摄影 + 卖点信息图组合」**，全部走 `forge generate`。

## 默认交付

- 主图 5 张，比例 `1:1`（拼多多 / 淘宝）或按 `references/platforms.md`
- 详情 6 张，比例 `3:4`
- 图型、顺序与防疲劳规则以 `references/shots-womenswear.md` 为准；用户点名张数或图型时听用户

## 核心卖点图（`main-selling-point` / `detail-infographic`）板式智能推荐

写计划时根据 `facts.selling_points` 的特征，从 `references/prompts/infographic.md` 选最契合的板式（不再千篇一律）：

| 商品卖点特征 | 推荐板式 | 视觉结构说明 |
| --- | --- | --- |
| 面料细节、刺绣、蕾丝、领袖局部工艺 | **① 放大镜气泡（`magnifier`）** | 服装居中 + 3 个圆形局部放大镜气泡，细线连向 `visual_keywords` 对应部位 |
| 防晒、透气、弹力、保暖、高支棉参数 | **② 信息图标列表（`icon-list`）** | 左衣（45%）+ 右侧主标题与 3 条极简细线图标 + 胶囊短标签 |
| 连衣裙剪裁、法式领口、高腰线、荷叶边 | **③ 杂志标注线（`annotation`）** | 服装居中 + 1px 极简指示线指向各设计部位并配短标签 |
| 需同屏兼顾上身整体廓形与两处微距做工 | **④ 60:40 非对称分屏（`asymmetric`）** | 左 60% 全身/七分主视觉 + 右 40% 上下两个局部特写格，细线分隔 |

## 两阶段模特锚点锁定机制（关键！）

当任务包含真人模特（提供了 `--ref model=`）且有多张模特出镜图（如 `main-hero`、`main-three-quarter`、`detail-silhouette`、`detail-scene`）时，**严禁一次性盲目并发生成所有模特图**：

1. **阶段一（生成并锁定首张模特锚点图）**：
   - 先用 `--ref garment=<正面成衣> --ref model=<模特>` 跑出第 1 张 `main-hero`（正面全身主图）。
   - 立即看图质检（五官眼神、衣服领口/袖口/下摆/印花是否 100% 正确）。
2. **阶段二（以锚点图派生其余模特镜头）**：
   - `main-hero` 质检通过后，后续所有需要同一模特出镜的正面/侧面/场景图，统一把 `<run_dir>/images/main-hero.png` 作为 `--ref source=`（连同 `--ref garment=`）传入，走 `references/prompts/vary.md` 骨架。
   - 这样整套主图和详情页里的模特面孔、发型、衣服合身度与光线逻辑 100% 锁定同一人同一件衣服。

## 正背面成衣双图路由

- 用户提供了正面 + 背面两张成衣图时（`input_image_type` 为 `flat_lay_front_back` 或 `hanging_front_back`）：
  - 正面/侧面/卖点图传 `--ref garment=<正面成衣>`
  - 背面主图（`main-back`）、后侧裂变（`vary-back-look`）与背面材质微距传 `--ref garment_back=<背面成衣>`（若还需锁模特成片则同时传 `--ref source=<main-hero.png>`）

## 步骤

1. `forge doctor --json`
2. `forge job init --workflow pdp --slug <商品短名> --json`，记下 `run_dir`
3. 看图写 `facts.json` 到 `run_dir`（含 `conversion_driver`、`garment_position`、`input_image_type`、`selling_points[].visual_keywords`）。缺口确认见 `SKILL.md`「生图前确认」
4. 按 `references/style-lock.md` 与 `references/typography.md` 锁定 `style_lock` 与平台排版美学，写入 `facts.json`
5. 按 `references/shots-womenswear.md` 写 `plan.json`（检查角度多样性：无连续 3 张同角度，全身全景 ≤ 50%）：

```json
{
  "tasks": [
    {
      "name": "main-01-hero",
      "prompt": "tryon",
      "ratio": "1:1",
      "goal": "G1 正面主视觉锚点图，服装占画面 80%，留白 ≥20%"
    },
    {
      "name": "main-02-selling-point",
      "prompt": "infographic-magnifier",
      "ratio": "1:1",
      "goal": "G2 核心卖点放大镜气泡图，留白 ≥45%，展示 3 大卖点标签"
    },
    {
      "name": "detail-01-infographic",
      "prompt": "infographic-asymmetric",
      "ratio": "3:4",
      "goal": "详情首屏 60:40 非对称卖点信息图，左主视觉右局部细节"
    }
  ]
}
```

6. 生图前确认缺口；无缺口或用户已确认后进入生成
7. 为每张写 `work/prompts/<name>.txt`（遵循五层结构：Style Lock + 商品事实锁 + 参考图角色 + 本张构图/机位 + 图内文字契约与否定清单）
8. 执行出图：

```bash
# 阶段一：首张模特主图（锚点）
forge generate --job-dir <run_dir> \
  --prompt-file <run_dir>/work/prompts/main-01-hero.txt \
  --ref garment=<正面成衣> --ref model=<模特> \
  --name main-01-hero --ratio 1:1 --json

# 阶段二：基于锚点成片派生侧身/场景模特镜头
forge generate --job-dir <run_dir> \
  --prompt-file <run_dir>/work/prompts/main-03-three-quarter.txt \
  --ref source=<run_dir>/images/main-01-hero.png --ref garment=<正面成衣> \
  --name main-03-three-quarter --ratio 1:1 --json

# 卖点信息图 / 隐形人台 / 微距细节
forge generate --job-dir <run_dir> \
  --prompt-file <run_dir>/work/prompts/detail-01-infographic.txt \
  --ref garment=<正面成衣> --name detail-01-infographic --ratio 3:4 --json
```

9. 逐张看图质检（含文字 200% 笔画核对）；失败只重跑该 `--name`
10. 交付 `images/` 路径列表与 Assumptions

## 素材不齐时的降级策略

- **无模特图**：主图 G1 优先改用 `references/prompts/ghost-mannequin.md`（**3D 立体隐形人台**，自然撑起胸省、腰线与裙摆垂坠）或净版平铺；详情页用売点信息图 + 放大镜气泡 + 面料/工艺微距 + 平铺搭配组合，并告知用户。
- **无白底成衣、只有挂拍或街拍**：仍可 `generate`，Prompt 中写明以该图为衣服唯一标准、忽略原图衣架或杂乱背景，并标 Assumption。
- **有印花且用户要单独印花文件**：先跑 `references/workflows/extract.md`，再继续本流程。
