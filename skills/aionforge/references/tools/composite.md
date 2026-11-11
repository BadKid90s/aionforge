# forge composite

| 项 | 值 |
| --- | --- |
| command | `forge composite` |
| kind | local（纯 Pillow） |
| reads | 成衣实拍图、透明印花，或 facts 里的 placement |
| writes | `<bucket>/<name>.png`、`manifest.json` |

把透明印花按位置和宽度合成到 T 恤实拍图上。本地 alpha 合成，**不重绘文字**。浅色衣走正片叠底保留布料明暗，深色衣自动白墨打底、深色笔画转白。

## 参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--garment` / `-g` | 必填 | 成衣实拍图 |
| `--print` / `--print-file` | 与 `--placement` 二选一 | 透明印花 PNG |
| `--placement` | 与 `--print` 二选一 | 从 `facts.print.placements` 读取 `source/x/y/width/ink` |
| `--color` / `-c` | 空 | 成衣颜色名；配合 `--placement` 自动选用该色专属的撞色适配印花与墨色 |
| `--product-dir` | 必填 | 商品工作区目录 |
| `--name` / `-n` | `print-composite` | 结果文件名 |
| `--bucket` / `-b` | `bg_white` | 成品落点：`bg_white` / `main` / `detail` |
| `--x` | 0.5 | 印花中心 x，0–1 |
| `--y` | 0.38 | 印花中心 y，0–1 |
| `--width` | 0.35 | 印花宽度占画布比例 |
| `--ink` | `auto` | `auto` / `multiply` / `normal` / `white` |
| `--shading` | 0.25 | 让印花跟随布料明暗的强度，0–1 |
| `--json` | 关闭 | 输出 JSON 信封 |

## placement 模式

`--placement <id>` 从 `facts.print.placements` 里找对应条目，读取 `source` / `x` / `y` / `width` / `ink`；传入 `--color <color>` 时自动读取该颜色专属的适配印花与墨色。显式参数仍可覆盖。

## 输出

- 成品：`<logo>/<bucket>/<name>.png`
- JSON 信封的 `extra.ink` 是实际使用的墨色。

## 保证

- 文字、形状、颜色逐像素保留，不重画。
- 印花只出现一次，不镜像。
- 同名重跑时旧图自动进 `history/`。

## 不适用

- 需要贴合复杂褶皱、透视、侧身曲面时，改用 `generate` + `compose` 提示词模板。
- 背面印花必须有背面成衣实拍图；不要拿正面图冒充背面。
- 撞色严重时先用 `print adapt` 调色，再合成。

## 失败与处置

| 现象 | 处置 |
| --- | --- |
| 印花超出画布 | 调小 `--width` 或调整 `--x` / `--y` |
| 深色衣上看不见 | `--ink white`，或先用 `print adapt --strategy white` |
| 浅色衣上白印花消失 | 改用 `normal` 或 `print adapt --strategy darken` |
| placement 不存在 | 先走 `aionforge-print` 写 facts，或检查 id |

## 标准调用

```bash
forge composite --product-dir <product_dir> --placement <id> --color <color> \
  --garment <成衣图> --name <product>-<color> --json

forge composite --garment <成衣图> --print <透明印花> \
  --product-dir <product_dir> --name <product>-<color> \
  --x 0.5 --y 0.42 --width 0.35 --ink auto --json
```
