# 商品事实 `facts.json`

每个 logo + 款式一份，放在 `output/<logo>/.forge/products/<product>/facts.json`。它是整套图的唯一真相源：只写图上可见的内容；看不清的字段留空并列入 `uncertain`。禁止编造品牌、面料成分百分比、质检认证或销量数据。

- `logo` 是要印在衣服上的**图案 / 设计名**，不是品牌店名；从图案主标题、品牌署名或文件名推断，素材站水印（如「千图网」）不是 logo 名。
- `product` 是**衣服款式**，如 `short`（短袖）、`long`（长袖）、`tee`、`hoodie`；同一个 logo 可以套多个款式。
- 颜色名可以用英文（`black` / `white`）或素材里的中文色名（`黑` / `浅灰`）。

写完后的用户核对见入口 Skill「标准流程」第 4 步。用户确认前不要写计划、不要出图。

## 完整结构

```json
{
  "schema_version": 2,
  "logo": "锁定目标",
  "product": "short",
  "product_name": "短袖 T 恤",
  "category": "T恤",
  "garment_position": "top",
  "input_image_type": "flat_lay|hanging|model",
  "visual_features": {
    "silhouette": "宽松直筒",
    "length": "常规款，盖过腰线",
    "neckline": "圆领",
    "sleeve": "短袖",
    "cuff": "平口",
    "hem": "直下摆",
    "closure": "无",
    "pockets": "无",
    "waist_hip": "直筒"
  },
  "colors": [
    {
      "name": "black",
      "hex": "#1A1A1A",
      "source": "refs/blank-black.png",
      "bg_white": "bg_white/short-black.png",
      "hero": "main/short-black-hero.png",
      "anchor": "main/short-black-hero.png",
      "status": "approved"
    },
    {
      "name": "白",
      "hex": "#F7F7F5",
      "source": "refs/blank-white.png",
      "bg_white": "bg_white/short-白.png",
      "hero": "",
      "anchor": "",
      "status": "pending"
    }
  ],
  "materials_visible": ["纯棉平纹，表面哑光"],
  "print": {
    "has_print": true,
    "placement": "胸前正中",
    "text_exact": "锁定目标",
    "technique": "胶印"
  },
  "selling_points": [
    {
      "type": "pattern",
      "title": "趣味目标图案",
      "description": "蓝橙撞色，胸前视觉焦点",
      "visual_keywords": ["目标图案", "蓝橙配色", "胸前胶印"]
    }
  ],
  "target_scenes": ["日常通勤", "周末出街"],
  "style_lock": "5500K 柔和棚光，主背景 #F7F5F2，次背景 #EFECE6",
  "conversion_driver": "pattern",
  "model": {
    "ref": "refs/model.png",
    "face": "鹅蛋脸，鼻梁挺直，唇形偏薄",
    "eyes": "杏眼，深棕瞳，双眼皮，眼神光在左上",
    "hair": "黑色长直发，中分，过肩",
    "skin": "暖白皮，真实皮肤纹理",
    "bottom": "浅蓝直筒牛仔裤",
    "accessories": "细链小包",
    "room_light": "左侧窗光，4500K，暖白墙",
    "uncertain": []
  },
  "canonical": {
    "garment": "bg_white/short-black.png",
    "anchor": "main/short-black-hero.png"
  },
  "uncertain": ["后背是否有同款图案"]
}
```

## 字段规则

1. **`garment_position`**：`top`（上衣）、`bottom`（下装）、`full_body`（连衣裙 / 连体裤）、`set`（套装）。上装没有模特参考锁定下装时，自动搭配低饱和基础款下装；下装自动搭配纯色修身基础上衣；连衣裙 / 套装不额外加搭。
2. **`colors[]`**：用户给几张空白成衣图就写几个颜色。`name` 用英文短名或素材里的中文色名，`hex` 写主色，`source` 写该色空白成衣图，`bg_white` / `hero` / `anchor` 由工作流回写，`status` 用 `pending|approved|failed`。默认所有颜色都出；用户点名只出一个颜色时，只跑该色。
3. **`print`**：`has_print` 决定是否走 logo 合成与是否需要 `requires: ["print"]` 的姿势。`text_exact` 必须逐字来自图案稿，含大小写与标点，不准改写；`placement` 写具体位置（胸前正中 / 左胸上方 / 后背肩胛骨之间 / 下摆左侧）。图案稿上的素材站水印不是图案内容，不得进入成品；源图带水印时优先换有授权的无水印文件。
4. **`selling_points[].visual_keywords`**：每个卖点提炼 1–3 个具体可见部位词（如 `["目标图案", "蓝橙配色", "胸前胶印"]`），供详情信息图的放大镜气泡或标注线直接引用。
5. **`conversion_driver`**：`visual`（颜值与廓形驱动）、`pain_point`（版型 / 功能驱动）、`craft`（面料 / 重工驱动）、`pattern`（图案 / 印花驱动）。详情图按它选板式。
6. **`model`**：只有含模特的 main / detail 需要。记录五官、眼型、瞳色、双眼皮、眼神光、发型发色、肤色、下装、鞋包、房间光线；看不清的脸列入 `uncertain`，不要默默生成五官。
7. **`canonical.garment`**：bg_white 通过质检后写入，后续 main / sku / detail 一律用它当 `garment`，不再用原始空白成衣图。`canonical.anchor` 写主色 main 锚点，SKU 和带模特的详情优先用它当 `source`。
8. **`uncertain`**：原图未展示的结构（后背、内里、领口内侧、下摆内侧等）。Prompt 里明确要求这些部位不要臆造。

## 参考资产角色

| `--ref` 角色名 | 语义 | 允许借用 | 隔离禁区 |
| --- | --- | --- | --- |
| `garment` / `garment_back` | 商品身份 | 版型、领口、肩线、袖型、袖口、下摆、衣长、面料、颜色、印花与文字 | 不继承挂拍衣架、吊牌、杂乱背景或临时折痕 |
| `model` | 人物身份 | 五官比例、眼型、瞳色、双眼皮、眼神光、发型发色、肤色、下装与房间 | 原上衣整件作废；头部朝向随本张姿势转 |
| `print` | 图案身份 | 平面 logo 的几何形状、颜色、逐字文本与相对比例 | 不改变成衣版型与面料颜色；不带素材站水印 |
| `source` | 连续性成片 / 母版 | 已通过成片的人物、穿好的成衣、房间道具与光线；SKU 里锁构图与姿势 | 裂变只改机位、景别与身体姿势；SKU 只换衣服颜色 |
| `pose` | 姿势参考 | 身体姿态、手脚、头朝向 | 五官跟模特图或成片，衣服跟成衣图 |

用画面内容指代参考图，不要写「图1 / 图2」。
