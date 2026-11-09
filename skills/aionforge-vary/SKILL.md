---
name: aionforge-vary
description: >
  女装电商图裂变：基于一张已通过的成片，保持服装、场景和风格，变化机位和姿势。
  用户说裂变、多机位、多姿势、lookbook、再出几张、保持场景换角度时使用。
  Use when the user runs /aionforge-vary.
---

# 电商图裂变

基于一张已通过的参考图（通常是换装成功的模特图），保持服装身份，按内置展示套餐换机位与姿势。出图只调用 `forge generate`。

未加载入口时先读 `../aionforge/SKILL.md`。`forge` = `uv run --project <入口目录>/scripts forge`，入口目录是本 SKILL.md 同级的 `../aionforge`。标准流程按入口 Skill。

- Prompt 骨架：`../aionforge/references/prompts/vary.md`
- 展示套餐（镜头 + 场景 + 风格写在同一段）：`../aionforge/references/catalog/looks.json`
- 用户给了姿势/lookbook 图：加 `--ref pose=`，身体按该图，文字套餐作补充

参考图贡献光线、色板、房间、人物身份；衣服结构优先成衣图。

换一件衣服或换一个模特 → `aionforge-tryon`。详情卖点长图 → `aionforge-pdp`。

## 输入

| 素材 | 角色 | 必填 |
| --- | --- | --- |
| 参考成片 | source | 是 |
| 白底成衣 | garment | 建议有 |
| 张数、走/坐/半身等关键词 | 计划 | 否 |
| 姿势参考图 | pose | 否 |

## 选套餐

读取 `../aionforge/references/catalog/looks.json`。每条 shot 已按万象公式写好【场景】【风格】【镜头语言】【主体动作】，整段粘贴，不要拆开重配。

1. 选 pack：用户说走/动态 → `walk`；窗光/生活 → `lifestyle`；特写/细节 → `detail`；否则 `studio`。
2. 无印花则跳过 `requires: ["print"]` 的 shot。
3. 用户给了单屏姿势参考：先按参考图写该张，再从 pack 里补未占用的 shot。
4. 张数：用户点名 > 该 pack 全部 shot。`plan.json` 的 `name` = shot id（如 `studio-front`）。
5. 有姿势参考图时 `--ref pose=`，Prompt 写：身体、手脚、头朝向以姿势参考图为准，本张套餐文字作补充。

## 步骤

1. doctor。
2. `forge job init --workflow vary --slug <短名> --json`（或接到已有 tryon 的 `run_dir`）。
3. 看参考图锁视觉 DNA：房间、光线、色温、人物。看成衣图锁版型印花。新任务写完 `facts.json` 后按入口 Skill「锁商品事实」给用户核对；接到已有 tryon 则沿用已确认的 facts。
4. 按上一节选出 shot，写入 `plan.json`。确认规则见入口 Skill「生图前确认」。
5. 每张：按 `../aionforge/references/prompts/vary.md` 填人物与印花事实，再把该 shot 的 `prompt` 整段贴进「本张展示」。有 `--ref pose=` 时补一句身体跟姿势参考图。
6. 出图：

```
forge generate --job-dir <run_dir> \
  --prompt-file <run_dir>/work/prompts/studio-front.txt \
  --ref source=<参考成片> --ref garment=<成衣> \
  --name studio-front --ratio 1:1 --json
```

有姿势参考图时加 `--ref pose=<图>`。没有成衣时只传 `--ref source=`。指定 `--ratio` 后默认扩图铺满。

7. 质检：同一件衣服、同一双眼睛和五官；头、颈、视线跟本张【主体动作】（侧身是侧脸，回眸是过肩，走是看路，低头是看衣）；禁止正面脸贴在侧身或后背上；构图符合该 shot 的镜头语言；印花未漂。
8. 失败只重做该 `--name`。
