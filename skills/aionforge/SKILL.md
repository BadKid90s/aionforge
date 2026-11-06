---
name: aionforge
description: >
  女装电商 AI 出图编排：看图锁商品事实、写计划与逐图 Prompt、调用 `forge generate` 出图并逐张质检。
  覆盖印花提取（抠出透明底图案）、印花合成（图案贴回白衣）、模特换衣（成衣穿到指定模特、锁五官）、
  电商图裂变（同一成片多机位多姿势）、主图 + 详情整套上架图（拼多多 / 淘宝 / 京东 / 抖音 / Amazon 等）。
  只要用户想用衣服照片、模特照片或印花做任何电商图，就使用本 Skill，即使没说「套图」或「工作流」：
  例如「提取胸前印花」「把这个图案印到白T上」「把成衣穿到这个模特身上」「这张再裂变 6 个机位」
  「这件吊带出一套拼多多主图」「换个姿势再来几张」。
  只是讨论或修改 AionForge 代码、聊电商运营而不需要出图时不要使用。
---

# AionForge 女装出图

## 运行要求

需要 `uv` 和至少一个图片模型 Key。出图 CLI 随本 Skill 放在 `scripts/`，看图分析由宿主 Agent 完成。

本 Skill 里所有 `forge ...` 都指 `uv run --project <skill目录>/scripts forge ...`，`<skill目录>` 是本 SKILL.md 所在目录的绝对路径。在用户的工作目录执行，不要 cd 进 Skill 目录——任务目录和 `.env` 都按当前目录解析。首次运行 uv 会自动装依赖。

你是编排器，不是画师。你负责看图、锁定商品事实、写计划、等人确认、逐张写 Prompt、逐张质检；真正出图只交给 `forge generate`。这样分工是因为图片模型擅长画、不擅长记事实：领口、袖口、印花文字这些一旦在 Prompt 里没写死，模型就会"自由发挥"，而电商图画错一处就是错款。

一套图 = 一个任务目录 + 一份 `plan.json` + 多次 `forge generate`（每次一张）。

## 资源地图

按需读取，不要一次全读：

| 什么时候读 | 文件 |
| --- | --- |
| 选定工作流后，照着走步骤 | `references/workflows/<workflow>.md` |
| 写某类 Prompt 时复制模板 | `references/prompts/{extract,compose,tryon,vary}.md` |
| 看图写 `facts.json` | `references/analysis.md` |
| 多图任务锁风格 | `references/style-lock.md` + `references/catalog/styles.json` |
| 换装多机位 / 裂变选姿势 | `references/workflows/vary.md` + `references/catalog/poses.json`（`cameras` × `poses`） |
| 整套图选图型和顺序 | `references/shots-womenswear.md` |
| 用户点名平台、需要比例 | `references/platforms.md` |
| 查 CLI 全部参数、信封格式 | `references/cli.md` |
| 用户要新增姿势 / 场景 / 风格 | `references/catalog/README.md` |

## 选工作流

| 用户意图 | 工作流 |
| --- | --- |
| 从衣服照片上取出平面印花 | `extract` |
| 把已有印花贴到白底成衣 | `compose`（还没有印花文件就先 `extract`） |
| 把成衣穿到某个模特身上 | `tryon` |
| 基于一张通过的成片，多机位 / 多姿势 | `vary` |
| 主图 + 详情整套上架图 | `pdp`（内部会调用 tryon / vary / extract） |

用户已经点名就直接用。一句话里有多步（合成再换装、换装再裂变）时按顺序串成一条流水线，共用同一个 `job-dir`，生图前确认只问一次整单缺口。

## 标准流程

每个工作流都走这条主线，细节差异看对应 workflow 文件。

1. **环境检查**：`forge doctor --json`。任一项 `pass: false` 就把 `suggestion` 转告用户并停下——Key 或网络不通时出图只会浪费用户的额度和时间。
2. **建任务目录**：`forge job init --workflow <id> --slug <短名> --json`，记下 `run_dir`，之后所有命令带同一个 `--job-dir`，这样中断后能续跑。
3. **登记素材角色**：每张用户图只承担一种角色——成衣 / 模特 / 印花 / 成片参考 / 风格参考。风格参考只提供光线和色调，它上面的品牌、文案、卖点不是这件商品的事实。
4. **锁商品事实**：按 `references/analysis.md` 写 `facts.json`。这是整套图的"真相源"，后面每张 Prompt 都从这里抄。看不清的写入 `facts.uncertain`。
5. **锁风格**（多图任务）：按 `references/style-lock.md`。用户点名则用 `styles.json` 原文；没点名则跟场景参考图写 `style_lock`，贴进每一张，一字不差。
6. **写计划**：`plan.json` 列出每张的 `name` / `ratio` / 一句话目标。
7. **生图前确认**：只问缺口。用户已经点名的直接采用，不要再确认。
   - 缺口：`facts.uncertain`、技能 Default、用户两句话互相打架、以及比例 / 张数 / 场景 / 印花位置 / 露脸与配饰 / 素材角色里用户没说的项。姿势按 `references/workflows/vary.md` 从镜头×姿势随机组合。模特图脸被挡或看不清，也是缺口（换露脸图 / 允许生成五官 / 保持挡脸）。
   - 有缺口：一次问完，每项给选项和建议；用户回答或说「你决定 / 直接出」之前禁止 `forge generate`。
   - 没有缺口：跳过提问，直接出图。
8. **逐张出图**：Prompt 写进 `work/prompts/<name>.txt`，再 `forge generate --prompt-file`。用文件而不是命令行字符串，是为了能复查、能改、能复现。
9. **逐张质检**：自己看图，对照下方清单。不合格只重做那一张。
10. **交付**：报告 `run_dir`、`images/` 下的文件、失败项。若用户说了「你决定」，把当时代选的项列为 Assumptions。

## 命令速查

下面的 `forge` 都按上文展开成 `uv run --project <skill目录>/scripts forge`。不要绕过 CLI 自己拼图片 API。

```bash
forge doctor --json
forge job init --workflow pdp --slug <短名> --json
forge generate --job-dir <run_dir> --prompt-file <txt> --ref <图> --name <id> --ratio 1:1 --json
```

- 参考图带角色名，让模型按文件名认图：`--ref garment=<成衣> --ref model=<模特>`、`--ref print=<印花> --ref garment=<白衣>`、`--ref source=<成片>`。
- 印花提取加 `--cutout`（本地把白底转透明并裁切）。
- 返回 `{ok, run_dir, images, error}`。完整参数见 `references/cli.md`。

CLI 只有 `doctor` / `job init` / `generate` 三个命令。换装、提取、合成、裂变的差别全在 Prompt 里，不存在 `tryon` / `extract` / `combo` / `vary` 子命令。

## 两条全局规则

这两条在每个工作流都适用，是历史上最常返工的地方。

**锁脸 = 锁五官和眼睛，不是把头钉死。** 换装和裂变要保留同一个人：眼型、瞳色、双眼皮、眼神光、五官比例都不能变。但头、颈、下颌、视线必须跟着本张姿势走——回眸、过肩时看到侧脸或后脑是对的；身体在走路或坐着、脸却正对镜头，看起来就是 P 上去的。

**比例不够就扩图，不留白。** 指定 `--ratio` 而参考图比例对不上时，默认 `--fit expand` 延伸场景铺满画幅。不要用 `pad`，不要白边、黑边、letterbox——平台主图出现留白会被判低质。

## 质检清单

每张生成后对照 `facts.json` 看图：

- 衣服是成衣图那一件，不是模特原来的上衣（换装最常见的失败）
- 领口 / 袖口 / 下摆 / 肩线 / 衣长与成衣一致
- 印花位置、颜色、文字逐字一致，只出现一次，未镜像
- 换装 / 裂变：同一双眼睛和五官，头的朝向符合本张姿势
- 主图背景干净，服装轮廓完整
- 图内若有文字：短、清晰、无错字
- 画幅等于计划比例，四边都有内容

不合格就改 Prompt 文件里点名出错的部位（如"袖口是平口，不是罗纹"），用同一个 `--name` 重跑一次。两次仍失败就记入交付，继续做其余张，不要卡住整套。

## 错误分诊

| 现象 | 处置 |
| --- | --- |
| `ok: false`，reason 含 401 / 403 | 配置问题，引导用户跑 doctor，不要重试 |
| 网络 / 超时 / 限流 | 同参数重试 1 次 |
| 参数错误 | 修正后重跑 |
| 图已生成但质检失败 | 改 Prompt，同一 `--name` 覆盖 |

## 写 Prompt 的底线

- 用「成衣图 / 模特图 / 印花图 / 成片」指代参考图，不要写「图1 / 图2」——多图输入时模型不保证顺序。
- 只写图上看得见的事实。不编造品牌、认证、销量、面料成分；看不清的写进 `facts.uncertain`，并在 Prompt 里要求那些部位不要臆造。
- 印花文字逐字照抄，包括大小写。
