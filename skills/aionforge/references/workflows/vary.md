# 工作流：电商图裂变

基于一张已通过的参考图（通常是换装成功的模特图），保持服装身份、场景和风格，变化**机位**和**姿势**。出图只调用 `forge generate`。

- Prompt 骨架：`references/prompts/vary.md`
- 机位 / 姿势 / 成片配方：`references/catalog/poses.json`
- 场景：`references/catalog/scenes.json`（默认锁参考图场景；用户要换场景时按 keywords 选）
- 风格：`references/catalog/styles.json`（把 `style_lock` 贴进每一张）
- 加新定义：见 `references/catalog/README.md` 与 `references/catalog/schemas/`

方法对齐风格裂变：参考图贡献光线、色板、房间、人物身份；衣服结构优先成衣图。

## 何时用

用户说裂变、多机位、多姿势、lookbook、再出几张、保持场景换角度。

换一件衣服或换一个模特 → `tryon`。详情卖点长图 → `pdp`。

## 输入

| 素材 | 角色 | 必填 |
| --- | --- | --- |
| 参考成片 | source | 是 |
| 白底成衣 | garment | 建议有 |
| 套餐或点名姿势 | 计划 | 否，默认 8 张 |

## 选配方

1. 读取 `references/catalog/poses.json`。风格从 `references/catalog/styles.json` 选，场景默认跟参考图；用户点名场景则读 `references/catalog/scenes.json`。
2. 用户没点名且商品是 T恤/卫衣/长袖：用 `packs.tee-hoodie-12`。其他品类用 `default-8`。
3. 「全套 / 多拍」：`lookbook-16`。「只要走姿」：`motion-6`。「只要细节」：`detail-4`。只要 T恤：`tee-8`。只要卫衣：`hoodie-10`。
4. 用户点了坐姿、回眸、低机位：在 `recipes[].keywords` 和 `poses[].keywords` 里匹配。
5. 无印花：按 `substitutions.no_print` 替换；裤装：按 `substitutions.pants` 替换；`requires` 含 `pockets` 而衣服无袋则跳过。
6. 每张 `plan.json` 写 `name` = 配方 `id`，`prompt` = 配方 `prompt`，`ratio`。

禁止用旧的 9 行短名（`vary-front` 这种一句话）代替配方；短名没有姿势，模型会把每张拍成同一姿势。

## 步骤

1. doctor。
2. `forge job init --workflow vary --slug <短名> --json`（或接到已有 tryon 的 `run_dir`）。
3. 看参考图锁视觉 DNA：房间、光线、色温、人物。看成衣图锁版型印花。
4. 按上一节选出配方，展示计划表（name + 一句话目标），等人批准。
5. 每张：按 `references/prompts/vary.md` **整份骨架填写**。先看图写人物/印花零件/房间道具，再把配方 `prompt` 只填进「本张机位与姿势」，并写清与成片差在哪。禁止只写「同一人同一件衣服 + 走两步」这种短句。Style Lock 用 `references/catalog/styles.json` 原文。
6. 出图：

```
forge generate --job-dir <run_dir> \
  --prompt-file <run_dir>/work/prompts/vary-front-relax.txt \
  --ref source=<参考成片> --ref garment=<成衣> \
  --name vary-front-relax --ratio 1:1 --json
```

`--name` 必须等于配方 id。没有成衣时只传 `--ref source=`。指定 `--ratio` 后默认扩图铺满，参考图比例不够时不要留白。

7. 质检：同一件衣服、同一双眼睛和五官、同一房间；头随本张姿势转；机位和姿势与配方一致；与成片构图有明显差别；印花未漂。
8. 失败只重做该 `--name`。
