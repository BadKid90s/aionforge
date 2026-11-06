# Campaign Style Lock

风格定义在 `references/catalog/styles.json`，字段见 `references/catalog/schemas/style.schema.json`。选定后把 `style_lock` 原样放进每一张 Prompt。不要每张重新配色或换光线。

- 用户点名了 `styles.json` 的 id 或平台关键词：用该条 `style_lock` 原文。
- 用户没点名：按本任务的场景参考图写一段 `style_lock`（优先成片 / 模特图，没有则用成衣图背景），锁光线、色温、背景逻辑；服装颜色仍以成衣为准。

多图任务在出计划前锁定风格，整套一字不差。

从参考图写锁时必填：

1. 视觉方向（棚拍 / 室内实景 / 窗光 / 室外，以参考图为准）
2. 色板：背景来自参考图、服装以成衣为准、文字色、最多一个强调色（写 hex）
3. 冷暖调：warm / cool / neutral，全套一致
4. 光线：主光方向与软硬，抄参考图
5. 背景逻辑：同一房间 / 同一室外 / 无缝棚拍，抄参考图
6. 字体（若图内有字）：一种无衬线，不混用手写或衬线
7. 产品尺度：服装在画面中的大致占比
