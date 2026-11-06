# 工作流：印花提取

从服装实拍 / 成衣上取出平面印花，输出白底（再经 `--cutout` 变透明底）。出图只调用 `forge generate`。Prompt 模板：`references/prompts/extract.md`。

方法来自电商出图工作流的「商品事实锁定」：图案、文字、颜色以照片为准，不重绘、不补全。

## 何时用

用户说提取印花、抠图案、要透明底 logo / 胸前印花 / 单独图案文件。

## 输入

| 素材 | 角色 | 必填 |
| --- | --- | --- |
| 服装或商品照片 | 印花所在的成衣/实拍 | 是 |
| 用户指定哪一块 | 「只要左胸小狗」等 | 否 |

不要把风格参考图、海报、详情长图当提取源。

## 步骤

1. `forge doctor --json`。失败则停。
2. `forge job init --workflow extract --slug <短名> --json`。
3. 看图登记：印花位置、文字原文、主色、是否多块印花。写入 `facts.json` 的 `print` 段。文字必须逐字来自图。
4. 多块印花时问用户提取哪一块；用户说「都要」则每块一个任务。
5. 把 `references/prompts/extract.md` 模板写入 `work/prompts/print.txt`，补充说明写位置。
6. 只有一块印花且用户已指定（或图上只有一块）则不必再问。多块或位置不清时按 `SKILL.md`「生图前确认」问要提取哪块。
7. 出图：

```
forge generate --job-dir <run_dir> \
  --prompt-file <run_dir>/work/prompts/print.txt \
  --ref <照片> --name print --cutout --json
```

8. 质检（必须看图）：
   - 只有图案，没有袖子、领口、衣架、人脸
   - 文字完整、未镜像、未改字
   - 颜色与原图一致
   - 图案已放平，没有褶皱透视
   - `--cutout` 后背景透明，边缘没有一圈白边脏点
9. 失败：改补充说明或去掉 `--cutout`，同一 `--name` 重跑 1 次。
10. 交付 `images/print.png`。需要贴回衣服时交给 `references/workflows/compose.md`。
