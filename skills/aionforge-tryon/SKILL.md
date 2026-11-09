---
name: aionforge-tryon
description: >
  女装模特换衣：把成衣穿到指定模特身上，锁五官和眼睛、锁衣服、锁场景。
  用户说换装、试穿、把衣服穿到这个人身上、锁脸出模特图时使用。
  Use when the user runs /aionforge-tryon.
---

# 模特换衣

把成衣穿到模特身上：锁五官和眼睛、锁衣服、锁场景，整件替换上衣。头随姿势转动，不要把头钉死。出图只调用 `forge generate`。

未加载入口时先读 `../aionforge/SKILL.md`。`forge` = `uv run --project <入口目录>/scripts forge`，入口目录是本 SKILL.md 同级的 `../aionforge`。Prompt 模板：`../aionforge/references/prompts/tryon.md`。标准流程按入口 Skill。

成衣图提供商品事实；模特图提供身份与场景，不提供商品版型。禁止只把印花贴到原衣上。

## 输入

| 素材 | 角色 | 必填 |
| --- | --- | --- |
| 白底/平铺/挂拍成衣 | garment | 是 |
| 有完整人脸的模特图 | model | 是 |
| 本张姿势、机位、比例 | 补充说明 | 否 |

成衣图没有需要保留的人脸。两张都是街拍真人时，先问哪张是「要穿的衣服标准」、哪张是「要保留的脸」。模特图脸被挡或看不清时按入口 Skill 生图前确认来问，不要默默生成五官。

## 步骤

1. doctor。
2. `forge job init --workflow tryon --slug <短名> --json`。
3. 看图锁商品事实（版型、领口、袖口、下摆、面料、颜色、印花位置与文字）写入 `facts.json`。写完按入口 Skill「锁商品事实」给用户核对，通过后再进入下一步。
4. 看模特图记下：五官、眼部细节、发型发色、下装、包、房间光线。身体和头按本张姿势重新摆，不要把正面脸贴到走、坐、回眸上。
5. 列出模特原上衣有、成衣没有的结构（罗纹袖口、帽兜、袋鼠兜等），写进 prompt 补充说明的「必须去掉」。
6. 多机位按 `aionforge-vary` 从镜头×姿势随机组对后写入计划。单张且用户已写清姿势则按该姿势写 Prompt。风格按 `../aionforge/references/style-lock.md`。
7. 复制 `../aionforge/references/prompts/tryon.md` 到 `work/prompts/<name>.txt`，贴上 Style Lock（若有）、facts 锁定项、本张姿势。
8. 出图（参考图必须带角色名）：

```
forge generate --job-dir <run_dir> \
  --prompt-file <run_dir>/work/prompts/tryon-01.txt \
  --ref garment=<成衣> --ref model=<模特> \
  --name tryon-01 --ratio 1:1 --json
```

9. 质检（必须看图）：
   - 同一人的五官和眼睛；头的朝向符合本张姿势（回眸必须是侧脸/过肩，不是正面脸贴在背上）
   - 衣服是成衣那一件：领口、袖口、下摆、肩线、衣长
   - 印花位置、文字、颜色与成衣一致，只出现一次
   - 没有模特原衣残留（罗纹、帽子、旧图案）
   - 姿势、下装、包、背景与模特图一致
10. 失败改补充说明（点名袖口/印花），同一 `--name` 重跑 1 次。
