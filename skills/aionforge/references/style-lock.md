# 信息图 / 多图任务的风格锁定

模特展示图直接用 `catalog/looks.json` 该张 shot 的【风格】段，不要另写一套。

信息图、人台、需要 `facts.style_lock` 的图：色板从 `catalog/typography.json` 对应平台抄 6 位 Hex；没点名平台则跟参考图写。选定后一字不差贴进每一张，不要每张重新配色。组段顺序见 `references/prompts/formula.md`。

## 从参考图写锁时必填

1. **视觉方向**：棚拍 / 室内实景 / 窗光 / 室外街拍，以参考图为准。
2. **固定色板（6 位 Hex）**：主背景、副背景、文字色、最多 1 个强调色。禁止只写「白底」「米色」。
3. **色温**：如 `4500K` 暖窗光、`5500K` 标准棚光，全套一致。
4. **光线**：主光方向、软硬、阴影，抄参考图。
5. **背景节奏**：连续详情图可在 `background` 与 `background_alt` 之间交替。
6. **字体**：有字时按 `typography.md`，整套最多 2 种字体。
7. **占比与留白**：主图服装 75–85%、留白 ≥20%；信息图留白至少 45%。
8. **平台安全区**（国内主图按需）：左上或顶部中央约 200×100 留空给角标/价格。
9. **禁止漂移**：`no palette drift, no mixed fonts, no random backgrounds, no extra logos`。

种草 / 街拍 / 买家秀：写真实织物与皮肤微纹理，`NOT airbrushed`；不用 `flawless`、`hyper-realistic`。
