# 平台尺寸与排版映射

未指定平台时：主图和详情默认都是 `1:1`。用户点名平台则用下表。各平台独立的字体、胶囊标签与配色美学见 `references/typography.md` 与 `references/catalog/typography.json`。

| 平台 | 主图比例 | 详情比例 | 图内语言 | 默认风格 `styles.json` | 排版美学 `typography.json` |
| --- | --- | --- | --- | --- | --- |
| 淘宝/天猫 | `1:1` | `1:1` | 中文 | `taobao-warm` | `taobao`（暖调轻奢画册风） |
| 京东 | `1:1` | `1:1` | 中文 | `pdd-clean` | `jd`（都市品质规格美学） |
| 拼多多 | `1:1` | `1:1` | 中文 | `pdd-clean` | `pinduoduo`（清透莫兰迪胶囊轻杂志风） |
| 抖音/小红书 | `1:1` | `1:1` | 中文 | `xhs-fresh` / `ugc-street` | `douyin_xhs`（买手店种草笔记风） |
| Amazon | `1:1`（首图纯白无字） | `1:1` | 英文 | `amazon-white` | `amazon`（国际目录级净版美学） |
| Shopify / 独立站 | `1:1` | `1:1` | 英文 | `editorial-magazine` | `shopify`（DTC 极简画廊美学） |
| TikTok Shop | `1:1` | `1:1` | 按站点语言 | `xhs-fresh` | `shopify` / `douyin_xhs` |
| Shopee / Temu | `1:1` | `1:1` | 英文 | `pdd-clean` | `shopify` |

`forge --ratio` 只接受 `W:H`。具体像素由模型决定，CLI 会把结果拟合到对应比例（长边约 1024，短边 > 480）。
