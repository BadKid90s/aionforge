# SKU 配色 Prompt

按 `references/prompts/formula.md` 组段。每张配色单独一份 `<product_dir>/prompts/sku/<product>-<color>.txt`。母版锁人与构图，本张配色白底锁衣服。只换上衣颜色，其余与母版一致。

母版优先用已通过的 `main/<product>-<color>-hero.png`；没有 main 时才用产品图或隐形人台成片。

```bash
forge generate --product-dir <product_dir> --bucket sku \
  --prompt-file <product_dir>/prompts/sku/<product>-<color>.txt \
  --ref source=<母版：main 锚点 / 产品图> \
  --ref garment=<output/<logo>/bg_white/<product>-<color>.png> \
  --name <product>-<color> --ratio 1:1 --json
```

成品落在 `output/<logo>/sku/<product>-<color>.png`。

```
一张女装 SKU 配色规格图，可上架，不是插画、不是拼图、不是九宫格。

【主体】
人物锁定（必须写看得见的细节）
- 性别与年龄感：
- 脸型、五官、肤色、妆容：
- 眼型、瞳色、双眼皮、眼神光（眼部细节禁止改）：
- 发型发色长度与分线：
- 体型与肩宽：
以上与母版为同一人。姿势、头朝向、视线与母版一致，不要换机位、不要换姿势。

服装锁定（必须写到本张配色）
- 品类与版型：
- 本张颜色与面料质感（写成衣图看见的颜色，不要写母版原色）：
- 领口 / 袖口 / 下摆：
- 印花位置：
- 印花逐项：主图形 / 颜色 / 文字原文（逐字，含大小写） / 装饰元素：
- 下装、鞋、包：与母版一致，本张不要凭空加减

【场景】
空间、道具左右位置、地面、主光、色温与母版同一张。禁止换房间。

【风格（Campaign Style Lock）】
（粘贴 facts.style_lock。没点名则跟母版写光线、色温、背景。必须含 6 位 Hex 色号。）

【镜头语言】
机位、取景、占比与母版一致，不要改景别。铺满画布，禁止白边、黑边、letterbox。

【氛围与细节】
商业女装实拍，织物与皮肤质感跟母版。

【参考图角色】
成片参考图（文件名 source）：SKU 母版。决定人物五官、发型、身体姿势、头朝向、手、下装、鞋、包、房间、光线、机位与取景。这张上原来的上衣颜色作废。
成衣图（文件名 garment）：本张配色的白底成衣。颜色、版型、领口、肩线、袖型、袖口、下摆、衣长、面料、印花和文字都以它为准。

【约束】
只换上衣为成衣图这一色。构图、姿势、场景保持母版。禁止把母版原来的衣服颜色留下来，禁止重绘印花，禁止印花出现第二次。只输出一张图。无水印、无边框、无后期大字、无 logo 角标。
```
