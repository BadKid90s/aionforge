---
name: aionforge-main
description: >
  女装模特换衣与姿势展示：保留模特原脸和眼神，把 bg_white 成衣穿到模特身上，先出锚点主图，再派生多个机位和姿势。
  用户说换装、换衣、把衣服穿到这个模特身上、保留模特的脸、锁脸出模特图、多机位、多姿势、lookbook、再出几张时使用。
  Use when the user runs /aionforge-main.
---

# 模特换衣与姿势展示（main）

把 `bg_white` 成衣穿到指定模特身上：锁五官和眼睛、锁衣服、锁场景，整件替换上衣。头随姿势转动，不要把头钉死。先出锚点主图，后续姿势全部从锚点派生。

这里的「换脸」指**保留模特原来的脸**换我们的商品衣，不是把另一张脸换到模特身上。用户要给模特换一张脸时，先说明本工作流不支持人脸替换。

未加载入口时先读 `../aionforge/SKILL.md`。`forge` = `uv run --project <入口目录>/scripts forge`，入口目录是本 SKILL.md 同级的 `../aionforge`。Prompt 模板：`../aionforge/references/prompts/tryon.md`、`../aionforge/references/prompts/vary.md`。姿势套餐：`../aionforge/references/catalog/looks.json`。标准流程按入口 Skill。

## 输入

| 素材 | 角色 | 必填 |
| --- | --- | --- |
| 各颜色 bg_white 成衣 | `garment` | 是；没有就先走 `aionforge-white` |
| 有完整人脸的模特图 | `model` | 是 |
| 姿势套餐或关键词（走 / 坐 / 窗光 / 特写） | 计划 | 否，默认 `studio` |
| 单张姿势参考图 | `pose` | 否 |

bg_white 成衣提供商品事实；模特图提供身份与场景，不提供商品版型。禁止只把图案贴到模特原衣上。

## 输出

- 锚点：`output/<logo>/main/<product>-<color>-hero.png`
- 姿势：`output/<logo>/main/<product>-<color>-<pose-id>.png`
- 默认所有颜色都出；用户点名只出一个颜色时，只跑该色。
- 单色商品可以省略 color，例如 `<product>-hero.png`、`<product>-walk.png`。

## 步骤

1. `forge doctor --json`。失败则停。
2. 复用已有商品工作区；没有就先从素材推断 logo / product 并 `forge workspace init` + `forge product init`。没有通过质检的 `bg_white` 时，先走 `aionforge-white`，不要直接拿原始成衣图换装。
3. 看模特图，在 `facts.json` 的 `model` 段记录：五官、眼型、瞳色、双眼皮、眼神光、发型发色、肤色、下装、鞋、包、房间光线。看不清的脸是缺口，按入口 Skill「生图前确认」问用户（换露脸图 / 允许生成五官 / 保持挡脸），不要默默生成。
4. 列出模特原上衣有、成衣没有的结构（罗纹袖口、帽兜、袋鼠兜、旧图案等），写进 Prompt 的「必须去掉」。
5. **阶段一：逐色出锚点**。每个颜色单独跑一张主图。锚点默认复刻模特图原有的姿势、机位、下装、鞋包和房间，只把上衣换成本色 `bg_white`；用户点名要新姿势时才改。每个颜色单独跑：
   ```bash
   forge prompt check --file <product_dir>/prompts/main/<product>-<color>-hero.txt \
     --facts <product_dir>/facts.json --json
   forge generate --product-dir <product_dir> --bucket main \
     --prompt-file <product_dir>/prompts/main/<product>-<color>-hero.txt \
     --ref garment=<output/<logo>/bg_white/<product>-<color>.png> \
     --ref model=<模特图> \
     --name <product>-<color>-hero --ratio <计划比例，默认 1:1> --json
   forge verify --image <output/<logo>/main/<product>-<color>-hero.png> --ratio <计划比例，默认 1:1> --json
   ```
   Prompt 用 `tryon.md`，写死成衣的领口、袖口、下摆、印花文字和本张姿势；风格段从本张 `looks.json` shot 取，必须含 6 位 Hex 色号。
   质检通过后，把这张路径写入 `facts.colors[].anchor`，主色写入 `canonical.anchor`。
6. **阶段二：派生姿势**。锚点通过后，再逐张出姿势图：
   ```bash
   forge prompt check --file <product_dir>/prompts/main/<product>-<color>-<pose>.txt \
     --facts <product_dir>/facts.json --json
   forge generate --product-dir <product_dir> --bucket main \
     --prompt-file <product_dir>/prompts/main/<product>-<color>-<pose>.txt \
     --ref source=<output/<logo>/main/<product>-<color>-hero.png> \
     --ref garment=<output/<logo>/bg_white/<product>-<color>.png> \
     --name <product>-<color>-<pose> --ratio <计划比例，默认 1:1> --json
   forge verify --image <output/<logo>/main/<product>-<color>-<pose>.png> --ratio <计划比例，默认 1:1> --json
   ```
   - 用户说走 / 动态 → `walk`；窗光 / 生活 → `lifestyle`；特写 → `detail`；否则 `studio`。
   - **图案有文字时，把干净印花图也传进去**：`--ref print=<product_dir>/refs/<product>-print.png`，并在 Prompt 写「印花图只用于核对图案形状和逐字写法，不要照搬白底」。实测能明显减少换姿势时的糊字。
   - **复刻模特图的房间时写死取景**：Prompt 里点名拱形镜框、电视、沙发、矮柜的位置不变，禁止新增植物、门或第二扇窗，禁止拉远扩大视野；否则模型会自己扩展场景，四色成片构图对不上。
   - **脸被遮挡时，遮挡物必须跟着姿势走**：模特图用手机、手、帽子或头发挡脸时，每张派生图的 Prompt 都要写「遮挡物始终在脸前，不能离开脸，禁止补全完整五官」。实测一旦没写死，模型会在「提衣摆」「转身」这类需要腾出手的姿势里把手机放下，自己编一张脸。
   - 机位角度以实际画面差异为准：模型可能把 45° 画成接近侧身，只要与其它张角度不同、服装和场景不变，就按通过处理，不必纠结 shot 名称。
   - 无印花时跳过 `requires: ["print"]` 的 shot。
   - 用户给了单屏姿势参考图时加 `--ref pose=`，Prompt 写：身体、手脚、头朝向以姿势参考图为准，本张套餐文字作补充。
   - 每张 Prompt 的【场景】【风格】【镜头语言】【主体动作】整段粘贴 `looks.json` 该 shot，不要拆开重配。
7. **看图质检**（必须看）：
   - 同一人的五官和眼睛；头的朝向符合本张姿势（回眸必须是侧脸 / 过肩，不是正面脸贴在背上）。
   - 衣服是成衣那一件：领口、袖口、下摆、肩线、衣长。
   - 印花位置、文字、颜色与成衣一致，只出现一次。
   - 没有模特原衣残留（罗纹、帽子、旧图案）。
   - 姿势、下装、鞋、包、背景与模特图 / 锚点一致。
8. 失败时改 Prompt 点名出错部位（如「袖口是平口，不是罗纹」「头随身体转向，不要正面脸」），同一个 `--name` 重跑一次。两次仍失败记入交付，继续其余张。
9. 交付 `main/` 文件列表与失败项；如果只出一个颜色，说明 Assumption。
