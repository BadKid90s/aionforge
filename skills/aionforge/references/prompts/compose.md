# 印花合成 Prompt

按 `references/prompts/formula.md` 组段。把提取好的透明底印花合到白底成衣上。写入 `<product_dir>/prompts/bg_white/<product>-<color>.txt`，位置和尺寸写进「镜头语言」。

```bash
forge generate --product-dir <product_dir> --bucket bg_white \
  --prompt-file <product_dir>/prompts/bg_white/<product>-<color>.txt \
  --ref print=<product_dir>/refs/<product>-print.png \
  --ref garment=<白底成衣> \
  --name <product>-<color> --ratio 1:1 --json
```

成品落在 `output/<logo>/bg_white/<product>-<color>.png`。每个颜色单独一份 Prompt、单独一次 generate。

```
一张女装印花合成图，棚拍成衣照片。

【主体】
印花图（文件名 print）：平面图案，通常白底或透明底，没有衣服和人脸。形状、颜色、文字和比例与印花图一致，不要重绘。印花文字逐字为「<facts.print.text_exact>」；没有文字则写「无文字」。
成衣图（文件名 garment）：白底或平铺的衣服。版型、颜色、领口、袖口、下摆与成衣图一致。印花只出现一次。

【场景】
无缝纯白 `#FFFFFF`，铺满画幅四边。不要灰底、棋盘格透明底、渐变底板、地面投影板。

【风格（Campaign Style Lock）】
商业白底产品摄影，均匀柔光，无色偏。

【镜头语言】
- 景别：成衣全身平铺或挂拍全貌
- 视角：平视
- 印花位置：（未指定则胸前正中）与大约宽

【氛围与细节】
衣服外轮廓平滑抗锯齿：袖笼、袖口、下摆、领弧是连续曲线。禁止锯齿、阶梯像素边、毛边、碎边、抠图白边。

【约束】
不要加模特、不要加额外图案。去掉吊牌、领标、衣架和背景杂物。只输出一张照片。用印花图 / 成衣图指代参考图，不要写图序号。
```
