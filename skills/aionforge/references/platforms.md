# 平台尺寸与排版映射

未指定平台时：国内默认 `main` 主图 `1:1`、`detail` 详情 `3:4`。用户点名平台则用下表。各平台独立的字体、胶囊标签与配色美学见 `typography.md` 与 `catalog/typography.json`。

| 平台 | main 主图比例 | detail 详情比例 | 图内语言 | 默认展示套餐 `looks.json` | 排版美学 `typography.json` |
| --- | --- | --- | --- | --- | --- |
| 淘宝/天猫 | `1:1` | `3:4` | 中文 | `studio` | `taobao`（暖调轻奢画册风） |
| 京东 | `1:1` | `3:4` | 中文 | `studio` | `jd`（都市品质规格美学） |
| 拼多多 | `1:1` | `3:4` | 中文 | `studio` | `pinduoduo`（清透莫兰迪胶囊轻杂志风） |
| 抖音/小红书 | `4:5` 或 `1:1` | `3:4` | 中文 | `lifestyle` | `douyin_xhs`（买手店种草笔记风） |
| Amazon | `1:1`（首图纯白无字） | `3:4` 或 `2:3` | 英文 | `studio` | `amazon`（国际目录级净版美学） |
| Shopify / 独立站 | `1:1` 或 `4:5` | `3:4` | 英文 | `studio` | `shopify`（DTC 极简画廊美学） |
| TikTok Shop | `1:1` | `3:4` | 按站点语言 | `lifestyle` | `shopify` / `douyin_xhs` |
| Shopee / Temu | `1:1` | `3:4` | 英文 | `studio` | `shopify` |

出图比例用 `W:H`。具体像素由模型决定，CLI 会把结果拟合到对应比例（长边约 1024，短边 > 480）。比例不符时默认扩图铺满，不留白边、黑边或 letterbox。参数见 [tools/generate.md](tools/generate.md)。
