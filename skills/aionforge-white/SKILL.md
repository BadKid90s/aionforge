---
name: aionforge-white
description: >
  女装白底商品图：把 logo 图案合成到每个颜色的白底空白成衣上，按颜色输出可上架的 bg_white 成片。
  用户说这个 logo / 图案合成白底、每个颜色出一张白底图、提取印花、印花合成、白底衣图时使用。
  Use when the user runs /aionforge-white.
---

# 白底商品图（bg_white）

把平面 logo 图案合成到每个颜色的白底空白成衣上，按颜色各出一张可上架的成衣图。logo 通常是白底或透明底的平面设计稿：先用 `forge cutout` 在本地去背景、裁到图案主体，再合成。只有拿到的是成衣实拍、没有平面稿时，才先从衣服上提取印花。

未加载入口时先读 `../aionforge/SKILL.md`。`forge` = `uv run --project <入口目录>/scripts forge`，入口目录是本 SKILL.md 同级的 `../aionforge`。Prompt 模板：`../aionforge/references/prompts/extract.md`、`../aionforge/references/prompts/compose.md`、`../aionforge/references/prompts/ghost-mannequin.md`。标准流程按入口 Skill。

## 输入

| 素材 | 角色 | 必填 |
| --- | --- | --- |
| 平面 logo 图案（白底 / 透明底 JPG / PNG） | `print` | 是；没有平面稿时才从成衣实拍提取 |
| 各颜色空白成衣（白底 / 平铺 / 挂拍） | `garment` | 是 |
| 图案位置与大约宽度 | 补充说明 | 否，默认胸前正中、宽约衣宽 30% |
| 颜色列表 | `facts.colors` | 否，默认用户给几张空白成衣就出几个颜色 |

## 输出

- 成品：`output/<logo>/bg_white/<product>-<color>.png`，例如 `output/锁定目标/bg_white/short-black.png`
- 图案中间产物：`<product_dir>/refs/<product>-print.png`
- 白底清理中间产物：`<product_dir>/tmp/<product>-<color>-clean.png`
- 同名重跑时旧图自动进 `<product_dir>/history/`

## 步骤

1. `forge doctor --json`。失败则停。
2. 从素材推断 logo / product，再
   `forge workspace init --logo <logo> --json`、
   `forge product init --logo <logo> --product <product> --json`。
   - logo = 图案名，看图案主标题（如「锁定目标」「LAZY DAY」「CHILL OUT」）；素材站水印不是 logo 名。
   - product = 款式，从空白成衣文件夹推断（`short` / `long` / `tee` / `hoodie`）。
   - 一次只处理一个 logo；用户一次给多张图案稿时，先问这一轮出哪个。
   - 多个候选或看不出时问用户。
3. 看每张空白成衣图，按 `../aionforge/references/facts.md` 写 `facts.json`：
   - 品类、版型、领口、袖型 / 袖口、下摆、衣长、腰臀剪裁、门襟、口袋。
   - 每个颜色一条 `colors[]`：`name`（`black` / `白` / `浅灰` 等）、`hex`、`source`（该色空白成衣图路径）。
   - 图案 `has_print`、`placement`、`text_exact`（逐字）、`technique`。
   - 看不清的写入 `uncertain`。
   写完把关键事实列给用户核对，确认前禁止出图。
4. **准备 logo 图案**。有平面图案稿时直接本地抠图，不经过图片模型，避免文字和形状被重画：
   ```bash
   forge cutout --input <logo 图案稿> --product-dir <product_dir> \
     --name <product>-print --json
   forge verify --image <product_dir>/refs/<product>-print.png --alpha --json
   ```
   本地抠图会按四边背景色自适应去底，米白 / 浅灰底也能处理，并裁到图案主体。图案稿带素材站水印时，提示用户换有授权的无水印源文件，不要把带水印的预览图直接出成品。图案稿自带黑色边框、底色块时，先确认它是不是设计的一部分；本地抠图只去背景色，不会去掉设计内部的边框，切不掉就换干净源文件。
   只有成衣实拍、没有平面稿时，才用 `extract.md` 走模型提取：
   ```bash
   forge generate --product-dir <product_dir> --store refs \
     --prompt-file <product_dir>/prompts/refs/<product>-print.txt \
     --ref <成衣图> --name <product>-print --cutout --json
   ```
   多块印花时问用户要哪块；用户说「都要」则每块一个 name。
5. **按颜色准备白底衣**。空白成衣本身已经是纯白底时直接当 `garment`；不是纯白底（实拍、灰底、带衣架）时，先用 `ghost-mannequin.md` 做一张干净白底：
   ```bash
   forge generate --product-dir <product_dir> --store tmp \
     --prompt-file <product_dir>/prompts/tmp/<product>-<color>-clean.txt \
     --ref garment=<该色空白成衣> \
     --name <product>-<color>-clean --ratio 1:1 --json
   forge verify --image <product_dir>/tmp/<product>-<color>-clean.png \
     --ratio 1:1 --white-bg --json
   ```
   这一步只为合成提供干净衣身，不直接当成品；成品仍要在下一步合成图案后落进 `bg_white`。
6. **逐色合成**。每个颜色单独一份 Prompt，复制 `compose.md`，写清图案位置和大约宽度；有文字时把 `facts.print.text_exact` 逐字写进【主体】：
   ```bash
   forge prompt check --file <product_dir>/prompts/bg_white/<product>-<color>.txt \
     --facts <product_dir>/facts.json --json
   forge generate --product-dir <product_dir> --bucket bg_white \
     --prompt-file <product_dir>/prompts/bg_white/<product>-<color>.txt \
     --ref print=<product_dir>/refs/<product>-print.png \
     --ref garment=<白底衣> \
     --name <product>-<color> --ratio 1:1 --json
   forge verify --image <output/<logo>/bg_white/<product>-<color>.png> \
     --ratio 1:1 --white-bg --json
   ```
   默认所有颜色都出；用户点名只出某一个颜色时，只跑该色。
7. **看图质检**（必须看）：
   - 衣服仍是空白成衣那一件：领口、肩线、袖型、袖口、下摆、衣长未变。
   - 图案只出现一次、未重绘、未镜像，文字逐字一致；图案颜色与 logo 稿一致。
   - 位置符合计划，没有漂到袖子、领口或下摆外。
   - 没有吊牌、领标、衣架或背景杂物残留（用户明确要保留领标时除外）。
   - 背景是无缝纯白 `#FFFFFF`，四边都是白，没有灰底、棋盘格、投影底板。
   - 成品没有素材站水印、预览字、边框或二维码。
   - 袖笼、袖口、下摆、领弧外轮廓平滑抗锯齿；放大看没有阶梯像素边、毛边、碎边或抠图杂边。
8. **回写 facts**：把每色 `bg_white` 路径、`status: "approved"` 写入 `colors[]`；主色成片写入 `canonical.garment`。后续 main / sku / detail 一律用这张白底衣，不再用原始空白成衣图。
9. 失败时改 Prompt 点名出错部位（如「图案只出现一次」「外轮廓平滑抗锯齿，纯白底，不要抠图像素边」），同一个 `--name` 重跑一次。
10. 交付 `bg_white/` 文件列表；用户只要图案文件时，交付 `refs/<product>-print.png` 并停下。
