---
name: aionforge-sku
description: >
  女装 SKU 配色规格图：用一张已通过的产品图当母版，把多张配色白底成衣套进同一构图。
  用户说 SKU 裂变、SKU 套图、SKU 母版、电商 SKU、SKU 图、批量规格图，或「按这张主图出黑/藏青/浅灰规格图」时使用。
  Use when the user runs /aionforge-sku.
---

# SKU 配色规格图

用一张已通过的产品图当母版，把用户指定的多张配色白底成衣一一套进去，生成同构图的规格图。出图只调用 `forge generate`。

未加载入口时先读 `../aionforge/SKILL.md`。`forge` = `uv run --project <入口目录>/scripts forge`，入口目录是本 SKILL.md 同级的 `../aionforge`。Prompt 模板：`../aionforge/references/prompts/sku.md`。标准流程按入口 Skill。

母版锁人、姿势、场景、光线；本张配色白底锁衣服颜色、面料、印花。不要改机位，不要把母版原来的衣服颜色留下来。

换姿势 / 换机位 → `aionforge-vary`。换一件不同款 → `aionforge-tryon`。

## 输入

| 素材 | 角色 | 必填 |
| --- | --- | --- |
| SKU 母版（模特成片或已通过的产品图） | source | 是 |
| 配色白底成衣 | garment | 是，可多张；用户指定几张就出几张 |

用户点名的配色全部入计划，一色一任务。没说清哪几张配色时，按入口 Skill「生图前确认」问要哪些色。

## 步骤

1. `forge doctor --json`。
2. `forge job init --workflow sku --slug <短名> --json`。
3. 登记角色：母版 → `source`；每张配色白底 → `garment`，slug 用颜色短名（`black` / `navy` / `heather`，或文件名里的色名）。
4. 看母版锁构图与人物；看配色白底锁版型、领口、袖口、下摆、印花。写入 `facts.json`（`visual_features.main_color` 写母版色；各配色色名写入计划）。写完按入口 Skill「锁商品事实」给用户核对，通过后再进入下一步。
5. `plan.json` 一色一任务，`name` = `sku-<slug>`，比例跟母版（用户点名则用用户的，默认 `1:1`）。
6. 每张复制 `../aionforge/references/prompts/sku.md` 到 `work/prompts/sku-<slug>.txt`，写上本张配色。
7. 出图（一次一张、一张一色）：

```
forge generate --job-dir <run_dir> \
  --prompt-file <run_dir>/work/prompts/sku-black.txt \
  --ref source=<母版> --ref garment=<该色白底> \
  --name sku-black --ratio 1:1 --json
```

8. 质检（必须看图）：
   - 人、姿势、头朝向、场景、光线与母版一致
   - 衣服是本张配色白底那一件：颜色、领口、袖口、下摆、印花；不是母版原来的颜色
   - 印花只出现一次，未镜像；白底图未展示的背面按同色素面
   - 没有母版原衣色块残留
9. 失败点名「袖口是平口 / 颜色是藏青不是黑」，同一 `--name` 重跑 1 次。两张仍失败记入交付，继续下一色。
