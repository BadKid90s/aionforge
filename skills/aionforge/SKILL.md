---
name: aionforge
description: >
  女装电商 AI 出图入口：看图锁商品事实、调度工作流 Skill、调用 `forge generate` 出图并逐张质检。
  只要用户想用衣服照片、模特照片、竞品参考图或印花做任何电商图，就使用本 Skill，即使没说「套图」或「工作流」。
  命中更具体的 `aionforge-*` 工作流 Skill 时，先加载那个 Skill 再执行。
  例如「提取胸前印花」「把这个图案印到白T上」「把成衣穿到这个模特身上」「这张再裂变 6 个机位」
  「照这张竞品图的排版和色调做我的连衣裙」「这件吊带出一套拼多多主图」「换个姿势再来几张」
  「SKU裂变」「SKU套图」「按这张母版出黑、藏青、浅灰规格图」「检查 aionforge 环境」。
  只是讨论或修改 AionForge 代码、聊电商运营而不需要出图时不要使用。
---

# AionForge 入口

有对应工作流 Skill 时必须先加载再执行，不要只凭记忆走流程。宣布 `Using [skill] to [purpose]`，然后严格按该 Skill。

## 选 Skill

| 用户意图 | Skill |
| --- | --- |
| 从衣服照片上取出平面印花 | `aionforge-extract` |
| 把已有印花贴到白底成衣 | `aionforge-compose`（还没有印花文件就先 `aionforge-extract`） |
| 把成衣穿到某个模特身上 | `aionforge-tryon` |
| 基于一张通过的成片，多机位 / 多姿势 | `aionforge-vary` |
| SKU 裂变 / SKU 套图 / SKU 母版 / 电商 SKU / SKU 图 / 批量规格图：母版产品图 + 多张配色白底 | `aionforge-sku` |
| 参考竞品图 / 标杆海报的版式与光影，迁移到自家成衣 | `aionforge-deconstruct` |
| 主图 + 详情整套上架图（含卖点信息图、3D 隐形人台） | `aionforge-pdp`（内部会用到 tryon / vary / extract） |

用户已经点名就直接用。一句话里有多步（合成再换装、换装再裂变）时按顺序调用多个 Skill，共用同一个 `job-dir`。商品事实核对见第 4 步；生图前确认只问一次整单缺口。

工作流 Skill 与本 Skill 同级：`../aionforge-<id>/SKILL.md`。

## 运行要求

需要 `uv` 和至少一个图片模型 Key。出图 CLI 随本 Skill 放在 `scripts/`，看图分析由宿主 Agent 完成。

所有 `forge ...` 都指 `uv run --project <skill目录>/scripts forge ...`，`<skill目录>` 是**本** SKILL.md 所在目录的绝对路径（`skills/aionforge`）。工作流 Skill 里的 `forge` 也指向这里，不要用工作流 Skill 自己的目录。在用户的工作目录执行，不要 cd 进 Skill 目录——任务目录和 `.env` 都按当前目录解析。首次运行 uv 会自动装依赖。

你是编排器，不是画师。你负责看图、锁定商品事实、写计划、等人确认、逐张写 Prompt、逐张质检；真正出图只交给 `forge generate`。图片模型擅长画、不擅长记事实：领口、袖口、印花文字一旦没写死就会自由发挥，电商图画错一处就是错款。

一套图 = 一个任务目录 + 一份 `plan.json` + 多次 `forge generate`（每次一张）。

## 资源地图

按需读取，不要一次全读。路径相对本 Skill 目录。

| 什么时候读 | 文件 |
| --- | --- |
| 写任何 Prompt 时先看组段公式 | `references/prompts/formula.md` |
| 写某类 Prompt 时复制模板 | `references/prompts/{extract,compose,tryon,vary,sku,infographic,ghost-mannequin,deconstruct}.md` |
| 看图写 `facts.json`（含正反面路由、三轴参考协议） | `references/analysis.md` |
| 女装展示套餐（镜头+场景+风格+动作） | `references/catalog/looks.json` |
| 图内印字、6 大平台字体与配色 | `references/typography.md` + `references/catalog/typography.json` |
| 信息图写 style_lock 的规则 | `references/style-lock.md` |
| 整套图选图型、姿势映射、主图/详情菜单与组装 | `references/shots-womenswear.md` |
| 用户点名平台、需要比例与风格映射 | `references/platforms.md` |
| 查 CLI 全部参数、信封格式 | `references/cli.md` |
| 用户要新增姿势 / 场景 / 风格 / 字体美学 | `references/catalog/README.md` |

## 标准流程

每个工作流都走这条主线，细节差异看对应工作流 Skill。

1. **环境检查**：`forge doctor --json`。任一项 `pass: false` 就把 `suggestion` 转告用户并停下——Key 或网络不通时出图只会浪费用户的额度和时间。
2. **建任务目录**：`forge job init --workflow <id> --slug <短名> --json`，记下 `run_dir`，之后所有命令带同一个 `--job-dir`，这样中断后能续跑。
3. **登记素材角色（三轴参考资产协议）**：每张用户图只承担明确角色：
   - 商品事实源：`garment`（正面成衣）、`garment_back`（背面成衣，背视图/360°拼接专用）、`print`（印花特写）
   - 人物身份源：`model`（指定模特）、`source`（已通过的锚点成片）
   - 视觉机制源：`style`（只借光线色调）、`layout`（只借版式构图，严禁复制参考图上的衣服款式与竞品 Logo）
   - **长图隔离红线**：若参考图是竖长条详情页拼接图（`H / W >= 2.2`），标记 `LONG_PAGE`，**只看图文字反推，严禁传给 `--ref`**。
4. **锁商品事实**：按 `references/analysis.md` 写 `facts.json`（含 `garment_position` 合理搭配推导、`conversion_driver` 转化钩子、`selling_points` 卖点视觉化）。这是整套图的"真相源"，后面每张 Prompt 都从这里抄。看不清的写入 `facts.uncertain`。写完立刻把关键事实列给用户核对：品类、主色、领口、袖型/袖口、下摆、衣长、印花文字与位置、`uncertain`。用户说没问题之前，禁止写计划、禁止 `forge generate`。用户改正则先改 `facts.json` 再继续。说「你决定 / 直接出」只跳过第 7 步的缺口提问，不跳过本步——领口袖口看错一次，后面整套都错款。
5. **锁展示套餐与字体美学**：模特/裂变图用 `references/catalog/looks.json` 对应 shot 的【风格】段，不要另配一套。信息图按 `references/style-lock.md` 与 `typography.json` 写 `style_lock`（必须含 6 位 Hex）。
6. **写计划**：sku 按 `aionforge-sku` 一色一任务；其余按 `references/shots-womenswear.md` 写 `plan.json`（`name` / `ratio` / 一句话目标；图型从菜单组装，姿势先映射参考图，不够再从姿势库补齐）。
7. **生图前确认**：只问缺口。用户已经点名的直接采用，不要再确认。
   - 缺口：`facts.uncertain`、技能 Default、用户两句话互相打架、以及比例 / 张数 / 场景 / 印花位置 / 露脸与配饰 / 素材角色里用户没说的项。姿势按 `references/shots-womenswear.md` 写入计划，不必再问。模特图脸被挡或看不清，也是缺口（换露脸图 / 允许生成五官 / 保持挡脸）。
   - 有缺口：一次问完，每项给选项和建议；用户回答或说「你决定 / 直接出」之前禁止 `forge generate`。
   - 没有缺口：跳过提问，直接出图。
8. **两阶段模特锚点锁定（多张含模特图时）**：先生成第 1 张核心上身主图（`main-hero`），质检通过后，后续所有含模特的镜头必须把这张成片作为 `--ref source=<run_dir>/images/main-hero.png` 传入，实现跨机位同一人物、同一场景锚定。sku 每张都用原始母版做 `--ref source=`，不要把上一色的生成图当母版。
9. **逐张出图**：按 `references/prompts/formula.md` 组段，把 Prompt 写进 `work/prompts/<name>.txt`，再 `forge generate --prompt-file`。需要画面内文字时必须使用 `VISIBLE_TEXT_BLOCK` 隔离块。
10. **逐张质检**：自己看图，对照下方清单。不合格只重做那一张。
11. **交付**：报告 `run_dir`、`images/` 下的文件、失败项。若用户说了「你决定」，把当时代选的项列为 Assumptions。

## 命令速查

下面的 `forge` 都按上文展开成 `uv run --project <skill目录>/scripts forge`。不要绕过 CLI 自己拼图片 API。

```bash
forge doctor --json
forge job init --workflow pdp --slug <短名> --json
forge generate --job-dir <run_dir> --prompt-file <txt> --ref <图> --name <id> --ratio 1:1 --json
```

- 参考图带角色名，让模型按文件名认图：`--ref garment=<成衣> --ref model=<模特>`、`--ref print=<印花> --ref garment=<白衣>`、`--ref source=<锚点成片>`、`--ref garment_back=<背面图>`、`--ref layout=<单屏版式参考>`、`--ref style=<风格参考>`、`--ref pose=<姿势参考图>`。
- 印花提取加 `--cutout`（本地把白底转透明并裁切）。
- 返回 `{ok, run_dir, images, error}`。完整参数见 `references/cli.md`。

CLI 只有 `doctor` / `job init` / `generate` 三个命令。换装、提取、合成、裂变、SKU 配色、反推迁移的差别全在 Prompt 里，不存在额外子命令。

## 两条全局规则

这两条在每个工作流都适用，是历史上最常返工的地方。

**锁脸 = 锁五官和眼睛，不是把头钉死。** 换装和裂变要保留同一个人：眼型、瞳色、双眼皮、眼神光、五官比例都不能变。但头、颈、下颌、视线必须跟着本张姿势走——回眸、过肩时看到侧脸或后脑是对的；身体在走路或坐着、脸却正对镜头，看起来就是 P 上去的。

**比例不够就扩图，不留白。** 指定 `--ratio` 而参考图比例对不上时，默认 `--fit expand` 延伸场景铺满画幅。不要用 `pad`，不要白边、黑边、letterbox——平台主图出现留白会被判低质。

## 质检清单

每张生成后对照 `facts.json` 看图：

- 衣服是成衣图那一件，不是模特原来的上衣或竞品参考图的衣服（换装与反推最常见的失败）
- 领口 / 袖口 / 下摆 / 肩线 / 衣长与成衣一致
- 印花位置、颜色、文字逐字一致，只出现一次，未镜像
- 换装 / 裂变 / 套图：同一双眼睛和五官，头的朝向符合本张姿势
- SKU 规格图：人、姿势、场景与母版一致；衣服颜色和结构是本张配色白底那一件，不是母版原色
- 主图背景干净，服装轮廓完整，主体占比与呼吸留白符合平台美学
- 图内若有文字（`VISIBLE_TEXT_BLOCK`）：放大 200% 检查汉字笔画完整无乱码、无黑边描边、未把字号/色号等排版元指令画进画面
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

组段顺序与镜头词典见 `references/prompts/formula.md`：用途 → 主体 → 场景 → 风格 → 镜头语言 → 氛围与细节 → 参考图角色 → 图内文字 → 约束。

- 用「成衣图 / 背面成衣图 / 模特图 / 印花图 / 锚点成片 / 版式参考图」指代参考图，不要写「图1 / 图2」——多图输入时模型不保证顺序。
- 只写图上看得见的事实。不编造品牌、认证、销量、面料成分；看不清的写进 `facts.uncertain`，并在 Prompt 里要求那些部位不要臆造。
- 印花文字逐字照抄，包括大小写；图内排版文案一律放进 `VISIBLE_TEXT_BLOCK` 并用 `「...」` 包裹。
- 光线写具体方向与软硬（如「左侧窗来的柔和自然光」），不要写「美丽的光线」。裂变或编辑写死「只改 X，其余与成片一致」。
