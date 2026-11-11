# forge CLI 参考

出图一律调用本 Skill 自带的 CLI。下文 `forge ...` 都是 `uv run --project <skill目录>/scripts forge ...` 的简写，在用户工作目录执行；首次运行 uv 会自动装依赖。

Key 从环境变量读取，其次是当前目录 `.env`，再其次是 `<skill目录>/.env`（模板 `<skill目录>/.env.example`）。

## workspace init

```bash
forge workspace init --logo <logo> --json
```

创建或复用 `output/<logo>/`，补齐四个交付目录：

```text
<logo>/
  bg_white/  main/  sku/  detail/
  .forge/
    workspace.json
    products/
    history/
```

| 参数 | 说明 |
| --- | --- |
| `--logo` / `-l` | 图案 / logo 设计名，从图案主标题推断；素材站水印不是 logo 名 |
| `--root` | 成品根目录，默认 `output` |
| `--json` | 输出 JSON 信封 |

## product init

```bash
forge product init --logo <logo> --product <product> --json
```

创建或复用商品工作区，生成 `facts.json` / `project.json` / `manifest.json` 模板：

```text
<logo>/.forge/products/<product>/
  project.json
  facts.json
  manifest.json
  refs/  prompts/  tmp/  history/
```

| 参数 | 说明 |
| --- | --- |
| `--logo` / `-l` | 图案 / logo 设计名 |
| `--product` / `-p` | 衣服款式短名（`short` / `long` / `tee` / `hoodie`），进入文件名 |
| `--root` | 成品根目录，默认 `output` |
| `--json` | 输出 JSON 信封，含 `product_dir` / `facts` / `manifest` |

已存在的 `facts.json` 不会被覆盖，可放心重复 init。

## generate

每次出一张图。成品写 bucket，中间产物写 store，二选一。

| 参数 | 说明 |
| --- | --- |
| `--product-dir` | 商品工作区目录，由 `product init` 生成 |
| `--bucket` / `-b` | 成品落点：`bg_white` / `main` / `sku` / `detail` |
| `--store` | 中间产物落点：`refs`（印花 / 白底素材）或 `tmp` |
| `--prompt` / `-p` | 提示词字符串，与 `--prompt-file` 二选一 |
| `--prompt-file` | 从文件读提示词（推荐） |
| `--ref` / `-r` | 参考图，可重复；带角色写 `garment=./a.png`、`garment_back=./a_back.png`、`model=./b.jpg`、`print=`、`source=`、`pose=` |
| `--name` / `-n` | 结果文件名（不含扩展名），写入 `<bucket>/<name>.png` |
| `--ratio` | `W:H`，输出宽高均大于 480px |
| `--fit` | `expand`（默认，扩图铺满）/ `crop`（居中裁切） |
| `--cutout` | 白底转透明并按图案裁切，本地处理 |
| `--padding` | `--cutout` 的透明边距像素，默认 8 |
| `--threshold` | 背景估计失败时的亮度阈值，默认 238 |
| `--tolerance` | 与边缘采样背景色的最大通道差，默认 18 |
| `--remove-enclosed-white` | `--cutout` 时把封闭白区（字母孔洞、镂空）也清成透明；白色字标不要开 |
| `--denoise` | `--cutout` 时删除面积小于该像素数的 alpha 孤岛，默认 0（关闭） |
| `--json` | 输出 JSON 信封 |

```bash
# 印花提取：中间产物进 refs
forge generate --product-dir <product_dir> --store refs \
  --prompt-file <product_dir>/prompts/refs/<product>-print.txt \
  --ref <成衣图> --name <product>-print --cutout --json

# 白底合成：成品进 bg_white
forge generate --product-dir <product_dir> --bucket bg_white \
  --prompt-file <product_dir>/prompts/bg_white/<product>-<color>.txt \
  --ref print=<product_dir>/refs/<product>-print.png \
  --ref garment=<白底成衣> \
  --name <product>-<color> --ratio 1:1 --json

# 模特换衣：成品进 main
forge generate --product-dir <product_dir> --bucket main \
  --prompt-file <product_dir>/prompts/main/<product>-<color>-hero.txt \
  --ref garment=<bg_white 成衣> --ref model=<模特图> \
  --name <product>-<color>-hero --ratio 1:1 --json

# 姿势裂变：锚点当 source
forge generate --product-dir <product_dir> --bucket main \
  --prompt-file <product_dir>/prompts/main/<product>-<color>-walk.txt \
  --ref source=<main 锚点> --ref garment=<bg_white 成衣> \
  --name <product>-<color>-walk --ratio 1:1 --json

# SKU：main 母版 + 本张配色 bg_white
forge generate --product-dir <product_dir> --bucket sku \
  --prompt-file <product_dir>/prompts/sku/<product>-<color>.txt \
  --ref source=<main 母版> --ref garment=<bg_white 本色> \
  --name <product>-<color> --json

# 详情：bg_white + 可选 main 锚点
forge generate --product-dir <product_dir> --bucket detail \
  --prompt-file <product_dir>/prompts/detail/<product>-<color>-craft.txt \
  --ref garment=<bg_white 成衣> --ref source=<main 锚点> \
  --name <product>-<color>-craft --ratio 3:4 --json
```

同名重跑会覆盖成品，旧图自动进商品 `history/`。Prompt 和 staged refs 始终写进商品工作区。

## cutout

```bash
# 平面 logo 稿：模型清洗白底，本地生成透明通道（推荐）
forge cutout --input <logo稿> --product-dir <product_dir> --name <product>-print --ai --json

# 深色图案 / 字母孔洞：连封闭白区和压缩噪点一起清
forge cutout --input <logo稿> --product-dir <product_dir> --name <product>-print \
  --ai --remove-enclosed-white --denoise 4 --json

# 原稿本来就是干净透明 PNG：只走本地，文字和形状逐像素不变
forge cutout --input <logo稿> --product-dir <product_dir> --name <product>-print --json
```

平面图案稿预处理，输出透明底 PNG 到 `<product_dir>/refs/<name>.png`。

- 默认本地抠图：按四边背景色自适应去底，裁到图案主体。原稿自带 alpha 时，也会清理与 alpha 边界连通的白底 / 白边；图案内部的白色文字、描边和高光保留。
- `--ai`：先让图片模型把图案清洗到纯白底，再本地抠图。适合 alpha 内残留白底、白边或半透明光晕的原稿。模型只做背景清理，不重新设计；最终 alpha 仍由本地生成，不依赖模型直接输出透明图。
- 背景色不是纯白（米白、浅灰）时调大 `--tolerance`；背景和图案亮度接近时调大 `--threshold`，或直接用 `--ai`。
- 深色图案、字母孔洞需要把封闭白区也清掉时加 `--remove-enclosed-white`；白色字标保持默认的 `--keep-enclosed-white`。
- 稿子里有压缩噪点、孤立白点时加 `--denoise 4`，删除小于 4 像素的 alpha 孤岛。
- 图案内部有透明镂空（字母内圈、图形穿孔）或图案本身就是白色时，不要用 `--ai`：模型会把镂空当成白色细节保留，纯白图案可能被清洗成空白。这两类稿子用本地路径，`--clean-white` 会保留图案内部白色。

| 参数 | 说明 |
| --- | --- |
| `--input` / `-i` | 平面 logo 图案稿（JPG / PNG / WebP） |
| `--product-dir` | 商品工作区目录 |
| `--name` / `-n` | 输出文件名，写入 `refs/<name>.png` |
| `--padding` | 透明边距像素，默认 8 |
| `--threshold` | 背景估计失败时的亮度阈值，默认 238 |
| `--tolerance` | 与边缘采样背景色的最大通道差，默认 18 |
| `--clean-white/--no-clean-white` | 原稿带 alpha 时仍清理边界连通白底，默认开启；纯白 logo 可关闭 |
| `--remove-enclosed-white/--keep-enclosed-white` | 是否把封闭白区（字母孔洞、镂空）也清成透明，默认保留 |
| `--denoise` | 删除面积小于该像素数的 alpha 孤岛，默认 0（关闭） |
| `--ai` | 先调用图片模型清洗白底，再本地抠图 |
| `--json` | 输出 JSON 信封 |

印花只存在于成衣实拍上时，用 `generate --store refs --cutout` 让模型先提取再本地去底；平面稿有白残留则优先 `cutout --ai`。

## extract-element

```bash
forge extract-element --input <印花.png> --product-dir <product_dir> \
  --name <product>-print --min-pixels 16 --json
```

把透明底印花按 alpha 的 8 邻接连通域拆成独立元素，输出：

- `refs/<name>-element-01.png`、`-02.png`……每个元素单独裁切并保留透明边距。
- `refs/<name>-elements.json`：每个元素的 bbox、面积、`touches_edge`（是否贴到源图边缘，贴边说明可能被裁断）。

先跑 `cutout` 或 `cutout --ai` 得到干净透明底，再拆元素。文字和图形会被拆成连通域；想按词合并，用 `--min-pixels` 过滤细小噪点后按需要组合。

| 参数 | 说明 |
| --- | --- |
| `--input` / `-i` | 透明底印花（PNG / WebP） |
| `--product-dir` | 商品工作区目录 |
| `--name` / `-n` | 输出前缀，默认 `print` |
| `--min-pixels` | 忽略面积小于该像素数的连通域，默认 16 |
| `--padding` | 每个元素的透明边距像素，默认 4 |
| `--json` | 输出 JSON 信封，含 `elements` / `incomplete` / `catalog` |

## composite

```bash
forge composite --garment <白底成衣> --print <透明印花> \
  --product-dir <product_dir> --bucket bg_white \
  --name <product>-<color> --x 0.5 --y 0.45 --width 0.35 --ink auto --json
```

本地合成：把透明印花按坐标贴到成衣图上，不调用图片模型，文字和颜色不会被重画。

- `--ink auto`：浅色衣用正片叠底（保留布料明暗），深色衣用白墨底，并把中性深色笔画转成白色。
- `--ink multiply`：正片叠底，适合浅色衣；白色印花会接近隐形。
- `--ink normal`：直接 alpha 合成，适合白墨或彩色印花。
- `--ink white`：白墨打底 + 深色笔画转白，适合深色衣；`--underbase-expand` 默认 0，调大会出现白边。
- `--x` / `--y` / `--width` 都是画布比例，默认中心 0.5 / 0.38、宽度 0.35；印花超出画布会报错。
- `--shading` 布料明暗强度，默认 0.25；`--opacity` 印花不透明度，默认 1。

| 参数 | 说明 |
| --- | --- |
| `--garment` / `-g` | 成衣图，通常用 `bg_white` 成品 |
| `--print` / `--print-file` | 透明底印花 PNG / WebP |
| `--product-dir` | 商品工作区目录 |
| `--bucket` / `--store` | 成品或中间产物落点，二选一 |
| `--name` / `-n` | 结果文件名，默认 `print-composite` |
| `--x` / `--y` / `--width` | 印花中心和宽度，占画布比例 |
| `--ink` | `auto` / `multiply` / `normal` / `white` |
| `--shading` | 布料明暗强度 0-1，`multiply` 模式不再叠加 |
| `--opacity` | 印花不透明度 0-1 |
| `--underbase-expand` | 白墨底外扩像素，默认 0 |
| `--json` | 输出 JSON 信封，含 `ink` |

## verify

```bash
forge verify --image <成品.png> --ratio 1:1 --white-bg --json
```

| 参数 | 说明 |
| --- | --- |
| `--image` / `-i` | 要校验的成品图 |
| `--ratio` | 期望比例，例如 `1:1` / `3:4` |
| `--white-bg` | 采样四边，检查是否接近纯白 |
| `--alpha` | 检查是否保留透明通道（印花提取用） |
| `--print` | 印花质量：透明通道、alpha 边界白边、小于 4px 的孤立碎点 |
| `--min-side` | 宽高最小值，默认 480 |
| `--json` | 输出 checks 列表 |

只做确定性检查：文件、尺寸、比例、白底、alpha、印花白边与碎点。审美与商品事实由 Agent 看图判断。`--print` 的白边项对白色字标会误报，结合图案判断即可。

## prompt check

```bash
forge prompt check --file <prompt.txt> --facts <facts.json> --visible-text --json
```

检查：

- 是否用「图1 / 图2」指代参考图。
- 是否含 6 位 Hex 色号。
- 有画面内文字时是否含 `VISIBLE_TEXT_BLOCK`，文案是否用 `「...」` 包裹。
- `facts.print.text_exact` 是否逐字出现在 Prompt 中。

`--visible-text` 用于信息图 / 卖点图这类需要渲染文字的画面。

## list

```bash
forge list --logo <logo> --json
forge list --logo <logo> --bucket main --json
```

列出四个 bucket 里已经生成的成品、大小和修改时间。

## doctor

```bash
forge doctor --json
forge doctor --deep --json
```

检查配置、Key、浅层连通性、日志与数据目录。任一项 `pass: false` 时把 `suggestion` 告诉用户并停下。

`--deep` 会真实 POST 一次 `/images/edits`（产生一次模型调用），检查模型名、额度、网关协议是否真的能出图。`image.reachable` 只测 `GET /models`，通过不代表出图通道可用；生成连续失败时先跑 `--deep`。

## JSON 信封

```json
{"ok": true, "run_dir": "...", "images": ["..."], "error": null}
```

`generate` 额外带 `logo` / `product` / `product_dir` / `bucket` / `store`；`doctor` / `verify` 带 `checks`；`prompt check` 带 `issues`。

`ok: false` 时看 `error.reason` 分诊；失败只重试该张 1 次。
