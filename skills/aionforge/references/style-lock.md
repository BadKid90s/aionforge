# Campaign Style Lock 与生图数字化铁律

风格定义在 `references/catalog/styles.json`，字段见 `references/catalog/schemas/style.schema.json`。平台字体与排版美学独立定义在 `references/typography.md` 与 `references/catalog/typography.json`。

选定后把 `style_lock` **一字不差**原样放进每一张 Prompt 的第一段，不要每张重新配色、换同义词或换光线。

- 用户点名了 `styles.json` 的 id 或平台/风格关键词：用该条 `style_lock` 原文。
- 用户没点名：按本任务的场景参考图写一段 `style_lock`（优先成片 / 模特图，没有则用成衣图背景），锁光线、色温、背景逻辑；服装颜色仍以成衣为准。

## 从参考图写锁时必填 9 项

1. **视觉方向**：棚拍 / 室内实景 / 窗光 / 室外街拍 / 杂志大片，以参考图为准。
2. **固定色板（强制写 6 位 Hex 码）**：禁止只写「白底」「米色」「金色」等形容词（模型会把「白底」画成淡灰、「金色」画出 8 种色偏）。必须写明主背景 Hex（如 `#FFFFFF`、`#F7F5F2`）、副背景 `background_alt` Hex（如 `#EFECE6`）、文字色 Hex（如 `#2D2D2D`）和最多 1 个强调色 Hex。
3. **冷暖调与色温**：`warm` / `cool` / `neutral`，场景图写明色温（如 `4500K` 暖窗光、`5500K` 标准棚光），全套一致。
4. **光线系统**：主光方向、软硬、阴影浓度与反光质感，抄参考图。
5. **背景系统与多图节奏**：同一空间逻辑或无缝棚拍。连续 6–9 张详情图禁止背景死板同色导致视觉疲劳，可在主背景 `background` 与同色系副背景 `background_alt` 之间交替。
6. **字体与排版系统（若图内有字）**：按 `references/typography.md` 匹配对应平台的 `typography_id`，整套最多 2 种字体，禁止混用手写、卡通或第三种字体。
7. **数字化占比与显式留白**：
   - 正面/背面主图：服装占 `75–85%`，留白 `≥ 20%`
   - 卖点副图 / 详情信息图：服装或特写占 `40–55%`，**必须显式声明 `留白至少 45%`**（不写留白，模型一定把画面填满）
   - 场景氛围图：人物与服装占 `60–75%`，环境留白 `≥ 25%`
8. **平台安全预留区（主图按需声明）**：国内电商（淘宝/拼多多/京东）主图若需防遮挡，写明 `左上角 200×100 像素区域留白（角标/Logo 区）` 或 `顶部中央 200×100 区域留空（平台价格叠加区）`。
9. **禁止漂移项（Negative Lock）**：结尾显式写 `no palette drift, no mixed fonts, no random backgrounds, no inconsistent lighting, no extra logos`。

## Anti-AI 真实感规则（种草 / 街拍 / 买家秀场景）

当风格选定为 `xhs-fresh`、`ugc-street`、`campus-youth` 或用户要求小红书/抖音种草、素人街拍、真实买家秀时，把对应条目的 `anti_ai_tips` 拼入 Prompt：

- 指定拍摄载体与色彩科学：如 `shot on iPhone 15 Pro`、`Kodak Portra 400 color feel`。
- 保留真实瑕疵与物理细节：真实皮肤毛孔、发丝微动（`natural hair flyaway`）、轻微环境生活痕迹、棉麻/针织自然折痕与织纹。
- 显式去 AI 声明：`NOT studio lighting, NOT retouched, NOT smoothed, NOT airbrushed`。
- 禁用典型 AI 塑料词：不用 `flawless`、`perfect`、`hyper-realistic`、`stunning`。
