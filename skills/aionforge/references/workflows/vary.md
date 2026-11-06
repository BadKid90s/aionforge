# 工作流：电商图裂变

基于一张已通过的参考图（通常是换装成功的模特图），保持服装身份、场景和风格，变化**机位**和**姿势**。出图只调用 `forge generate`。

- Prompt 骨架：`references/prompts/vary.md`
- 机位 / 姿势：`references/catalog/poses.json` 的 `cameras` × `poses`
- 场景：`references/catalog/scenes.json`（默认锁参考图场景；用户要换场景时按 keywords 选）
- 风格：`references/style-lock.md`（没点名则跟参考图写 `style_lock`，贴进每一张）
- 加新定义：见 `references/catalog/README.md` 与 `references/catalog/schemas/`

方法对齐风格裂变：参考图贡献光线、色板、房间、人物身份；衣服结构优先成衣图。

## 何时用

用户说裂变、多机位、多姿势、lookbook、再出几张、保持场景换角度。

换一件衣服或换一个模特 → `tryon`。详情卖点长图 → `pdp`。

## 输入

| 素材 | 角色 | 必填 |
| --- | --- | --- |
| 参考成片 | source | 是 |
| 白底成衣 | garment | 建议有 |
| 张数、走/坐/半身等关键词 | 计划 | 否 |

## 选机位与姿势

读取 `references/catalog/poses.json`。每一张都是一对 `camera` + `pose`。N = 用户说的张数，未说则为 8。

1. **入池**：镜头、姿势各自独立入池。条目带 `requires` 时，成衣具备该结构才入池（`print` / `pockets` / `hoodie`）。用户说了走、坐、回眸、半身、微距等，只保留 `keywords` 命中的条目。
2. **配对**：`cam-detail-*` 配站定类姿势；其余镜头配入池里的任意姿势。随机抽 N 对：每对唯一，同一套内每个镜头 id、每个姿势 id 只用一次。N 取用户张数与两池较小者。
3. **落盘**：`name` = `vary-<camera>-<pose>`。本张机位 = 该镜头 `prompt` + 该姿势 `prompt`；`recipes` 里已有这一对时用那条 `prompt`。`plan.json` 写 `name` / `ratio` / 一句话目标。

## 步骤

1. doctor。
2. `forge job init --workflow vary --slug <短名> --json`（或接到已有 tryon 的 `run_dir`）。
3. 看参考图锁视觉 DNA：房间、光线、色温、人物。看成衣图锁版型印花。
4. 按上一节选出 N 对，写入 `plan.json`。确认规则见 `SKILL.md`「生图前确认」。
5. 每张：按 `references/prompts/vary.md` **整份骨架填写**。先看图写人物/印花零件/房间道具，再把本张 camera + pose 的文案填进「本张机位与姿势」，并写清与成片差在哪。Style Lock 按 `references/style-lock.md`。
6. 出图：

```
forge generate --job-dir <run_dir> \
  --prompt-file <run_dir>/work/prompts/vary-cam-3q-full-pose-lean-wall.txt \
  --ref source=<参考成片> --ref garment=<成衣> \
  --name vary-cam-3q-full-pose-lean-wall --ratio 1:1 --json
```

`--name` 等于 `vary-<camera>-<pose>`。没有成衣时只传 `--ref source=`。指定 `--ratio` 后默认扩图铺满。

7. 质检：同一件衣服、同一双眼睛和五官、同一房间；头随本张姿势转；机位和姿势与本张 camera + pose 一致；与成片构图有明显差别；印花未漂。
8. 失败只重做该 `--name`。
