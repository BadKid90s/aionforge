# forge print metrics

| 项 | 值 |
| --- | --- |
| command | `forge print metrics` |
| kind | local（纯 Pillow） |
| reads | 原稿或透明印花，可多张 |
| writes | 无 |

给印花做客观体检：宽高比、色数、细节密度、平均笔画、透明孔洞、是否触边。只给数字，不做「适合正面还是背面」的结论；结论属于流程。

## 参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--input` / `-i` | 必填，可重复 | 原稿 JPG / PNG / WebP，或透明 PNG |
| `--max-colors` | 8 | 调色板最多取几种主色 |
| `--json` | 关闭 | 输出 JSON 信封 |

## 输出

每张图一条：

| 字段 | 含义 |
| --- | --- |
| `source` | 输入路径 |
| `has_alpha` | 输入是否自带 alpha |
| `background_estimated` | 无 alpha 时是否在内存里估出了背景 |
| `size` / `bbox` | 原图尺寸与前景包围盒 |
| `aspect` | 包围盒宽 / 高 |
| `coverage` | 不透明像素 / 包围盒面积 |
| `palette[]` | 主色 `hex` 与 `share`，share 只按不透明像素算 |
| `edge_density` | alpha 边界像素 / alpha 像素；越高越碎 |
| `mean_stroke_px` | alpha 面积 / 边界像素，平均笔画宽度代理 |
| `mean_stroke_ratio` | `mean_stroke_px / bbox 宽度` |
| `transparent_holes` | 不触边的封闭透明孔洞数 |
| `touches_edge` | 前景是否贴到画布边缘 |

## 保证

- 不写文件，不建工作区；可以直接对用户给的原稿批量跑。
- 无 alpha 时在内存里估背景，不会污染源文件。
- 只输出客观指标，不判断正反面、不选核心元素。

## 不适用

- 不要用它替代 `verify --print`；后者检查白边和碎点。
- 不要把「色数少」直接等同于适合正面；还要看文字大小和构图。
- 带素材站水印的原稿会把水印算进调色板和包围盒；精确指标请先 `cutout` 成透明稿再测。

## 失败与处置

| 现象 | 处置 |
| --- | --- |
| 背景估计失败 | 改传已抠好的透明 PNG |
| 全透明 / 空白 | 检查输入或先重新抠图 |
| 指标异常 | 看 `has_alpha` 与 `background_estimated`，确认是否误把衣服当背景 |

## 标准调用

```bash
forge print metrics --input <印花稿> --json
forge print metrics --input <稿A> --input <稿B> --json
```
