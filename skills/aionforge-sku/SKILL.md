---
name: aionforge-sku
description: >
  女装 SKU 配色规格图：用一张已通过的 main 主图、模特成片或产品图当母版，把每个颜色的 bg_white 成衣套进同一构图。
  用户说 SKU 裂变、SKU 套图、SKU 母版、电商 SKU、SKU 图、批量规格图、按这张母版出黑 / 藏青 / 浅灰规格图时使用。
  Use when the user runs /aionforge-sku.
---

# SKU 配色规格图

用户点名才生成。用一张已通过的 main 主图、模特成片或产品图当母版，把用户指定的多张配色白底成衣一一套进去，生成同构图的规格图。

母版锁人、姿势、场景、光线；本张配色白底锁衣服颜色、面料、印花。不要改机位，不要把母版原来的衣服颜色留下来。

未加载入口时先读 `../aionforge/SKILL.md`。`forge` = `uv run --project <入口目录>/scripts forge`，入口目录是本 SKILL.md 同级的 `../aionforge`。Prompt 模板：`../aionforge/references/prompts/sku.md`。标准流程按入口 Skill。

## 输入

| 素材 | 角色 | 必填 |
| --- | --- | --- |
| 母版：已通过的 `main/<product>-<color>-hero.png`，或用户指定的产品图 / 模特成片 | `source` | 是 |
| 每个颜色的 `bg_white` 成衣 | `garment` | 是，可多张；用户指定几张就出几张 |

用户点名的配色全部入计划，一色一张。没说清哪几张配色时，按入口 Skill「生图前确认」问要哪些色。

优先用 main 里已通过的模特成片当母版：这样 SKU 和主图是同一个人、同一姿势、同一场景。没有 main 时，再用产品图或 3D 隐形人台成片当母版。

## 输出

- `output/<logo>/sku/<product>-<color>.png`
- 单色商品可省略 color：`<product>.png`
- 同名重跑时旧图自动进 `<product_dir>/history/`

## 步骤

1. `forge doctor --json`。
2. 复用已有商品工作区。没有 `bg_white` 时先走 `aionforge-white`；没有通过质检的 main 母版时，问用户用哪张当母版，或改用产品图 / 隐形人台。
3. 看母版锁构图与人物；看配色白底锁版型、领口、袖口、下摆、印花。把母版路径、各色 `bg_white` 路径、色名写入 `facts.json` 的 `colors[]` 与 `canonical`。写完按入口 Skill「锁商品事实」给用户核对，通过后再出图。
4. `plan.json` 一色一任务，`name` = `<product>-<color>`，比例跟母版（用户点名则用用户的，默认 `1:1`）。
5. 每张复制 `../aionforge/references/prompts/sku.md` 到 `<product_dir>/prompts/sku/<product>-<color>.txt`，写上本张配色和母版路径：
   ```bash
   forge prompt check --file <product_dir>/prompts/sku/<product>-<color>.txt \
     --facts <product_dir>/facts.json --json
   forge generate --product-dir <product_dir> --bucket sku \
     --prompt-file <product_dir>/prompts/sku/<product>-<color>.txt \
     --ref source=<母版> \
     --ref garment=<output/<logo>/bg_white/<product>-<color>.png> \
     --name <product>-<color> --ratio <母版比例，默认 1:1> --json
   forge verify --image <output/<logo>/sku/<product>-<color>.png> \
     --ratio <母版比例，默认 1:1> --json
   ```
6. **看图质检**（必须看）：
   - 人、姿势、头朝向、场景、光线与母版一致。
   - 衣服是本张配色白底那一件：颜色、领口、袖口、下摆、印花；不是母版原来的颜色。
   - 印花只出现一次，未镜像；白底图未展示的背面按同色素面。
   - 没有母版原衣色块残留。
   - 画幅铺满，没有白边、黑边、letterbox。
7. 失败点名「袖口是平口 / 颜色是藏青不是黑 / 不要保留母版原色」，同一个 `--name` 重跑一次。两张仍失败记入交付，继续下一色。
8. 交付 `sku/` 文件列表；说明母版用的是哪张 main 成片。
