# forge cutout

| 项 | 值 |
| --- | --- |
| command | `forge cutout` |
| kind | hybrid（本地抠图 / `--ai` 先模型清洗白底） |
| reads | 平面印花稿 |
| writes | `refs/<name>.png`、`manifest.json` |

把平面印花稿去背景、裁到图案主体，输出透明 PNG。默认纯本地；`--ai` 先让图片模型清洗白底，透明通道仍由本地生成。

## 参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--input` / `-i` | 必填 | 平面印花稿，JPG / PNG / WebP |
| `--product-dir` | 必填 | 商品工作区目录 |
| `--name` / `-n` | `print` | 输出 `refs/<name>.png` |
| `--ai` | 关闭 | 先模型清洗白底，再本地抠图 |
| `--padding` | 8 | 透明边距像素 |
| `--threshold` | 238 | 背景估计失败时的亮度阈值 |
| `--tolerance` | 18 | 与边缘背景色的最大通道差 |
| `--remove-enclosed-white` | 关闭 | 把封闭白区（字母孔洞、镂空）也清成透明；白色字标不要开 |
| `--denoise` | 0 | 删除面积小于该像素数的 alpha 孤岛 |
| `--json` | 关闭 | 输出 JSON 信封 |

## 输出

`refs/<name>.png`，RGBA，已裁到图案主体并加透明边距。JSON 信封的 `extra.mode` 为 `local-cutout` 或 `ai-cutout`。

## 保证

- 形状、颜色、文字逐像素保留；不做重绘、不做美化。
- 透明通道始终本地生成，原稿自带 alpha 时自动清理外围连通白底。
- 图案内部属于设计的白色（白色文字、描边、高光）默认保留。

## 不适用

- 图案内部有大量透明镂空、或图案本身就是纯白时，不要用 `--ai`；走纯本地路径。
- 原稿带素材站水印时，先换有授权的无水印源文件。
- 需要语义级地挑一枚核心图标时，用 `extract-core-element`，不要用 `cutout`。

## 失败与处置

| 现象 | 处置 |
| --- | --- |
| 抠完是空白 | 检查阈值 / 容差；深色稿可调低 `--threshold` |
| 白边残留 | 调小 `--tolerance` 或开启 `--ai` |
| 图案内部白区被挖空 | 关闭 `--remove-enclosed-white` |
| 碎片噪点 | 加 `--denoise 4` |

## 标准调用

```bash
forge cutout --input <印花稿> --product-dir <product_dir> --name <product>-print --json
forge cutout --input <印花稿> --product-dir <product_dir> --name <product>-print --ai --json
forge verify --image <product_dir>/refs/<product>-print.png --print --json
```
