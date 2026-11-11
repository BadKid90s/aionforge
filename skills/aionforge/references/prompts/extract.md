# 印花提取 Prompt

## 平面 logo 图案稿

优先用 `forge cutout --ai`：

```bash
forge cutout --input <logo稿> --product-dir <product_dir> --name <product>-print --ai --json
```

模型只负责语义判断：去掉图案外围的白底、白边、白色残留和半透明白色光晕，保留图案内部的白色文字、描边和高光；最终透明通道由本地 flood fill 生成，不依赖模型直接输出透明图。原稿本来就是干净透明 PNG 时，去掉 `--ai` 只走本地抠图，文字和形状逐像素不变。

深色图案、字母孔洞里的封闭白区加 `--remove-enclosed-white`；白色字标保持默认的 `--keep-enclosed-white`。稿子有压缩噪点或孤立白点时加 `--denoise 4`。提取后跑一次 `forge verify --image <...> --print --json`。

图案内部有透明镂空（字母内圈、图形穿孔）或图案本身就是白色时，不要用 `--ai`：模型会把镂空当成白色细节保留，纯白图案可能被清洗成空白。这两类稿子走本地路径。

需要自定义清洗 Prompt 时，把下面模板写入 `<product_dir>/prompts/refs/<product>-print.txt`，再执行：

```bash
forge generate --product-dir <product_dir> --store refs \
  --prompt-file <product_dir>/prompts/refs/<product>-print.txt \
  --ref source=<logo稿> --name <product>-print --cutout --json
```

```
一张可复用的平面印花图案文件。

【主体】
把参考图中的平面印花图案完整提取到纯白背景上。形状、颜色、文字、字体、笔画、比例和相对位置必须与参考图一致，逐字保留，不要重新设计、美化、补全、简化或改字。

【场景】
纯白 `#FFFFFF` 背景，图案完整居中，四周少量白边。

【风格（Campaign Style Lock）】
平面图形，无光影、无材质褶皱。

【镜头语言】
正面平面图，无透视。

【氛围与细节】
去掉图案外围的白色背景、白边、白色残留和半透明白色光晕；保留图案内部本来就属于设计的白色（白色文字、描边、高光、眼睛留白）。边缘干净。

【约束】
不要输出衣服、模特、衣架、吊牌、背景杂物，也不要添加新的水印、二维码或说明文字。只输出一张图片，不要拼图。源图带素材站水印时，提示用户换有授权的无水印源文件。
```

## 印花只存在于成衣实拍上

按 `references/prompts/formula.md` 组段。把下面模板写入 `<product_dir>/prompts/refs/<product>-print.txt`。用户指定了哪一块印花时，把要求写进「主体」。

然后：

```bash
forge generate --product-dir <product_dir> --store refs \
  --prompt-file <product_dir>/prompts/refs/<product>-print.txt \
  --ref <商品照片> --name <product>-print --cutout --json
```

`--cutout` 把白底打成透明并按图案裁切，这是本地处理，不是模型能力。成品落在 `<product_dir>/refs/<product>-print.png`，不放进 `bg_white`。用完跑一次 `forge verify --image <...> --alpha --json`。

```
一张可复用的平面印花图案文件。

【主体】
从参考图（服装或商品照片）上提取印花。形状、颜色、文字和比例必须与参考图一致，不要重新设计、美化或补全。把图案放平，去掉衣服褶皱和透视。多块时提取正面面积最大的一块（用户另有指定则按指定）。

【场景】
纯白 `#FFFFFF` 背景，图案完整居中，四周少量白边。

【风格（Campaign Style Lock）】
平面图形，无光影、无材质褶皱。

【镜头语言】
正面平面图，无透视。

【氛围与细节】
文字和描边完整，边缘干净。

【约束】
不要输出衣服、模特、衣架、吊牌、背景杂物，也不要添加新的水印、二维码或说明文字。只输出一张图片，不要拼图。源图带素材站水印时，提示用户换有授权的无水印源文件。
```
