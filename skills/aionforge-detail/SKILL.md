---
name: aionforge-detail
description: >
  女装详情图与卖点信息图：基于已通过的 bg_white 成衣和 main 模特成片，生成放大镜气泡、图标列表、标注线、60:40 分屏、三角度、多场景、3D 隐形人台等详情图。
  用户说详情图、详情页、卖点信息图、卖点放大、面料微距、一衣多穿、三角度、隐形人台时使用。
  Use when the user runs /aionforge-detail.
---

# 详情图与卖点信息图（detail）

用户点名才生成。详情回答主图没讲完的问题：版型、做工、面料、一衣多穿、多角度。不要用整屏印花微距充数，也不要每套详情都把四种信息图板式出一遍。

未加载入口时先读 `../aionforge/SKILL.md`。`forge` = `uv run --project <入口目录>/scripts forge`，入口目录是本 SKILL.md 同级的 `../aionforge`。Prompt 模板：`../aionforge/references/prompts/infographic.md`、`../aionforge/references/prompts/ghost-mannequin.md`、`../aionforge/references/prompts/vary.md`。图型菜单：`../aionforge/references/shots-womenswear.md`。平台排版：`../aionforge/references/typography.md` + `../aionforge/references/catalog/typography.json`。标准流程按入口 Skill。

## 输入

| 素材 | 角色 | 必填 |
| --- | --- | --- |
| 各颜色 `bg_white` 成衣 | `garment` | 是 |
| 已通过的 main 锚点 / 模特成片 | `source` | 否；详情里出现模特时强烈建议 |
| 卖点、目标场景、平台 | `facts.json` | 是 |
| 详情图型 | 计划 | 否；按卖点推荐 |

详情图里的模特镜头优先用 main 的锚点成片当 `--ref source=`，这样详情和主图是同一个人、同一件衣服。没有 main 时，用 `bg_white` + 隐形人台，或先走 `aionforge-main`。

## 输出

- `output/<logo>/detail/<product>-<color>-<detail-id>.png`
- 单色商品可省略 color：`<product>-<detail-id>.png`
- 默认比例 `3:4`；用户点名平台时按 `../aionforge/references/platforms.md`。
- 同名重跑时旧图自动进 `<product_dir>/history/`。

## 步骤

1. `forge doctor --json`。
2. 复用已有商品工作区。没有 `bg_white` 时先走 `aionforge-white`；要出带模特的详情但还没有 main 锚点时，先走 `aionforge-main` 或改用隐形人台。
3. 看 `facts.json` 的 `selling_points`、`target_scenes`、`style_lock`、`conversion_driver`，按 `../aionforge/references/shots-womenswear.md` 的详情菜单选图型。用户点名图型 / 张数时照做；没点名时每张只回答一个还没回答的买家问题。
4. 按卖点特征选信息图板式：
   - 面料、刺绣、蕾丝、领袖局部工艺 → `magnifier` 放大镜气泡。
   - 防晒、透气、弹力、高支棉参数 → `icon-list` 图标列表。
   - 连衣裙剪裁、法式领口、高腰线、荷叶边 → `annotation` 标注线。
   - 同屏兼顾全身廓形与两处微距 → `asymmetric` 60:40 分屏。
5. 按平台锁定 `style_lock` 与字体：从 `../aionforge/references/catalog/typography.json` 抄 6 位 Hex 和 `prompt` 片段，整套图最多 2 种字体。连续详情可在 `background` 与 `background_alt` 之间交替。
6. 写 Prompt 到 `<product_dir>/prompts/detail/<product>-<color>-<detail-id>.txt`：
   - 纯产品图：`--ref garment=<bg_white>`。
   - 带模特：再加 `--ref source=<main/<product>-<color>-hero.png>`。
   - 三角度 / 背面：有背面成衣时用 `--ref garment_back=`，没有就按同色素面处理。
   - 有文字时写 `VISIBLE_TEXT_BLOCK`，文案用 `「...」` 包裹，并写清字体、字重、Hex、位置和字数上限。
7. 出图并做两层校验：
   ```bash
   forge prompt check --file <product_dir>/prompts/detail/<product>-<color>-<detail-id>.txt \
     --facts <product_dir>/facts.json --visible-text --json
   forge generate --product-dir <product_dir> --bucket detail \
     --prompt-file <product_dir>/prompts/detail/<product>-<color>-<detail-id>.txt \
     --ref garment=<output/<logo>/bg_white/<product>-<color>.png> \
     --ref source=<可选：main 锚点> \
     --name <product>-<color>-<detail-id> --ratio 3:4 --json
   forge verify --image <output/<logo>/detail/<product>-<color>-<detail-id>.png> \
     --ratio 3:4 --json
   ```
8. **看图质检**（必须看）：
   - 衣服 100% 是 bg_white 那一件：颜色、领口、袖口、下摆、印花；有模特时五官与 main 锚点同一人。
   - 信息图板式成立，留白 ≥45%，文字在留白区，没有压住人脸、领口、袖口、下摆或印花。
   - 放大 200% 检查汉字笔画完整、无乱码、无黑边描边、没有把字号 / 色号 / 排版元指令画进画面。
   - 三角度图的背面栏不扭头露正脸；后背按 `garment_back` 或同色素面，不把胸前印花画到后背。
   - 一衣多穿的每个分屏都是同一件衣服、同一个人。
9. 失败时改 Prompt 点名出错部位或精简文案，同一个 `--name` 重跑一次。
10. 交付 `detail/` 文件列表；说明每张回答了哪个买家问题、用了哪张 main 成片当 source。
