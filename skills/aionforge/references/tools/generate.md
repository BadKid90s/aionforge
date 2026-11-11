# forge generate

| 项 | 值 |
| --- | --- |
| command | `forge generate` |
| kind | model（调用图片模型） |
| reads | Prompt、参考图 |
| writes | `<bucket>/<name>.png`、`prompts/<bucket>/<name>.txt`、`manifest.json` |

调用图片模型生成一张成品图，写入指定的交付目录（`bg_white` / `main` / `detail`）；Prompt 和参考图自动收进商品工作区。**一张图一次调用**。

## 参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--product-dir` | 必填 | 商品工作区目录 |
| `--bucket` / `-b` | 必填 | 成品落点：`bg_white` / `main` / `detail` |
| `--prompt` / `-p` | 与 `--prompt-file` 二选一 | Prompt 字符串 |
| `--prompt-file` | 与 `--prompt` 二选一 | 从文件读 Prompt，推荐 |
| `--ref` / `-r` | 可重复 | 参考图；带角色写 `garment=./a.png`、`garment_back=`、`model=./b.jpg`、`print=`、`source=`、`pose=` |
| `--name` / `-n` | `image` | 结果文件名（不含扩展名） |
| `--ratio` | 空 | 输出比例 `W:H`，宽高均大于 480px |
| `--fit` | `expand` | 比例不符时 `expand` 扩图铺满 / `crop` 居中裁切 |
| `--background` | `white` | 模型返回透明底时铺的底色；详情图可用 `#F7F5F2` |
| `--json` | 关闭 | 输出 JSON 信封 |

## 输出

- 成品：`<logo>/<bucket>/<name>.png`
- Prompt：`<product_dir>/prompts/<bucket>/<name>.txt`
- 参考图按角色复制为 `refs/<role>.png`（同角色多张加序号），让模型看见文件名。

## 保证

- 每次只出一张图。
- 透明参考图在发给模型前自动铺白底，避免网关压成黑底。
- 比例不符时默认扩图铺满，不留白边、黑边、letterbox。
- 同名重跑时旧图自动进 `history/`。

## 不适用

- 平面印花抠图请用 `cutout`，核心小图标提取请用 `extract-core-element`。
- 平面印花合成、文字不能重画时，优先用 `composite`。

## 失败与处置

| 现象 | 处置 |
| --- | --- |
| `ok: false` 且含 401 / 403 | 配置问题，先跑 `doctor`，不要重试 |
| 网络 / 超时 / 限流 | 同参数重试 1 次 |
| 参数错误 | 修正后重跑 |
| 图已生成但质检失败 | 改 Prompt 点名出错部位，同一 `--name` 覆盖 |

## 标准调用

```bash
forge generate --product-dir <product_dir> --bucket main \
  --prompt-file <product_dir>/prompts/main/<product>-<color>-hero.txt \
  --ref garment=<bg_white> --ref model=<模特图> \
  --name <product>-<color>-hero --ratio 1:1 --json
```
