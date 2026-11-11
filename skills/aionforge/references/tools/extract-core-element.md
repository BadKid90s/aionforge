# forge extract-core-element

| 项 | 值 |
| --- | --- |
| command | `forge extract-core-element` |
| kind | model（始终调用图片模型，不回落本地） |
| reads | 原始印花稿 |
| writes | `refs/<name>.png`、`prompts/refs/<name>.txt`、`manifest.json` |

用图片模型从整张印花里挑出**一枚**轮廓闭合、缩小后仍可辨认的核心图标，重绘到纯白底上，再由本地 flood fill 生成 alpha。用于背面大图配套的左胸小标。

## 参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--input` / `-i` | 必填 | 原始印花稿，白底或透明底均可 |
| `--product-dir` | 必填 | 商品工作区目录 |
| `--name` / `-n` | `core-element` | 输出 `refs/<name>.png` |
| `--element-hint` | 空 | 10–25 字语义描述，如「箭头靶心图标」；留空由模型自选 |
| `--padding` | 12 | 透明边距像素 |
| `--denoise` | 4 | 删除面积小于该像素数的 alpha 孤岛 |
| `--threshold` | 238 | 本地抠白底亮度阈值 |
| `--tolerance` | 18 | 本地抠白底通道容差 |
| `--json` | 关闭 | 输出 JSON 信封 |

## 输出

`refs/<name>.png`，一枚 RGBA 透明底图标。JSON 信封额外含：

- `complete`：内容包围盒距画布边缘是否 ≥2%，`true` 表示未被裁断。
- `margin_ratio`：最小留白比例。
- `content_bbox`：非白内容包围盒。
- `element_hint`：本次使用的描述。

## 保证

- 只保留一个元素；其余文字、装饰、背景被删除。
- 不按 alpha 连通域拆分；元素是语义完整的。
- 封闭白区默认保留，保护白色花瓣、白色字标等设计白墨。
- 模型不可用时直接报错，不静默改用本地抠图。

## 不适用

- 需要列出所有碎片、检查哪些触边时，不要用它；这是语义提取，不是拆碎片。
- 输入是成衣实拍、印花还没有平面稿时，先从成衣提取印花，再用本工具。

## 失败与处置

| 现象 | 处置 |
| --- | --- |
| `complete: false` | 改 `--element-hint` 更具体地点名图标，同一 `--name` 重跑一次 |
| 图标带进文字 | 在 hint 里写「只要图形，不要文字」；仍失败换稿或让用户指定 |
| 模型不可用 | 先确认配置与出图通道，不要改用本地碎片拼徽章 |

## 标准调用

```bash
forge extract-core-element --input <印花稿> --product-dir <product_dir> \
  --name <product>-core --element-hint "<核心图标描述>" --json
forge verify --image <product_dir>/refs/<product>-core.png --print --json
```
