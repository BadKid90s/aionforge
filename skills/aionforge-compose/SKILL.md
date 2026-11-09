---
name: aionforge-compose
description: >
  女装印花合成：把已提取的平面印花贴到白底成衣指定位置。
  用户说把印花贴上去、印花合成、白衣加图案、胸前/后背印花时使用。
  Use when the user runs /aionforge-compose.
---

# 印花合成

把已提取的平面印花贴到白底成衣指定位置。出图只调用 `forge generate`。

未加载入口时先读 `../aionforge/SKILL.md`。`forge` = `uv run --project <入口目录>/scripts forge`，入口目录是本 SKILL.md 同级的 `../aionforge`。Prompt 模板：`../aionforge/references/prompts/compose.md`。标准流程按入口 Skill。

商品身份来自成衣图，图案身份来自印花图。风格参考不提供卖点或品牌。

印花图已经是平面白底或透明底、没有衣服和褶皱，直接合成。印花还在成衣/实拍上，先调用 `aionforge-extract`。

## 输入

| 素材 | 角色 | 必填 |
| --- | --- | --- |
| 透明底或白底印花 PNG | print | 是 |
| 白底成衣 | garment | 是 |
| 位置与大约尺寸 | 补充说明 | 否，默认胸前正中 |

## 步骤

1. doctor。
2. 已有任务目录则复用（提取刚跑完）；否则 `job init --workflow compose`。
3. 看两张图：成衣版型颜色；印花文字与朝向。写入 facts。写完按入口 Skill「锁商品事实」给用户核对，通过后再进入下一步。
4. 确认位置：`chest_center` / 左胸 / 右胸 / 后背正中 / 下摆。用户没说则放进生图前确认问题，建议胸前正中。
5. 复制 `../aionforge/references/prompts/compose.md` 到 `work/prompts/print-on-garment.txt`，写上位置和大约宽（例如「宽约衣宽的 30%」）。补充说明必须带上：纯白 `#FFFFFF` 无缝背景；衣服外轮廓平滑抗锯齿，不要阶梯像素边或抠图杂边。
6. 出图：

```
forge generate --job-dir <run_dir> \
  --prompt-file <run_dir>/work/prompts/print-on-garment.txt \
  --ref print=<印花PNG> --ref garment=<白底成衣> \
  --name print-on-garment --ratio 1:1 --json
```

7. 质检：
   - 衣服仍是成衣那一件（领口袖口下摆未变）
   - 印花只出现一次，未重复、未扭曲成新图案
   - 文字可读、未镜像
   - 位置符合计划，没有漂到袖子或领口
   - 没有凭空出现第二件衣服或模特
   - 背景是无缝纯白 `#FFFFFF`，四边都是白，没有灰底、棋盘格或投影底板
   - 袖笼、袖口、下摆、领弧外轮廓平滑抗锯齿；放大看没有阶梯像素边、毛边、碎边或抠图杂边
8. 失败改 Prompt 点名出错部位（轮廓锯齿则写「外轮廓平滑抗锯齿的棚拍成衣，纯白底，不要抠图像素边」），同一 `--name` 重跑 1 次。
