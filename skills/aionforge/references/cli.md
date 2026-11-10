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
forge cutout --input <logo稿> --product-dir <product_dir> --name <product>-print --json
```

平面 logo 图案稿本地预处理：按四边背景色自适应去底，裁到图案主体，输出透明底 PNG 到 `<product_dir>/refs/<name>.png`。不调用图片模型，所以图案文字和形状不会被重画。

| 参数 | 说明 |
| --- | --- |
| `--input` / `-i` | 平面 logo 图案稿（JPG / PNG / WebP） |
| `--product-dir` | 商品工作区目录 |
| `--name` / `-n` | 输出文件名，写入 `refs/<name>.png` |
| `--padding` | 透明边距像素，默认 8 |
| `--json` | 输出 JSON 信封 |

只有印花只存在于成衣实拍上时，才用 `generate --store refs --cutout` 让模型先提取再本地去底。

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
| `--min-side` | 宽高最小值，默认 480 |
| `--json` | 输出 checks 列表 |

只做确定性检查：文件、尺寸、比例、白底、alpha。审美与商品事实由 Agent 看图判断。

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
```

检查配置、Key、连通性、数据目录。任一项 `pass: false` 时把 `suggestion` 告诉用户并停下。

## JSON 信封

```json
{"ok": true, "run_dir": "...", "images": ["..."], "error": null}
```

`generate` 额外带 `logo` / `product` / `product_dir` / `bucket` / `store`；`doctor` / `verify` 带 `checks`；`prompt check` 带 `issues`。

`ok: false` 时看 `error.reason` 分诊；失败只重试该张 1 次。
