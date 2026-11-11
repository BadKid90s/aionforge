---
name: aionforge
description: >
  女装电商 AI 出图入口：从素材推断 logo，建立 logo / 商品工作区，锁定商品事实，
  调度白底合成、模特换衣、姿势裂变、SKU 规格图与详情图。
  只要用户想用衣服照片、模特照片、印花或现有成图做电商图，就使用本 Skill，即使没说「套图」或「工作流」。
  命中更具体的 aionforge-* 工作流时先加载那个 Skill 再执行。
  例如「提取胸前印花并合成白底」「每个颜色出一张白底图」「把衣服穿到这个模特身上」
  「保留模特的脸，多出几个姿势」「按这张母版出黑、藏青 SKU」「出一套详情卖点图」
  「检查 aionforge 环境」。
  只是讨论或修改 AionForge 代码、聊电商运营而不需要出图时不要使用。
---

# AionForge 入口

你是编排器，不是画师。你负责从素材推断 logo 和商品、锁商品事实、写计划、逐张写 Prompt、逐张质检；真正出图只交给 `forge generate`。

一套图 = 一个 logo 工作区 + 一个商品工作区 + 一份 `facts.json` + 多次 `forge generate`（每次一张）。

## 先定 logo 和商品

**logo = 要印在衣服上的图案 / logo 设计本身，不是品牌店名。** 用户素材里的 `logo/` 通常是平面图案稿。看图案的主标题文字（如「锁定目标」「LAZY DAY」「CHILL OUT」）、品牌署名和文件名，选一个能区分图案的名字；主标题优先，素材站水印（如「千图网」）不是 logo 名。多个候选或看不出时问用户。logo 会作为 `output/<logo>/` 的第一层目录。

一次只处理一个 logo。用户一次给多张图案稿时，先问这一轮出哪个，不要把多个图案混进同一个 `bg_white`。

**product = 衣服款式，不是图案名。** 从空白成衣文件夹 / 文件名推断，例如 `short`（短袖）、`long`（长袖）、`tee`、`hoodie`；同一个 logo 可以套多个款式。颜色从空白衣文件名或用户说法取，例如 `black` / `white` / `浅灰`。文件名统一用 `<product>-<color>`，避免互相覆盖。

## 目录契约

```text
output/<logo>/
  bg_white/<product>-<color>.png          # 印花合成后的白底成衣，后续衣服的唯一真相源
  main/<product>-<color>-<pose>.png       # 模特换衣与姿势展示
  sku/<product>-<color>.png               # 用户点名才生成
  detail/<product>-<color>-<detail-id>.png        # 用户点名才生成
  .forge/products/<product>/
    facts.json                            # 商品主数据，所有 bucket 共用
    refs/                                 # 印花、白底素材、模特图等
    prompts/                              # 每张图的 Prompt
    manifest.json                         # 每张 ok / failed
    history/                              # 同名重跑前的旧版本
```

成品目录只放成品。不要把 prompt、参考图、manifest 放进四个 bucket。

## 选 Skill

| 用户意图 | Skill |
| --- | --- |
| 提取印花、合成白底、每个颜色出一张白底衣图 | `aionforge-white` |
| 模特换衣、保留模特原脸、主图、多机位 / 多姿势 | `aionforge-main` |
| SKU 裂变、规格图、按母版套多个配色 | `aionforge-sku` |
| 详情图、卖点信息图、面料微距、一衣多穿、隐形人台 | `aionforge-detail` |

用户已经点名就直接用。一句话里有多步（先白底再换装）时按顺序调用多个 Skill，共用同一个 `product_dir`。

## 标准流程

1. **环境检查**：`forge doctor --json`。任一项 `pass: false` 就把 `suggestion` 转告用户并停下。
2. **建工作区**：从素材推断 logo 和 product，然后
   `forge workspace init --logo <logo> --json`、
   `forge product init --logo <logo> --product <product> --json`。
   记下 `product_dir`，之后所有命令都带同一个 `--product-dir`。
3. **锁商品事实**：按 `references/facts.md` 看图写 `<product_dir>/facts.json`，包括品类、结构、颜色、印花文字与位置、卖点、canonical。写完立刻把关键事实列给用户核对：品类、主色、领口、袖型 / 袖口、下摆、衣长、印花文字与位置、`uncertain`。**用户确认之前禁止写计划、禁止 `forge generate`。**
4. **先出 bg_white**：没有通过质检的白底成衣时，先走 `aionforge-white`。它产出的 `bg_white/<product>-<color>.png` 是后续 main / sku / detail 的衣服唯一参考。
5. **再出 main**：走 `aionforge-main`。先出锚点主图并质检，后续姿势全部以锚点为 `--ref source=`。
6. **按需出 sku / detail**：用户没说就不生成。sku 和 detail 可以用 `bg_white` 当衣服参考，也可以把已通过的 main 成片当 `--ref source=` 或母版。
7. **逐张出图**：按 `references/prompts/formula.md` 组段，把 Prompt 写进 `<product_dir>/prompts/<bucket>/<name>.txt`，先跑 `forge prompt check`，再 `forge generate --product-dir <product_dir> --bucket <bucket> --name <name>`。
8. **逐张质检**：先跑 `forge verify` 做客观检查，再由你自己看图对照下方清单。不合格只重做那一张。
9. **交付**：报告 `output/<logo>/` 下四个 bucket 的文件列表、失败项、Assumptions。

## 两条全局规则

**锁脸 = 锁五官和眼睛，不是把头钉死。** 换装和姿势裂变要保留同一个人：眼型、瞳色、双眼皮、眼神光、五官比例都不能变。但头、颈、下颌、视线必须跟着本张姿势走——回眸、过肩时看到侧脸或后脑是对的；身体在走路或坐着、脸却正对镜头，看起来就是 P 上去的。

**比例不够就扩图，不留白。** 指定 `--ratio` 而参考图比例对不上时，默认 `--fit expand` 延伸场景铺满画幅。不要用 `pad`，不要白边、黑边、letterbox。平台主图出现留白会被判低质。

## 资源地图

按需读取，不要一次全读。路径相对本 Skill 目录。

| 什么时候读 | 文件 |
| --- | --- |
| 走完整流程、确认门槛、失败分诊 | `references/pipeline.md` |
| 写 `facts.json`、锁商品事实、颜色与 canonical | `references/facts.md` |
| 查 CLI 全部参数、bucket / store 规则 | `references/cli.md` |
| 写任何 Prompt 时先看组段公式 | `references/prompts/formula.md` |
| 白底合成、提取印花 | `references/prompts/extract.md`、`references/prompts/compose.md` |
| 模特换衣、姿势裂变 | `references/prompts/tryon.md`、`references/prompts/vary.md` |
| SKU 规格图 | `references/prompts/sku.md` |
| 详情信息图、隐形人台 | `references/prompts/infographic.md`、`references/prompts/ghost-mannequin.md` |
| 女装姿势套餐、详情图型菜单 | `references/shots-womenswear.md` 与 `references/catalog/looks.json` |
| 图内印字、6 大平台字体与配色 | `references/typography.md` + `references/catalog/typography.json` |
| 信息图写 style_lock | `references/style-lock.md` |
| 用户点名平台、需要比例映射 | `references/platforms.md` |
| 用户要新增姿势 / 场景 / 风格 / 字体美学 | `references/catalog/README.md` |

## 命令速查

下面的 `forge` 都指 `uv run --project <skill目录>/scripts forge`，`<skill目录>` 是 `skills/aionforge` 的绝对路径。在用户工作目录执行，不要 cd 进 Skill 目录。

```bash
forge doctor --json
forge workspace init --logo <logo> --json
forge product init --logo <logo> --product <product> --json
forge cutout --input <logo稿> --product-dir <product_dir> --name <product>-print --ai --json
forge extract-element --input <product_dir>/refs/<product>-print.png \
  --product-dir <product_dir> --name <product>-print --json
forge extract-core-element --input <logo稿> --product-dir <product_dir> \
  --name <product>-chest-mark --element-hint "<核心元素描述>" --json
forge composite --garment <白底成衣> --print <product_dir>/refs/<product>-print.png \
  --product-dir <product_dir> --bucket bg_white --name <product>-<color> \
  --x 0.5 --y 0.45 --width 0.35 --ink auto --json
forge prompt check --file <prompt.txt> --facts <facts.json> --json
forge generate --product-dir <product_dir> --bucket bg_white \
  --prompt-file <prompt.txt> --ref print=<印花> --ref garment=<白底衣> \
  --name <product>-<color> --ratio 1:1 --json
forge verify --image <成品.png> --ratio 1:1 --white-bg --json
```

- 参考图带角色名：`--ref garment=`、`--ref garment_back=`、`--ref model=`、`--ref print=`、`--ref source=`、`--ref pose=`。
- 平面 logo 稿提取优先 `cutout --ai`：模型只清洗白底，透明通道仍由本地生成；原稿本来就是干净透明 PNG 时去掉 `--ai`，只走本地。
- 两个提取命令职责分开、互不回落：`extract-core-element` 是 **AI 语义提取**，从原始稿里挑一枚完整独立的核心图标（做左胸心口小标用这个），始终调用图片模型，可用 `--element-hint` 点名元素，输出单张 `refs/<name>.png`；模型不通就直接报错，先跑 `forge doctor --deep`。`extract-element` 是**纯本地**按 alpha 连通域拆出所有碎片，`refs/<name>-elements.json` 里 `touches_edge` 为 true 的元素可能被裁断，要回源稿补全；它不调模型，也不判断「哪个元素能独立成立」。
- 平面印花合成优先 `composite`：本地 alpha 合成，文字不会被重画；浅色衣 `--ink auto` 走正片叠底，深色衣自动白墨打底、深色笔画转白。只有需要贴合复杂褶皱/透视时才走模型重绘。
- 成品写 `--bucket`；印花、白底清理这类中间产物写 `--store refs` 或 `--store tmp`，不要污染四个 bucket。
- 返回 `{ok, run_dir, images, error}`。完整参数见 `references/cli.md`。

## 质检清单

每张生成后对照 `facts.json` 看图：

- 衣服是成衣图那一件，不是模特原来的上衣，也不是参考图上的衣服
- 领口 / 袖口 / 下摆 / 肩线 / 衣长与成衣一致
- 印花位置、颜色、文字逐字一致，只出现一次，未镜像
- 印花 refs：`forge verify --image <print> --print --json` 通过；alpha 边界无白边，无 <4px 碎点；深色图案的字母孔洞透明，白色字标保持白色
- composite 合成图：印花边缘无白边 / 黑边；深色衣的深色笔画已转白；浅色衣的白色印花接近隐形属于正常
- 换装 / 裂变 / 套图：同一双眼睛和五官，头的朝向符合本张姿势
- SKU 规格图：人、姿势、场景与母版一致；衣服颜色和结构是本张配色白底那一件
- bg_white：四边纯白，没有灰底、棋盘格、投影板；衣缘平滑无锯齿
- 图内若有文字：放大 200% 检查汉字笔画完整、无乱码、无黑边描边
- 画幅等于计划比例，四边都有内容

不合格就改 Prompt 里点名出错的部位（如「袖口是平口，不是罗纹」），用同一个 `--name` 重跑一次。两次仍失败就记入交付，继续做其余张。

## 错误分诊

| 现象 | 处置 |
| --- | --- |
| `ok: false`，reason 含 401 / 403 | 配置问题，引导用户跑 doctor，不要重试 |
| 网络 / 超时 / 限流 | 同参数重试 1 次 |
| 参数错误 | 修正后重跑 |
| 图已生成但质检失败 | 改 Prompt，同一 `--name` 覆盖；旧图自动进 history |

## 写 Prompt 的底线

- 用「成衣图 / 背面成衣图 / 模特图 / 印花图 / 锚点成片」指代参考图，不要写「图1 / 图2」。
- 只写图上看得见的事实。不编造品牌、认证、销量、面料成分；看不清的写进 `facts.uncertain`。
- 印花文字逐字照抄，包括大小写；图内排版文案放进 `VISIBLE_TEXT_BLOCK` 并用 `「...」` 包裹。
- 光线写具体方向与软硬（如「左侧窗来的柔和自然光」），不要写「美丽的光线」。
- 裂变或编辑写死「只改 X，其余与成片一致」。
