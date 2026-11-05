# Campaign Style Lock

风格定义在 `references/catalog/styles.json`，字段见 `references/catalog/schemas/style.schema.json`。选定一条后把 `style_lock` 原样放进每一张 Prompt。不要每张重新配色或换光线。用户没点名时默认 `pdd-clean`。

多图任务在出计划前锁定风格。

必填：

1. 视觉方向（棚拍女装电商 / 窗光通勤 / 暖调假日）
2. 色板：背景色、服装以成衣为准、文字色、最多一个强调色（写 hex）
3. 冷暖调：warm / cool / neutral，全套一致
4. 光线：主光方向与软硬
5. 背景逻辑：无缝棚拍 / 同一房间 / 同一室外
6. 字体（若图内有字）：一种无衬线，不混用手写或衬线
7. 产品尺度：服装在画面中的大致占比

用户没给品牌规范时用这段默认锁（可按成衣主色替换强调色）：

```
Campaign Style Lock: consistent womenswear ecommerce set; seamless off-white background #F7F5F2; charcoal text #2D2D2D; one product-matched accent; neutral-cool soft studio light from upper left; modern geometric sans-serif short labels only; garment identity locked to the product photo; generous whitespace; no palette drift, no mixed fonts, no random locations, no extra logos.
```
