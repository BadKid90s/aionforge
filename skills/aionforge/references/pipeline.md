# 标准流程与目录契约

入口 Skill 负责调度、锁事实、确认门槛和质检；具体工作流细节在 `../aionforge-<id>/SKILL.md`。四条业务线共用同一份商品工作区。

## 任务单位

**一个 logo + 一个商品 = 一个商品工作区。** 白底、模特、SKU、详情都从这个工作区取同一份 `facts.json` 和同一套 canonical 路径，不再每个工作流各建一个任务目录。

```text
output/<logo>/
  bg_white/<product>-<color>.png
  main/<product>-<color>-<pose>.png
  sku/<product>-<color>.png
  detail/<product>-<detail-id>.png
  .forge/products/<product>/
    project.json
    facts.json
    manifest.json
    refs/
    prompts/
    tmp/
    history/
```

- 四个 bucket 只放成品，方便运营直接浏览和上传。
- `.forge` 放提示词、参考图、manifest、历史版本，不污染成品目录。
- 同名重跑覆盖成品，旧图自动进 `history/`，不会堆出一串时间戳目录。

## 标准流程

1. **doctor**：`forge doctor --json`。任一项 `pass: false` 就转告 `suggestion` 并停下。
2. **推断 logo**：logo 是平面图案 / 设计稿，不是品牌店名。看图案的主标题文字（如「锁定目标」「LAZY DAY」「CHILL OUT」）、品牌署名和文件名；主标题优先，素材站水印（如「千图网」）不是 logo 名。多个候选或看不出时问用户。用推断结果跑 `forge workspace init --logo <logo> --json`。
3. **推断 product**：product 是衣服款式，不是图案名。从空白成衣文件夹 / 文件名推断，例如 `short`（短袖）、`long`（长袖）、`tee`、`hoodie`；颜色从空白衣文件名或用户说法取，例如 `black` / `white` / `浅灰`。跑 `forge product init --logo <logo> --product <product> --json`，记下 `product_dir`。
4. **锁商品事实**：按 `facts.md` 看图写 `<product_dir>/facts.json`。写完把品类、主色、领口、袖型 / 袖口、下摆、衣长、印花文字与位置、`uncertain` 列给用户核对。**用户确认前禁止写计划、禁止 `forge generate`。** 用户说「你决定 / 直接出」只跳过缺口提问，不跳过事实核对。
5. **先白底**：`aionforge-white` 产出 `bg_white/<product>-<color>.png`。这是后续所有图的衣服唯一真相源；把路径写进 `facts.colors[].bg_white` 和 `facts.canonical.garment`。
6. **再模特**：`aionforge-main` 用 bg_white + 模特图先出锚点，再派生姿势。锚点路径写进 `facts.colors[].anchor` 和 `facts.canonical.anchor`。
7. **按需扩展**：`aionforge-sku` / `aionforge-detail` 只有用户点名才跑。两者都可以把 main 锚点成片当 `source` 或母版，不必只参考 bg_white。
8. **逐张出图**：Prompt 写进 `<product_dir>/prompts/<bucket>/<name>.txt`，先 `forge prompt check`，再 `forge generate --product-dir <product_dir> --bucket <bucket> --name <name>`。
9. **逐张质检**：`forge verify` 做文件 / 尺寸 / 比例 / 白底 / alpha 检查；审美、商品事实和五官一致性由你看图判断。不合格只重做该 `--name`。
10. **交付**：报告四个 bucket 的文件、失败项、Assumptions。

## 确认门槛

必须问用户的缺口：

- `facts.uncertain` 里的关键结构。
- 用户两句话互相打架。
- 比例、张数、场景、印花位置、露脸与配饰、素材角色没说的项。
- 模特图脸被挡或看不清：换露脸图 / 允许生成五官 / 保持挡脸。
- 颜色：用户没点名时默认所有颜色都出；如果素材里颜色缺失或命名不清，问。
- SKU / 详情：用户没点名就不生成。

不必问的项：姿势按 `../references/shots-womenswear.md` 与 `looks.json` 写进计划即可；已经点名的平台、比例、图型直接采用。

## 参考图角色

每张输入图只承担一个角色，`--ref` 必须带角色名：

| 角色 | 允许借用 | 隔离禁区 |
| --- | --- | --- |
| `garment` | 版型、领口、肩线、袖型、袖口、下摆、衣长、面料、颜色、印花文字 | 衣架、吊牌、杂乱背景、临时折痕 |
| `garment_back` | 后背领口、绑带、开衩、后背印花、后下摆 | 不要把正面印花画到后背 |
| `model` | 五官比例、眼型、瞳色、双眼皮、眼神光、发型发色、肤色、下装、包、房间 | 原上衣整件作废；头随本张姿势转 |
| `print` | 图案形状、颜色、逐字文本、相对比例 | 不改成衣版型与面料颜色 |
| `source` | 已通过成片的人物、衣服、场景、光线；SKU 里当母版 | 裂变时只改机位、景别、身体姿势；SKU 里只换衣服颜色 |
| `pose` | 身体姿态、手脚、头朝向 | 五官跟模特图 / 成片，衣服跟成衣图 |

用「成衣图 / 背面成衣图 / 模特图 / 印花图 / 锚点成片 / 姿势参考图」指代参考图，不要写「图1 / 图2」。

## 已知网关行为

真实测试里遇到的两类问题，CLI 已经在本地处理，Skill 不需要额外操作：

1. **透明参考图会被压成黑底。** 部分网关把带 alpha 的参考图铺成黑色再送给模型，模型随即把黑色当成画面背景，白底商品图会变黑底。`forge generate` 会在暂存 `--ref` 时把透明图铺到白底，再传给模型。
2. **模型可能返回透明底成片。** 按比例缩放时直接 `convert("RGB")` 会把透明区丢成黑色。CLI 统一先把 alpha 铺到白底再转 RGB，所以 `bg_white` 落盘就是白底。

如果换了网关后仍出现黑底，先跑 `forge verify --white-bg` 确认，再看 `refs/` 里的暂存图是否带 alpha。

## 质检与失败处理

- 客观检查：`forge verify --image <成品> [--ratio W:H] [--white-bg] [--alpha]`。
- Prompt 底线：`forge prompt check --file <prompt> --facts <facts> [--visible-text]`。
- 看图质检：对照入口 Skill 的质检清单。
- 失败只改 Prompt 里点名出错的部位，同一个 `--name` 重跑一次；两次仍失败记入 manifest，继续其余张。
- `ok: false` 且 reason 含 401 / 403 时引导用户跑 doctor，不要重试。
