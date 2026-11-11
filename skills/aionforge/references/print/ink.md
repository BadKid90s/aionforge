# 撞色与对比度适配

印花和成衣颜色冲突时，先量对比度，再决定是换墨色、提亮 / 压暗，还是换位置。**只改颜色，不改形状、文字和 alpha。**

## 阈值

| 内容 | 最低对比度 |
| --- | --- |
| 大面积图形、粗笔画 | 3:1 |
| 小字、细线、徽章文字 | 4.5:1 |
| 深浅色相邻的描边 | 3:1 |

对比度按 WCAG 相对亮度计算，工具会返回 `contrast_before` / `contrast_after`。

## 策略矩阵

| 成衣亮度 | 印花情况 | 策略 | 合成墨色 |
| --- | --- | --- | --- |
| 浅色（> 0.65） | 深色 / 彩色墨 | `multiply` | `multiply` 或 `auto` |
| 浅色 | 白色 / 浅黄墨，对比 < 3:1 | `darken` 或加深描边 | `normal` |
| 中灰（0.3–0.65） | 任意 | `normal` + 必要时 `outline` | `normal` |
| 深色（< 0.3） | 中性深色笔画 | `white`：白墨打底 + 深色转白 | `white` |
| 深色 | 高饱和彩色 | `lighten`：提亮明度、保留色相 | `normal` 或 `white` |
| 任意 | 小字 < 4.5:1 | 文字改白 / 黑，或把印花移到背面 | 按新颜色选 |

注意：`print adapt` 的 `strategy` 不是 `composite` 的 `ink`。facts 里的 `placement.ink` 只能写 `auto` / `multiply` / `normal` / `white`；适配后的印花文件写进 `placement.source`。

## 操作步骤

1. 对目标成衣和印花跑 `print metrics`，看主色与平均亮度。
2. 跑 `print adapt`，先用 `auto`；看返回的 `strategy`、`contrast_before` / `contrast_after`。
3. 对比度达标就继续；不达标按矩阵换策略重跑一次。
4. 仍不达标时加 `outline`，或把印花移到背面。
5. 把适配后的文件写进 `facts.print.placements[].source`，把 `composite` 的 `ink` 写成对应模式。

## 禁止

- 不要用模型重绘来解决撞色；那会改字、改形状。
- 不要把白色印花直接印在浅色衣上；正片叠底会让它接近隐形，这是正常现象，不是失败。
- 不要只改文字颜色而留下同色的图形；整张印花的相对配色要一起看。
- 不要在适配后重新裁切或缩放；除 `outline` 外加描边环外，alpha 必须与输入逐像素一致。
