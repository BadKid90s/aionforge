# 工作流：印花合成

把已提取的平面印花贴到白底成衣指定位置。出图只调用 `forge generate`。Prompt 模板：`references/prompts/compose.md`。

商品身份来自成衣图，图案身份来自印花图。风格参考不提供卖点或品牌。

## 何时用

用户说把印花贴上去、印花合成、白衣加图案、胸前/后背印花。还没有透明底印花时，先跑 `references/workflows/extract.md`。

## 输入

| 素材 | 角色 | 必填 |
| --- | --- | --- |
| 透明底或白底印花 PNG | print | 是 |
| 白底成衣 | garment | 是 |
| 位置与大约尺寸 | 补充说明 | 否，默认胸前正中 |

## 步骤

1. doctor。
2. 已有任务目录则复用（提取刚跑完）；否则 `job init --workflow compose`。
3. 看两张图：成衣版型颜色；印花文字与朝向。写入 facts。
4. 确认位置：`chest_center` / 左胸 / 右胸 / 后背正中 / 下摆。用户没说则胸前正中，标 Default。
5. 复制 `references/prompts/compose.md` 到 `work/prompts/print-on-garment.txt`，写上位置和大约宽（例如「宽约衣宽的 30%」）。
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
8. 失败改位置描述，同一 `--name` 重跑 1 次。
