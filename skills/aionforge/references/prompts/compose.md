# 印花合成 Prompt

把提取好的透明底印花合到白底成衣上。写入 `work/prompts/<name>.txt`，位置和尺寸写进「补充说明」。

```
forge generate --job-dir <run_dir> --prompt-file <run_dir>/work/prompts/<name>.txt \
  --ref print=<印花PNG> --ref garment=<白底成衣> --name print-on-garment --ratio 1:1 --json
```

```
# Role: 服装印花合成

## 参考图角色（用画面内容区分，不要用先后顺序猜测）

**印花图**（文件名 print）：平面图案，通常白底或透明底，没有衣服和人脸。
**成衣图**（文件名 garment）：白底或平铺的衣服。输出必须仍是这件衣服，只把印花放到指定位置。

## Rules
1. 印花的形状、颜色、文字和比例与印花图一致，不要重绘。
2. 衣服的版型、颜色、领口、袖口、下摆与成衣图一致。
3. 印花只出现一次，贴在补充说明给出的位置；未指定时放在胸前正中。
4. 不要换场景、不要加模特、不要加额外图案。
5. 只输出一张照片。
```
