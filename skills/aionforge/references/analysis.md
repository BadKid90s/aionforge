# 商品事实 JSON

看图后写入任务目录 `facts.json`。只写图上可见的内容；看不清的字段留空字符串。不要编造品牌、面料成分、认证。

```json
{
  "product_name": "",
  "product_category": "上衣|裙装|裤装|外套|套装",
  "visual_features": {
    "main_color": "",
    "secondary_colors": [],
    "pattern": "",
    "neckline": "",
    "silhouette": "",
    "hemline": "",
    "length": "",
    "sleeves": "",
    "cuffs": "",
    "fabric_texture": ""
  },
  "print": {
    "present": false,
    "placement": "",
    "description": "",
    "text": ""
  },
  "selling_points": [
    { "type": "design|pattern|silhouette|material|function", "title": "", "description": "" }
  ],
  "target_audience": "",
  "target_scenes": [],
  "style_lock": "",
  "uncertain": []
}
```

## 规则

- `print.text` 必须逐字来自图，不准改写
- `uncertain` 列出看不清的部位，后续 Prompt 要求这些部位不要臆造
- 多张输入图必须是同一件衣服；颜色/款式不同则分任务
- 风格参考图的文案、logo、卖点不要写进本文件
