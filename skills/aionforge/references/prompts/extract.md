# 印花提取 Prompt

**平面 logo 图案稿不要走本模板。** 平面稿直接用 `forge cutout --input <logo稿> --product-dir <product_dir> --name <product>-print --json` 本地抠图，保证文字和形状不被重画。本模板只用于「印花只存在于成衣实拍上」的情况。

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
