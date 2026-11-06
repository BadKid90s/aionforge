# 工作流：竞品参考图反推与视觉迁移（deconstruct）

当用户给出一张或一组优秀的竞品主图、详情单屏或爆款参考图，说「照这个感觉做」「参考这张的排版/光影出我的衣服」「反推这张图并迁移到我的商品上」时使用。出图只调用 `forge generate`。

- Prompt 骨架：`references/prompts/deconstruct.md`
- 视觉资产解耦协议：`references/analysis.md`「三轴视觉参考资产协议」与「长图隔离红线」
- 风格锁定：`references/style-lock.md`
- 平台字体与排版：`references/typography.md` + `references/catalog/typography.json`

核心原则：**借机制，不借身份。** 竞品参考图只贡献版式骨架（L）、光影色调（S）和排版层级（T）；商品的版型、颜色、面料、印花文字、卖点主张 100% 来自用户的成衣图和 `facts.json`。

## 何时用

用户给了竞品图 / 优秀案例图，要求照着它的构图、色调、信息图板式或氛围，给自己的女装商品出 1 张或 1 组同级别新图。

没有竞品参考图、只想把同一张成片换机位 → `vary`。从零规划整套主图 + 详情 → `pdp`。

## 输入

| 素材 | 角色 | 必填 |
| --- | --- | --- |
| 用户成衣图（正面 / 背面） | `garment` / `garment_back` | 是 |
| 竞品或标杆参考图 | `layout`（版式）或 `style`（光影色调） | 是 |
| 指定模特图（可选） | `model` | 否 |
| 出图模式（1:1 迁移 vs 4 向裂变） | 计划 | 否（默认 1:1 迁移，或用户指定裂变张数） |

> **长图隔离红线（`LONG_PAGE`）**：先检查竞品参考图的宽高比。若 `H / W >= 2.2`（竖长条详情页拼接图），在 `facts.json` 标记 `input_image_type: "LONG_PAGE"`——**只允许看图提取文字版式机制写入 Prompt，严禁将该长图传给 `--ref`**，否则生成模型会把多屏拼图边框画进单张图里。单屏参考图（`SINGLE_POSTER`）才可作为 `--ref layout=` 或 `--ref style=` 传入。

## 反推五维视觉机制（写入 `work/deconstruct_notes.md` 或 `plan.json`）

看竞品参考图，拆解以下 5 个可迁移机制：

1. **构图与机位（Camera & Framing）**：景别（全身 / 七分 / 半身 / 局部微距）、机位角度（平视 / 10° 微俯 / 15° 微仰）、人物或服装在画面中的占比（`55%–85%`）及重心位置（居中 / 三分法偏左 / 偏右）。
2. **留白与网格（Layout & Whitespace）**：留白占比（`20%–45%`）、留白方位（左 / 右 / 上 / 对角）、信息图组件结构（放大镜圆窗 / 图标列表 / 细线批注 / 60:40 分栏）。
3. **光影与色温（Lighting & Palette）**：主光方向与软硬、背景主色与次背景色的 6 位 Hex 色值（如 `#F7F5F2`）、整体色温倾向。
4. **字体与标签美学（Typography & Badges）**：标题与正文字重对比、字色 Hex、胶囊角标或分割线样式（若用户指定了目标平台，优先对齐 `references/catalog/typography.json` 对应平台规范，例如拼多多自动升级为莫兰迪圆角胶囊轻杂志风）。
5. **转化钩子类型（Conversion Hook）**：这张图靠什么打动买家？（版型显瘦对比 / 面料微距触感 / 穿搭氛围代入 / 一衣多穿高性价比）。

## 两种生成模式

### 模式 A：1:1 版式与氛围迁移（单张）
复刻参考图的构图网格、留白方位、光影色温和信息层级，但将画面主体 100% 替换为用户成衣（若含模特则用指定 `model` 或契合风格的亚洲女模），文案替换为 `facts.json` 中的真实卖点。

### 模式 B：4 向同源裂变（4 张组图）
基于同一张优秀参考图的视觉语言，一次性衍生 4 个互补方向的生图方案：
- `deconstruct-01-layout`：**忠实版式迁移**（复刻原参考图的构图比例、留白方位与光影，替换成衣与卖点）
- `deconstruct-02-angle`：**构图景别升级**（保持原图光影色板，切换机位景别，如全身改半身微侧或 15° 仰拍显腿长）
- `deconstruct-03-scene`：**场景叙事代入**（提取原图色调与穿搭气质，延展到高契合度的真实生活场景）
- `deconstruct-04-infographic`：**卖点信息图设计**（提取原图的排版美学，结合成衣核心工艺生成带 `VISIBLE_TEXT_BLOCK` 的微距/批注卖点图）

## 步骤

1. `forge doctor --json`。
2. `forge job init --workflow deconstruct --slug <短名> --json`。
3. 看用户成衣图写 `facts.json`（含 `garment_position`、`conversion_driver`、`selling_points`）。
4. 看竞品参考图，判断 `SINGLE_POSTER` 还是 `LONG_PAGE`，拆解五维视觉机制。
5. 写入 `plan.json`，按 `SKILL.md`「生图前确认」向用户确认缺口（如 1 张还是 4 张、是否印字、目标平台）。
6. 按 `references/prompts/deconstruct.md` 逐张编写 `work/prompts/<name>.txt`，显式列出 **借用机制** 与 **隔离禁区**。
7. 调用 `forge generate`：

```bash
# 单屏参考图（SINGLE_POSTER）：可传 --ref layout= 或 --ref style=
forge generate --job-dir <run_dir> \
  --prompt-file <run_dir>/work/prompts/deconstruct-01-layout.txt \
  --ref garment=<用户成衣> --ref layout=<单屏参考图> \
  --name deconstruct-01-layout --ratio 3:4 --json

# 长图参考（LONG_PAGE）：只用反推出来的文字描述，不传参考图进 --ref
forge generate --job-dir <run_dir> \
  --prompt-file <run_dir>/work/prompts/deconstruct-01-layout.txt \
  --ref garment=<用户成衣> \
  --name deconstruct-01-layout --ratio 3:4 --json
```

8. 逐张质检：
   - 衣服 100% 是用户成衣图那一件，绝未混入竞品图上的领型、颜色、花纹或配饰。
   - 画面中无竞品品牌名、Logo 或竞品原图残留文字。
   - 构图比例、留白呼吸感、光影色调成功复现参考图的高级感。
   - 若含中文文案，放大 200% 检查笔画清晰无乱码。
