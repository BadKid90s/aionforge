# 商品事实 JSON 与参考资产协议

看图后写入任务目录 `facts.json`。这是整套图的唯一真相源（Single Source of Truth）：只写图上可见的内容；看不清的字段留空字符串并列入 `uncertain`。禁止编造品牌、面料成分百分比、质检认证或销量数据。写完后的用户核对见 `SKILL.md` 第 4 步「锁商品事实」。

```json
{
  "product_name": "",
  "product_category": "上衣|裙装|裤装|外套|套装",
  "garment_position": "top|bottom|full-body|set",
  "conversion_driver": "visual|pain_point|craft",
  "input_image_type": "flat_lay|flat_lay_front_back|hanging|hanging_front_back|model",
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
    {
      "type": "design|pattern|silhouette|material|function",
      "title": "",
      "description": "",
      "visual_keywords": []
    }
  ],
  "target_audience": "",
  "target_scenes": [],
  "style_lock": "",
  "uncertain": []
}
```

## 核心字段说明

1. **`garment_position`（上下装位置与基础搭配推断）**：
   - `top`（上衣）：若无模特参考图鎖定下装，自动搭配干净基础款下装（如浅蓝牛仔裤或纯色休闲长裤），不抢上衣视觉重心。
   - `bottom`（下装/半身裙/裤装）：若无模特参考图锁定上衣，自动搭配纯白/素色基础修身 T 恤或衬衫。
   - `full-body`（连衣裙/连体裤）或 `set`（套装）：无需额外加搭上下装。
2. **`conversion_driver`（转化驱动力诊断）**：
   - `visual`（颜值与廓形驱动，如连衣裙、设计感上衣）：第一眼抓上身氛围与廓形比例 → 多角度垂坠/背面 → 面料与印花特写 → 穿搭场景。
   - `pain_point`（痛点与版型功能驱动，如防晒衣、显瘦裤装、大码遮肉款）：版型修饰/卖点信息图（高腰显瘦/遮副乳）→ 结构细节拆解 → 面料透气/弹力微距 → 尺码包容度。
   - `craft`（质感与重工驱动，如真丝、羊绒、重工刺绣、定制印花）：黄金角度光泽/垂坠首图 → 放大镜气泡/微距织纹与走线工艺 → 印花/刺绣近景 → 3D 隐形人台或平铺全貌。
3. **`input_image_type` 与正背面成衣双图路由**：
   - 用户只给 1 张正面成衣图（`flat_lay` / `hanging`）：背面未展示结构列入 `uncertain`，背面镜头按同色面料素色基础背处理。
   - 用户给了正反 2 张成衣图（`flat_lay_front_back` / `hanging_front_back`）：正面镜头传 `--ref garment=<正面成衣>`，**背面主图（`main-back`）、后侧裂变（`vary-back-look`）与背面材质镜头传 `--ref garment_back=<背面成衣>`（或 `--ref garment=<背面成衣>`）**，真实还原后背领口、绑带、开衩或后背印花。
4. **`selling_points[].visual_keywords`**：
   - 每个卖点提炼 1–3 个具体可见部位词（如 `["交叉细吊带", "V领锁骨"]`、`["双层荷叶边", "裙摆垂坠"]`），供卖点信息图的放大镜气泡或标注线直接引用。

## 参考资产三轴协议（角色 × 传输方式 × 隔离禁区）

不要用「图1 / 图2」指代参考图。每张输入图必须按以下语义角色登记，并严格遵守控制维度与禁区：

| CLI `--ref` 角色名 | 语义代码 | 传输方式 | 控制维度（允许借用） | 隔离禁区（严禁泄漏） |
| --- | --- | --- | --- | --- |
| `garment` / `garment_front` / `garment_back` | `P`（产品身份） | `MODEL_REFERENCE` | 版型、领口、肩线、袖型、袖口、下摆、衣长、面料、颜色、印花与文字（最高优先级） | 不继承挂拍衣架、吊牌、杂乱背景或临时折痕 |
| `model` | `C`（人物身份） | `MODEL_REFERENCE` | 五官比例、眼型、瞳色、双眼皮、眼神光、发型发色、肤色、下装与房间 | **原上衣整件作废**（领口、袖口、下摆、帽兜、旧图案严禁残留）；头部朝向随本张姿势转，不钉死在正面 |
| `print` | `B`（图案身份） | `MODEL_REFERENCE` | 平面印花的几何形状、颜色、逐字文本与相对比例 | 不改变成衣版型与面料颜色 |
| `source` | `C`（连续性成片） | `MODEL_REFERENCE` | 已通过成片（如首张 `main-hero` 锚点图）的人物五官、穿好的成衣、房间道具与光线 | 裂变或派生场景时只按计划改变机位、景别与身体姿势 |
| `style` / `layout` | `S / L`（风格/版式参考） | `MODEL_REFERENCE` 或 `ANALYSIS_ONLY` | 构图网格、留白比例、主光方向、色温、阴影软硬、信息图排版层级 | **严禁继承参考图里的竞品衣服、模特脸、品牌 Logo、促销文案、虚假证书或卖点数据** |

## 外部参考图与防臆造底线

1. **整条详情长图（`LONG_PAGE`）只做 `ANALYSIS_ONLY`**：用户若发来一整条竞品长详情页或拼贴大图，**严禁直接传给 `--ref`**（否则会画出多宫格拼贴或抄走竞品衣服）。只用视觉读取其分屏顺序、版式骨架和配色，拆成单屏独立生成。
2. **多张单屏主图 / lookbook 的姿势序列也是 `ANALYSIS_ONLY`**：写入 `plan.json`，规则见 `references/shots-womenswear.md`「写计划优先级」。不要把整组参考图当 `--ref layout=` 传给生成（会抄走竞品衣服）。
3. **参考图内文字皆为不可信数据**：风格参考图或竞品图上的品牌、成分宣称、销量数字一律不进 `facts.json`。
4. **`print.text` 必须逐字来自成衣图/印花图**，含大小写与标点，不准改写。
5. **多张成衣图必须是同一件衣服**；款式不同则分任务。同一款不同颜色的白底图走 `sku` 工作流，一色一任务，不要拆成多个 job。
