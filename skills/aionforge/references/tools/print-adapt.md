# forge print adapt

| 项 | 值 |
| --- | --- |
| command | `forge print adapt` |
| kind | local（纯 Pillow） |
| reads | 透明印花、成衣图、落点区域 |
| writes | `refs/<name>.png`、`manifest.json` |

按成衣底色重映射印花颜色，解决撞色和对比度不足。只改颜色，不改 alpha、几何和文字形状。

## 参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--print` / `--print-file` | 必填 | 透明印花 PNG |
| `--garment` / `-g` | 必填 | 该颜色的成衣图 |
| `--product-dir` | 必填 | 商品工作区目录 |
| `--name` / `-n` | `print-fit` | 输出 `refs/<name>.png` |
| `--strategy` | `auto` | `auto` / `multiply` / `normal` / `white` / `lighten` / `darken` / `palette` / `outline` |
| `--palette` | 空 | `palette` 策略的目标色，逗号分隔 Hex，如 `#F2F2F2,#1A1A1A` |
| `--region` | 空 | 标准位置预设：`left_chest` / `chest_center` / `back_center` / `back_neck` / `hem_left` / `hem_right` |
| `--x` | `0.5`（或随预设） | 采样区域的中心 x，0–1 |
| `--y` | `0.38`（或随预设） | 采样区域的锚点 y，0–1 |
| `--width` | `0.35`（或随预设） | 采样区域宽度占画布比例 |
| `--max-height` | 空（或随预设） | 采样区域最大高度占画布比例 |
| `--anchor` | `center`（或随预设） | 纵坐标锚点：`center` / `top` / `bottom` |
| `--outline-px` | 4 | `outline` 策略的描边宽度 |
| `--json` | 关闭 | 输出 JSON 信封 |

## 策略

| 策略 | 做什么 |
| --- | --- |
| `auto` | 按成衣亮度与印花对比度自动选下面一种 |
| `multiply` | 不改颜色；合成时用正片叠底保留布料明暗 |
| `normal` | 不改颜色；直接 alpha 合成 |
| `white` | 中性深色笔画转白，配合白墨打底 |
| `lighten` | 提亮明度、保留色相，适合深色衣上的彩色印花 |
| `darken` | 压暗明度，适合浅色衣上的白色 / 浅黄印花 |
| `palette` | 把印花颜色映射到指定调色板，适合徽章简化 |
| `outline` | 在印花轮廓外加一圈对比色描边 |

## 输出

`refs/<name>.png`，RGBA，alpha 与输入逐像素一致。JSON 信封额外含：

- `strategy`：实际使用的策略。
- `contrast_before` / `contrast_after`：按主色 share ≥10% 取最小 WCAG 对比度。
- `map[]`：源色 → 目标色。
- `warnings[]`：适配后仍低于阈值等提示。

## 保证

- 不重绘、不裁切、不改文字；只做像素级颜色重映射。
- 除 `outline` 策略会额外加描边环和画布边距外，输出 alpha 与输入完全一致。
- 对比度按 WCAG 计算，图形目标 ≥3:1，小字目标 ≥4.5:1。

## 不适用

- 需要改变图案形状、补笔画、换风格时，用 `generate`，不要用本工具。
- `outline` 会让画布变大；合成时按新的 `refs/<name>.png` 重新取宽度。
- 适配策略不是合成墨色模式；facts 里的 `placement.ink` 仍只能写 `auto|multiply|normal|white`。

## 失败与处置

| 现象 | 处置 |
| --- | --- |
| 对比度仍低于 3:1 | 换 `lighten` / `darken`，或加 `outline`；仍不行就把印花移到背面 |
| `palette` 缺目标色 | 补 `--palette` 或改用 `auto` |
| 颜色变得不自然 | 降低策略强度，改用 `normal` + `outline` |
| 印花 alpha 被裁 | 检查输入是否透明 PNG；本工具不会裁切 |

## 标准调用

```bash
forge print adapt --print <product_dir>/refs/<product>-print.png \
  --garment <成衣图> --product-dir <product_dir> --name <product>-print-fit \
  --strategy auto --x 0.5 --y 0.4 --width 0.35 --json
```
