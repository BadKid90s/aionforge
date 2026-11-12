# 商品事实锁定契约 `facts.json`

每个 logo + 款式维护唯一一份 `facts.json`，存放在 `output/<logo>/.forge/products/<product>/facts.json`。
它是贯穿 **「印花准备 → 实拍调色合成 → 模特主图 → 详情图」** 四个阶段的**唯一真相源（Single Source of Truth）**：只记录图上可见的客观事实与经确认的计划，看不清的部位留空并列入 `uncertain`，严禁编造面料成分百分比、质检证书或虚假销量。

## 核心概念

- **`logo`**：印在 T 恤上的**图案 / 设计名称**（从图案主标题、设计署名或文件名推断；素材站水印绝不是 logo 名）。
- **`product`**：**衣服款式短名**，如 `short`（短袖 T 恤）、`long`（长袖 T 恤）、`tee`、`hoodie`（卫衣）。
- **事实锁定门槛**：在进入合成与生图前，必须将款式特征、颜色列表、印花正反面计划、左胸核心小标及撞色适配策略写入 `facts.json` 并展示给用户确认。

## 完整结构（schema_version 3）

```json
{
  "schema_version": 3,
  "logo": "锁定目标",
  "product": "short",
  "product_name": "圆领短袖 T 恤",
  "category": "T恤",
  "garment_position": "top",
  "input_image_type": "flat_lay",
  "visual_features": {
    "silhouette": "宽松落肩直筒",
    "length": "常规衣长，盖过腰线",
    "neckline": "经典罗纹圆领",
    "sleeve": "五分落肩短袖",
    "cuff": "平口双车线袖口",
    "hem": "直筒双车线下摆",
    "closure": "无",
    "pockets": "无",
    "waist_hip": "宽松直筒"
  },
  "colors": [
    {
      "name": "black",
      "hex": "#1A1A1A",
      "source": "refs/blank-black.png",
      "source_back": "refs/blank-black-back.png",
      "bg_white": "bg_white/short-black.png",
      "bg_white_back": "bg_white/short-black-back.png",
      "hero": "main/short-black-hero.png",
      "anchor": "main/short-black-hero.png",
      "color_adaptation": {
        "strategy": "white",
        "contrast_before": 1.05,
        "contrast_after": 4.8,
        "adapted_source": "refs/short-black-print-fit.png",
        "ink": "white"
      },
      "status": "approved"
    },
    {
      "name": "white",
      "hex": "#F5F5F5",
      "source": "refs/blank-white.png",
      "source_back": "refs/blank-white-back.png",
      "bg_white": "bg_white/short-white.png",
      "bg_white_back": "bg_white/short-white-back.png",
      "hero": "main/short-white-hero.png",
      "anchor": "main/short-white-hero.png",
      "color_adaptation": {
        "strategy": "multiply",
        "contrast_before": 5.2,
        "contrast_after": 5.2,
        "adapted_source": "refs/short-print.png",
        "ink": "multiply"
      },
      "status": "approved"
    }
  ],
  "materials_visible": ["纯棉平纹针织，哑光亲肤肌理"],
  "print": {
    "has_print": true,
    "source": "refs/short-print.png",
    "technique": "胶印",
    "text_exact": "锁定目标",
    "palette": ["#0B2A5B", "#1E88E5", "#F2A0A0"],
    "elements": [
      {
        "id": "core",
        "path": "refs/short-core.png",
        "role": "icon",
        "area": 12345,
        "touches_edge": false
      }
    ],
    "placements": [
      {
        "id": "back-main",
        "side": "back",
        "region": "back_center",
        "source": "refs/short-print.png",
        "x": 0.5,
        "y": 0.19,
        "width": 0.30,
        "max_height": 0.40,
        "anchor": "top",
        "ink": "auto",
        "text_exact": "锁定目标",
        "adaptations": {
          "black": {
            "source": "refs/short-black-print-fit.png",
            "ink": "white"
          },
          "white": {
            "source": "refs/short-print.png",
            "ink": "multiply"
          }
        }
      },
      {
        "id": "front-badge",
        "side": "front",
        "region": "left_chest",
        "source": "refs/short-core.png",
        "x": 0.61,
        "y": 0.29,
        "width": 0.09,
        "max_height": 0.11,
        "anchor": "center",
        "ink": "normal",
        "text_exact": ""
      }
    ],
    "analysis": {
      "front_score": 0.3,
      "back_score": 0.85,
      "reasons": ["多元素宽幅构图", "细节密度高", "含辅助小字适合背面大图展示"],
      "decided_by": "agent+user"
    },
    "color_adaptation": {
      "strategy": "white",
      "contrast_before": 1.05,
      "contrast_after": 4.8,
      "map": [{"from": "#0B2A5B", "to": "#FFFFFF"}],
      "warnings": []
    }
  },
  "selling_points": [
    {
      "type": "pattern",
      "title": "前胸小标·后背大印",
      "description": "正面左胸核心靶心徽章，背面大幅主题印花，正反呼应",
      "visual_keywords": ["左胸精致小标", "后背高清胶印", "双针罗纹领口"]
    }
  ],
  "target_scenes": ["日常街拍", "周末咖啡馆"],
  "style_lock": "5500K 柔和棚光，主背景 #F7F5F2，次背景 #EFECE6，文字色 #2D2D2D，强调色 #8C6A56",
  "conversion_driver": "pattern",
  "model": {
    "ref": "refs/model.png",
    "face": "鹅蛋脸，鼻梁挺直，自然淡妆",
    "eyes": "杏眼，深棕瞳，双眼皮，眼神光在左上",
    "hair": "黑色长直发，中分自然垂肩",
    "skin": "暖白皮，真实皮肤纹理",
    "bottom": "浅蓝宽松直筒牛仔裤",
    "accessories": "简约银色耳圈",
    "room_light": "左侧柔和自然窗光，4500K，暖白墙面",
    "uncertain": []
  },
  "canonical": {
    "garment": "bg_white/short-black.png",
    "garment_back": "bg_white/short-black-back.png",
    "anchor": "main/short-black-hero.png"
  },
  "uncertain": []
}
```

## 字段规范

1. **`colors[]`（按颜色管理实拍底图与撞色适配）**：
   - `source`：该颜色正面 T 恤实拍图路径；`source_back`：该颜色背面 T 恤实拍图路径（有背面印花时必填）。
   - `color_adaptation`：记录该颜色 T 恤专属的撞色适配策略（`strategy`）、适配前后 WCAG 对比度（`contrast_before` / `contrast_after`）、适配后的透明印花路径（`adapted_source`）及合成墨色（`ink`）。
   - `bg_white` / `bg_white_back` / `hero` / `anchor`：各阶段通过质检后回写的成品路径。
2. **`print.elements[]`（左胸核心元素记录）**：
   - 当主印花判定为背面印刷时，由 `extract-core-element` 提取核心元素写入 `refs/<product>-core.png`，供正面左胸小印花使用。
3. **`print.placements[]`（正反面合成计划）**：
   - 一条 placement 对应一次合成动作。
   - `side`：`front`（正面）或 `back`（背面）。
   - `region`：标准预设名，合成时自动绑定行业标准固定位置与尺寸（详见 [print/placement.md](../print/placement.md)）：
     - `left_chest`：左胸小标（8–12cm，正面图右侧 `x=0.61, y=0.29, width=0.09, max_height=0.11, anchor="center"`）
     - `chest_center`：胸前居中大图（28–32cm，领口下 7–9cm，`x=0.50, y=0.27, width=0.28, max_height=0.32, anchor="top"`）
     - `back_center`：全背印花（28–32cm × 35cm，后领下 2–5cm，`x=0.50, y=0.19, width=0.30, max_height=0.40, anchor="top"`）
     - `back_neck`：上背小标（5–8cm，后领下 3–5cm，`x=0.50, y=0.17, width=0.07, max_height=0.09, anchor="top"`）
     - `hem_left` / `hem_right`：下摆衣角标（5–8cm，下摆上 5cm，`x=0.66/0.34, y=0.84, width=0.065, max_height=0.08, anchor="bottom"`）
   - `adaptations`（可选）：按颜色名覆盖 `source`（指向该色专属适配印花）与 `ink`（`auto | multiply | normal | white`），配合 `composite --placement <id> --color <color>` 自动生效。
4. **`canonical`（跨阶段唯一真相源指针）**：
   - `garment` / `garment_back`：指向通过质检的正面 / 背面合成商品图，后续 `main` 与 `detail` 一律以它们为衣服标准。
   - `anchor`：指向通过质检的模特锚点主图，后续多姿势与模特详情图一律以它为人物标准。
5. **`uncertain`**：原图未展示的细节部位，在生图 Prompt 中明确约束禁止臆造。

参考图角色见 [reference-roles.md](reference-roles.md)，目录契约见 [workspace.md](workspace.md)。
