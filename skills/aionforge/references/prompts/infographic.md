# 电商卖点信息图与拼图 Prompt 模板（`infographic`）

用于 `pdp` 工作流中的核心卖点副图（`main-selling-point`）、详情页信息图（`detail-infographic`）、多角度拼图（`detail-three-angle`）和一衣多穿多场景分屏（`detail-multi-scene`）。

写入 `work/prompts/<name>.txt`，按目标平台从 `references/typography.md`（及 `references/catalog/typography.json`）选取排版美学与配色，再调用 `forge generate`：

```bash
forge generate --job-dir <run_dir> --prompt-file <run_dir>/work/prompts/<name>.txt \
  --ref garment=<成衣> --name <name> --ratio 3:4 --json
```

若本张信息图内需要已确认的真人模特上身形象，同时传入 `--ref source=<已通过的 main-hero.png> --ref garment=<成衣>`。

---

## 板式 ①：放大镜气泡（`magnifier` — 适合面料纹理、蕾丝刺绣、领袖局部工艺）

```
# Role: 女装电商视觉信息图设计师（放大镜局部特写板式）

E-commerce womenswear feature infographic on [主背景或副背景 Hex，如 #F7F5F2 / #EFECE6] background.

## Campaign Style Lock
（粘贴 facts.style_lock 原文）

## 参考图角色（用画面内容区分，不要用先后顺序猜测）
- 成衣图（文件名 garment）：整件衣服版型、领口、袖口、下摆、面料、颜色与印花的唯一标准。
- 成片参考图（文件名 source，若有）：保持同一模特身份与穿着效果。

## 画面构图与比例（Magnifier Callout Layout）
- 主体居中偏左或居中悬浮展示，占画面 45–50%，留白至少 45%。
- 画面边缘排布 3 个精致圆形放大镜气泡（circular magnifying glass callout insets），用 1px 极细指示线（色号 [强调色 Hex]）指向成衣对应部位，不能遮挡胸前主印花或人脸：
  1. 气泡 1（左上）：微距放大展示 [visual_keywords 1，如领口交叉细绑带与包边走线]
  2. 气泡 2（右上）：微距放大展示 [visual_keywords 2，如面料织纹与亲肤垂坠光泽]
  3. 气泡 3（右下）：微距放大展示 [visual_keywords 3，如袖口/下摆荷叶边层次工艺]

## 服装锁定（来自 facts.json）
- 品类与版型：
- 面料颜色与质感：
- 领口 / 袖口 / 下摆：
- 印花与文字（若有，逐字还原，只出现一次）：
- 未展示部位（uncertain）按同色简洁素面处理，禁止臆造装饰。

## 图内文字排版（VISIBLE_TEXT_BLOCK）
- 平台排版美学：（粘贴对应 typography.json 的 prompt 片段）
- 顶部主标题（居中或左上，28–36pt，字色 [文字 Hex]）：「[主标题，≤12字]」
- 气泡 1 标签（14–16pt）：「[卖点1短词，≤6字]」
- 气泡 2 标签（14–16pt）：「[卖点2短词，≤6字]」
- 气泡 3 标签（14–16pt）：「[卖点3短词，≤6字]」
- 所有文字清晰锐利、无错字重影，全部落在留白区或胶囊签内，严禁压在领口、袖口或印花图案上。

## 负面约束（Negative Constraints）
不要添加：红黄爆炸贴纸、粗黑描边字、倾斜艺术字、假 Logo、水印、二维码、伪造质检证书、大段密集小字、白边或黑边。只输出一张完整信息图。
```

---

## 板式 ②：左衣右签·信息图标列表（`icon-list` — 适合防晒、透气、弹力、高支棉功能卖点）

```
# Role: 女装电商视觉信息图设计师（双栏胶囊列表板式）

E-commerce womenswear benefits infographic screen on [背景 Hex，如 #F7F5F2] background.

## Campaign Style Lock
（粘贴 facts.style_lock 原文）

## 参考图角色（用画面内容区分，不要用先后顺序猜测）
- 成衣图（文件名 garment）：衣服版型、颜色、领口、袖口、下摆与印花的唯一标准。

## 画面构图与比例（Two-Column Icon List Layout）
- 干净双栏网格布局（clean two-column layout），整体留白至少 48%。
- 左栏（占画面 45%）：完整展示成衣正面或 45° 立体廓形，边缘干净，衣摆自然垂坠。
- 右栏（占画面 40%）：顶部为主标题，下方纵向等距排列 3 个卖点模块（极简 1.5px 细线图标 + 圆角柔雾胶囊标签）。

## 服装锁定（来自 facts.json）
- 品类与版型：
- 面料颜色与质感：
- 领口 / 袖口 / 下摆 / 印花：

## 图内文字排版（VISIBLE_TEXT_BLOCK）
- 平台排版美学：（粘贴对应 typography.json 的 prompt 片段）
- 右栏顶部主标题（28–36pt，字色 [文字 Hex]）：「[核心承诺主标题，≤12字]」
- 右栏卖点 1（配细线图标）：「[卖点1标题，≤6字]」
- 右栏卖点 2（配细线图标）：「[卖点2标题，≤6字]」
- 右栏卖点 3（配细线图标）：「[卖点3标题，≤6字]」
- 文字与左侧服装保持安全间距，严禁遮挡衣服轮廓。

## 负面约束（Negative Constraints）
不要添加：红黄促销爆炸贴、粗黑描边、杂乱道具、手部遮挡、水印、假 Logo、额外乱码小字。
```

---

## 板式 ③：杂志风指示线标注（`annotation` — 适合连衣裙、法式/韩系剪裁、显瘦版型拆解）

```
# Role: 女装电商视觉信息图设计师（画册级标注线板式）

Editorial womenswear design-anatomy infographic on [背景 Hex，如 #F5EFE6] background.

## Campaign Style Lock
（粘贴 facts.style_lock 原文）

## 参考图角色（用画面内容区分，不要用先后顺序猜测）
- 成衣图（文件名 garment）：衣服版型、领口、袖口、腰线、下摆与印花的唯一标准。

## 画面构图与比例（Editorial Pointer Annotation Layout）
- 服装（或穿好成衣的模特）居中展示，占画面 50%，四周留白至少 45%。
- 从成衣的 3 个关键剪裁部位引出水平 1px 极细实线（色号 [强调色 Hex]，起点带小圆点），指向左右两侧背景留白区的短标签：
  1. 指示线 1（指向领口/肩线）→ 展示 [visual_keywords 1]
  2. 指示线 2（指向高腰线/收腰剪裁）→ 展示 [visual_keywords 2]
  3. 指示线 3（指向下摆/开衩/袖口）→ 展示 [visual_keywords 3]

## 服装锁定（来自 facts.json）
- 品类与版型：
- 面料颜色与质感：
- 领口 / 袖口 / 下摆 / 印花：

## 图内文字排版（VISIBLE_TEXT_BLOCK）
- 平台排版美学：（粘贴对应 typography.json 的 prompt 片段）
- 左上角主标题（28–36pt，字色 [文字 Hex]）：「[版型主张标题，≤10字]」
- 指示线 1 终点标签：「[部位卖点1，≤6字]」
- 指示线 2 终点标签：「[部位卖点2，≤6字]」
- 指示线 3 终点标签：「[部位卖点3，≤6字]」

## 负面约束（Negative Constraints）
不要添加：杂乱箭头、促销贴纸、多余人物、水印、假 Logo、密集长句。
```

---

## 板式 ④：60:40 非对称主次分屏（`asymmetric` — 同屏兼顾全身廓形与两处微距细节）

```
# Role: 女装电商视觉信息图设计师（60:40 非对称主次分屏）

Asymmetric split-grid womenswear editorial screen on [背景 Hex] background.

## Campaign Style Lock
（粘贴 facts.style_lock 原文）

## 参考图角色（用画面内容区分，不要用先后顺序猜测）
- 成衣图（文件名 garment）：衣服版型、颜色、面料与细节的唯一标准。
- 成片参考图（文件名 source，若有）：左侧主视觉保持同一模特五官与全身穿搭。

## 画面构图与比例（60/40 Asymmetric Split Layout）
- 画面由 2px 干净细线（色号 #FFFFFF 或 #E5E5E5）分为左右非对称两栏：
  - **左侧主栏（占宽度 60%）**：全身或七分主视觉，完整展示成衣上身廓形与垂坠比例。
  - **右侧副栏（占宽度 40%，上下等分 2 格）**：
    - 右上格：领口 / 肩袖剪裁或胸前印花近景特写
    - 右下格：面料纹理或下摆走线微距特写

## 服装锁定（来自 facts.json）
- 左栏与右侧两格必须是完全同一件成衣：颜色、面料、领口、袖口、下摆、印花严格一致。

## 图内文字排版（VISIBLE_TEXT_BLOCK）
- 平台排版美学：（粘贴对应 typography.json 的 prompt 片段）
- 左栏顶部或底部留白区简短主标题：「[主标题，≤10字]」
- 右上格角标短签：「[细节1，≤5字]」
- 右下格角标短签：「[细节2，≤5字]」

## 负面约束（Negative Constraints）
不要出现两件不同颜色或不同领型的衣服；不要遮挡人脸和印花；无水印、无假 Logo。
```

---

## 补充板式 A：三角度同框拼图（`detail-three-angle`：正面 / 微侧 / 背面）

```
# Role: 女装三角度同框商拍师

Three-equal-panel vertical collage showing the exact same womenswear garment from Front (正面 0°), Three-Quarter (微侧 45°), and Back (背面) views on [背景 Hex] studio background.

## Campaign Style Lock
（粘贴 facts.style_lock 原文）

## 参考图角色
- 成衣图（文件名 garment，若有背面图则同时参考 garment_back）：整件衣服颜色、版型、长度的唯一标准。
- 成片参考图（文件名 source，若有）：三栏必须为同一位女性模特，五官、发型、肤色、下装与鞋完全一致。

## 画面构图（Three-Angle 1:1:1 Split：正面 / 微侧 / 背面）
- 画面水平均分为 3 个等宽竖栏（各占 33.3% 宽度），栏间用 2px 干净细白线分隔，全身或七分完整入画，禁止截断头部：
  - **左栏（正面 0°）**：自然站立正面，展示前领、胸前设计与衣长。
  - **中栏（微侧 45°）**：四分之三微侧站姿，展示胸前设计侧透视、肩袖与侧身剪裁。
  - **右栏（背面）**：背对镜头自然站立（只展示后脑长发与后背，严禁扭头露出正脸！），展示后领、肩线与后背下摆（后背按 garment_back 保持同色素面，禁止把胸前印花画到后背）。

## 负面约束
严禁在右栏背面身体上扭头露出正脸；三栏衣服颜色、衣长、袖长必须完全一致；无多余文字贴纸、无水印、无边框留白。
```

---

## 补充板式 B：一衣多穿·动态多场景分屏（`detail-multi-scene`）

> **注意**：场景必须从 `facts.target_scenes` 动态读取（如通勤办公 vs 周末咖啡馆、海边度假 vs 日常逛街），**严禁写死与当前女装款式冲突的固定场景词**。

```
# Role: 女装一衣多穿多场景视觉师

Split-screen womenswear multi-scene lookbook showcasing the exact same garment across 2 (or 3) distinct real-life occasions from facts.target_scenes.

## Campaign Style Lock
（粘贴 facts.style_lock 原文）

## 参考图角色
- 成片参考图（文件名 source）：保持同一女性模特五官、眼神、发型。
- 成衣图（文件名 garment）：所有分屏中穿着的核心成衣必须 100% 相同（同款、同色、同领型、同印花）。

## 画面构图与动态场景（来自 facts.target_scenes）
- 画面用 2px 极细分割线分为左右等宽两栏（或三栏），每栏全身或七分入画：
  - **场景一（左栏 — [target_scenes[0] 名称]）**：环境为 [target_scenes[0] 具体光线与空间描述]，自然生活姿态。
  - **场景二（右栏 — [target_scenes[1] 名称]）**：环境为 [target_scenes[1] 具体光线与空间描述]，不同站姿或走姿。

## 图内文字排版（VISIBLE_TEXT_BLOCK）
- 顶部居中主标题（28–34pt）：「[一衣多穿主标题，如 一衣多穿·日常通勤皆宜]」
- 左栏底部短签：「[target_scenes[0]，≤6字]」
- 右栏底部短签：「[target_scenes[1]，≤6字]」

## 负面约束
禁止改变成衣款式或颜色；禁止把正面印花画错位置；无促销爆炸贴、无水印、无假 Logo。
```
