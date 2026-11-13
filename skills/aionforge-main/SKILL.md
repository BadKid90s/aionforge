---
name: aionforge-main
description: >
  阶段 3 模特锁脸换衣与主图生成：按「思考 → 事实锁定 → 生成 → 检查」四步闭环，
  保留模特参考图的原脸五官与眼神，将阶段 2 合成好的正面/背面 T 恤实拍商品图（bg_white）穿到模特身上；
  先生成锚点主图，再派生多个机位与姿势（含背面回眸展示背面印花与正面展示左胸小标）。
  用户说根据模特图生成主图、把 T 恤穿到模特身上、保留模特的脸、多姿势主图时使用。
  Use when the user runs /aionforge-main.
---

# 阶段 3：模特锁脸换衣与多姿势主图（main）

本流程将阶段 2 通过质检的 T 恤实拍合成图（`bg_white` 正面与背面）穿到指定模特身上：**锁五官与眼神、锁 T 恤版型与印花、锁场景光影**，先出锚点主图（`hero`），再派生多姿势主图。

未加载入口时先读 `../aionforge/SKILL.md`。工具只按名称引用，参数见工具卡；本文件不写命令。Prompt 模板见 [tryon.md](../aionforge/references/prompts/tryon.md) 与 [vary.md](../aionforge/references/prompts/vary.md)。

## 输入与输出

| 方向 | 内容 | 说明 |
| --- | --- | --- |
| **输入** | 正面合成商品图 `bg_white`（`garment`）、背面合成商品图 `bg_white_back`（`garment_back`，有背面印花时必填）、模特参考图（`model`）、透明印花（`print`，防糊字辅助） | 未生成 `bg_white` 时必须先跑 `aionforge-product` |
| **输出文件** | 锚点主图 `main/<product>-<color>-hero.png`、多姿势主图 `main/<product>-<color>-<pose>.png` | 默认输出所有已合成颜色；用户点名某色则只跑该色 |
| **输出事实** | `facts.model`、`colors[].hero`、`colors[].anchor`、`canonical.anchor` | 供阶段 4 详情图复用同一模特形象 |

---

## 四步闭环执行流程

### 第一步：思考（Think —— 解析模特特征、旧衣擦除项与正背面姿势规划）

1. **解析模特与环境特征**：
   - 仔细观察模特图，提取：脸型、五官比例、眼型、瞳色、双眼皮、眼神光位置、发型发色、肤色（若模特图是手机挡脸对镜自拍，记录遮挡物位置，后续保持挡脸不强行补全五官）。
   - 提取模特图原有的下装（牛仔裤/休闲裤/半裙）、鞋包配饰、房间陈设与主光方向色温。
2. **识别模特原上衣擦除清单**：
   - 找出模特原身穿的上衣与目标 T 恤不同的结构（如旧衣领型、长袖、帽衫抽绳、口袋、旧图案），列入 Prompt 的「必须移除清单」，防止旧衣残留。
3. **正反面印花与姿势联动思考**：
   - **只有正面印花**：从 [shots-womenswear.md](../aionforge/references/shots-womenswear.md) 与 `catalog/looks.json` 挑选正面/微侧姿势套餐（如 `studio`、`mirror`、`outdoor`、`cafe`、`walk`）。
   - **背面主印花 + 左胸核心小标**：必须同时规划**正面姿势**（展示左胸精致小图标与正面上身版型）和**第三人称纯背面 / 微侧背姿势**（用 `garment_back` 重点展示后背大印花；**严禁出现“拿手机回头自拍后背”的画面**）。

### 第二步：事实锁定（Lock —— 锁定 `facts.model` 与主图拍摄计划）

1. 将模特五官、发型、下装、光线及 `uncertain` 写入 `facts.model`。
2. 锁定主图生成计划：
   - **第 1 张（锚点 `hero`）**：复刻模特原图姿势、机位与场景，仅将上衣整件替换为正面 `bg_white`。
   - **后续派生姿势**：明确每张姿势的 `shot-id`、参考图角色组合（正面姿势传 `source=hero` + `garment=正面bg_white`；背面/回眸姿势传 `source=hero` + `garment_back=背面bg_white`；含文字印花时加传 `print=透明印花` 辅助核对字形）。

### 第三步：生成（Generate —— 先出锚点，再派生多姿势）

1. **生成各颜色锚点主图（`hero`）**：
   - 按 [tryon.md](../aionforge/references/prompts/tryon.md) 编写 `<product_dir>/prompts/main/<product>-<color>-hero.txt`，写死 T 恤领口、袖口、下摆、底色、正面印花/左胸小标位置与文字，以及 6 位 Hex 色号。
   - 调用 [prompt check](../aionforge/references/tools/prompt-check.md) 做静态检查（严禁出现「图1/图2」序号，一律用「成衣图/模特图」角色名）。
   - 调用 [generate](../aionforge/references/tools/generate.md) 生成 `main/<product>-<color>-hero.png`，先跑第四步质检；**只有锚点通过质检后，才能继续派生其余姿势**。
2. **从锚点派生多机位/多姿势主图**：
   - 按 [vary.md](../aionforge/references/prompts/vary.md) 与 `looks.json` 对应 shot 编写每张姿势的 Prompt，强调「五官眼神锁定同一人，但头、颈、下颌、视线必须随本张身体动作自然转动」。
   - 背面展示镜头在 Prompt 中明确写死：「本张为第三人称纯背面/微侧背（165°–180°）实拍视角直接展示后背，后背图案以背面成衣图为准，只出现背面主印花，严禁把左胸小图标画到后背；长发拨至肩前或扎起。若锚点为对镜自拍，背面图必须去掉手机与镜框，双手自然垂放或插兜，严禁出现拿手机回头自拍或扭头看镜头的反人体工学动作」。
   - 逐张跑 [prompt check](../aionforge/references/tools/prompt-check.md) 后调用 [generate](../aionforge/references/tools/generate.md)。

### 第四步：检查（Verify —— 客观校验与锁脸/锁衣视觉质检）

1. **客观检查**：调用 [verify](../aionforge/references/tools/verify.md) 校验图片尺寸与目标画幅比例（如 `1:1` 或 `3:4`）。
2. **看图质检清单**：
   - **身份与头颈自然度**：五官、眼型、眼神光与原模特为同一人；侧身、行走、背面视角时头颈转向自然，无「后背贴正脸」或「拿手机回头后背自拍」的违和/反人体工学画面。
   - **T 恤与印花 100% 还原**：T 恤颜色、领口、袖长、宽松度与 `bg_white` 完全一致，无模特旧衣残留；正面左胸小标与背面大印花位置、大小、颜色（含阶段 2 适配后的颜色）准确无误，正背面绝不串位。
   - **画幅饱满**：画面铺满，无白边、黑边或 letterbox。
3. **回写交接**：将通过质检的锚点图写入 `colors[].hero` / `anchor` 与 `canonical.anchor`，交接给 `aionforge-detail` 生成详情图。

---

## 失败路由

| 现象 | 处置 |
| --- | --- |
| 五官漂移或眼神改变 | 在 Prompt【主体】细化眼型、瞳色、双眼皮与脸型特征，同一名称重跑一次 |
| 身体转了但脸还死板正对镜头 | 在 Prompt 强调「头颈随身体转向，侧身看 3/4 脸，背面看后脑或自然侧后轮廓，禁止正脸贴背」 |
| 背面图出现持手机回头自拍或镜框 | 改用第三人称纯背面/微侧背视角（165°–180°），在 Prompt 明确去掉手机与镜面、双手自然垂放、严禁回头自拍后重跑 |
| 背面图出现了正面左胸小标 | 检查是否误传了正面 `garment`，改为传入 `garment_back` 并在约束中禁止左胸徽章出现在背部 |
| 换姿势后印花文字变糊 | 额外传入透明印花作为 `print` 角色参考，写明「核对图案形状与逐字写法」 |
| 模特旧上衣结构残留 | 将残留部位（如帽衫领、旧袖口）明确加入 Prompt 的「必须去掉」列表重跑 |
