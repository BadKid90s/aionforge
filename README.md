# AionForge

T 恤印花电商 AI 出图插件。把印花图案稿、T 恤正反面实拍图、模特照片丢给 Agent，它会严格遵循 **「思考 → 事实锁定 → 生成 → 检查」** 闭环：先提取透明印花、分析哪些适合印正面哪些适合印背面、为背面大图提取核心元素生成左胸小印花，再针对不同颜色 T 恤实拍底图做撞色调整适配并合成商品图，最后根据模特图生成锁脸主图与详情卖点图。

架构上严格区分**工具层（`forge` CLI 确定性原子工具）**与**流程层（Skills 业务编排）**：入口 `aionforge` 负责总控路由；四大核心流程依次为 `aionforge-print`、`aionforge-product`、`aionforge-main`、`aionforge-detail`。

- **阶段 1 印花准备（`aionforge-print`）**：提取透明印花、客观体检分析正反面适用性、提取核心元素生成左胸小印花，锁定正反面位置计划
- **阶段 2 实拍调色与合成（`aionforge-product`）**：检测印花与各颜色 T 恤实拍底图的颜色冲突，调整适配印花颜色，合成正面 / 背面 `bg_white` 商品图
- **阶段 3 模特主图（`aionforge-main`）**：保留模特原脸五官与眼神，将合成好的正反面 T 恤穿到模特身上，先出锚点主图再派生正面与背面回眸多姿势主图
- **阶段 4 详情卖点图（`aionforge-detail`）**：基于生成的模特主图和 T 恤商品图，生成放大镜微距、正反双面三角度对比、60:40 分屏与多场景详情图

输出以 **logo 为第一层目录**，每个 logo 下固定三个成品交付目录：`bg_white` / `main` / `detail`。提示词、透明印花、适配印花、事实和 manifest 收在 `.forge`，不污染成品目录。

支持 **Claude Code**、**Codex**、**Cursor**、**Gemini CLI**、**Grok Build**，以及其他支持 Agent Skills 的工具。

## 快速开始

### 1. 安装 uv

插件自带的出图 CLI 用 [uv](https://docs.astral.sh/uv/) 运行，依赖会在第一次使用时自动安装。

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. 安装插件

**通用方式（推荐）**：一条命令装到本机所有支持 Skills 的 Agent（Claude Code、Codex、Cursor、Gemini CLI、OpenCode 等 70+ 种），需要 Node.js：

```bash
npx skills add BadKid90s/aionforge -g
```

`-g` 装到用户目录，所有项目都能用；去掉则只装到当前项目。只装给某个 Agent 用 `-a claude-code`。

也可以用各平台自己的插件系统安装：

**Claude Code**（在 Claude Code 对话框里输入）

```
/plugin marketplace add BadKid90s/aionforge
/plugin install aionforge@aionforge
```

**Grok Build**

```bash
grok plugin install BadKid90s/aionforge
```

**Codex / ChatGPT 桌面版**

```bash
codex plugin marketplace add BadKid90s/aionforge
```

然后在 Codex 的 `/plugins`（或 ChatGPT 桌面版的 Plugins）里安装 `aionforge`。

**Cursor**：用上面的通用方式 `npx skills add BadKid90s/aionforge -g -a cursor`。

**Gemini CLI**

```bash
gemini extensions install https://github.com/BadKid90s/aionforge
```

> 其他 Agent：从 [Releases](https://github.com/BadKid90s/aionforge/releases) 下载 `skills.zip`，解压到 Agent 的 skills 目录（如 `~/.claude/skills/`），会得到入口 `aionforge` 和一组 `aionforge-*` 工作流 Skill。

### 3. 配置图片模型 Key

至少配一个。一等供应商用各自的 Key + 可选 Base URL；其余 OpenAI 兼容网关走通用三件套。

| 供应商 | Key | Base URL（可选） | 默认模型 |
| --- | --- | --- | --- |
| xAI Grok | `XAI_API_KEY` | `XAI_BASE_URL` | `grok-imagine-image-2.0` |
| OpenAI | `OPENAI_API_KEY` | `OPENAI_BASE_URL` | `gpt-image-2.5-sunburst` |
| Google Gemini | `GEMINI_API_KEY` | `GOOGLE_GEMINI_BASE_URL` | `gemini-3-pro-image` |
| 阿里通义万相 | `DASHSCOPE_API_KEY` | `DASHSCOPE_BASE_URL` | `wanx2.1-imageedit` |
| 火山引擎豆包 | `ARK_API_KEY` | `ARK_BASE_URL` | `seedream-4.0` |
| 腾讯混元 | `HUNYUAN_API_KEY` | `HUNYUAN_BASE_URL` | `hy-image-v3` |
| 百度千帆 | `QIANFAN_API_KEY` | `QIANFAN_BASE_URL` | `ernie-image` |
| 其它 OpenAI 兼容 | `AIONFORGE_API_KEY` | `AIONFORGE_API_BASE` | `AIONFORGE_IMAGE_MODEL` |

两套写法：

```bash
# 一等（例：阿里）
DASHSCOPE_API_KEY=...
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/api/v1
AIONFORGE_IMAGE_MODEL=wanx2.1-imageedit

# 通用 OpenAI 兼容
AIONFORGE_API_BASE=https://xxx/v1
AIONFORGE_API_KEY=...
AIONFORGE_IMAGE_MODEL=模型名
```

硅基流动、智谱、MiniMax 以及任意中转站只用第二套。

**方式 A：写进 shell 配置（推荐，所有项目通用）**

```bash
echo 'export XAI_API_KEY=xai-你的key' >> ~/.zshrc   # bash 用户写 ~/.bashrc
source ~/.zshrc
```

改完要**重启 Agent**（Claude Code / Grok / Codex），新开的进程才能读到。

**方式 B：在工作目录放 `.env`（只对这个目录生效）**

在你打算出图的目录新建 `.env`：

```bash
XAI_API_KEY=xai-你的key
```

完整模板见 [`.env.example`](skills/aionforge/.env.example)。别把 `.env` 提交到 git。

> 配了多个 Key 时按 Grok > OpenAI > Gemini > 通义万相 > 豆包 > 混元 > 千帆 的顺序自动选；都没有一等 Key、且同时配了 `AIONFORGE_API_BASE` + `AIONFORGE_API_KEY` 时才走其它 OpenAI 兼容网关。换模型用 `AIONFORGE_IMAGE_MODEL`。

### 4. 开始出图

在放素材的目录启动 Agent，先说：

```
帮我检查一下 aionforge 的环境
```

Agent 会跑 `forge doctor`，Key、网络、目录都通过就可以用了。然后把图片拖进对话框：

- 「这批印花里哪些适合印在 T 恤正面，哪些适合印在背面？背面那几张在左胸前加个核心元素小印花」
- 「把这个图案合成到黑色、白色 T 恤实拍图上，存在颜色冲突的话帮我调整适配印花颜色」
- 「保留这个模特的脸，根据合成好的 T 恤图生成主图，并派生正面和背面回眸几个姿势」
- 「根据生成的主图和商品图生成一套详情卖点图，平台是拼多多」

Agent 会在每个阶段按 **「思考 → 事实锁定 → 生成 → 检查」** 推进：先锁定商品与印花事实，确认后提取印花与左胸小标，再按 T 恤底色调色合成商品图，接着生成模特主图与详情图。

## 输出目录

```text
output/
  锁定目标/
    bg_white/
      short-black.png
      short-black-back.png
      short-白.png
      short-浅灰.png
    main/
      short-black-hero.png
      short-black-walk.png
      short-black-studio-3q.png
    detail/
      short-black-craft.png
    .forge/
      products/
        short/
          facts.json
          refs/
          prompts/
          manifest.json
          history/
```

- `bg_white` 是印花调色并合成后的 T 恤实拍商品图，也是后续 `main` / `detail` 的唯一衣服真相源；`-back` 是背面商品图。
- `main` 是模特锁脸换衣与多姿势主图；先出 `hero` 锚点，后续姿势从它派生。
- `detail` 基于 `main` 模特主图与 `bg_white` 商品图生成详情卖点图。
- 同名重跑覆盖成品，旧图自动进 `history/`；不会堆出一串时间戳目录。

## 工作流

| 阶段 | 意图 | Skill | 输出 |
| --- | --- | --- | --- |
| 阶段 1 | 提取印花、分析正反面、提取核心元素生成左胸小印花 | `aionforge-print` | `refs/*` + `facts.print.placements` |
| 阶段 2 | 针对 T 恤实拍底色调整适配印花颜色、合成正反面实拍商品图 | `aionforge-product` | `bg_white/<product>-<color>[-back].png` |
| 阶段 3 | 模特锁脸换衣、锚点主图与正背面多姿势主图 | `aionforge-main` | `main/<product>-<color>-<pose>.png` |
| 阶段 4 | 基于主图和商品图生成放大镜、三角度、分屏等详情图 | `aionforge-detail` | `detail/<product>-<color>-<detail-id>.png` |

默认所有颜色都出；用户点名只出一个颜色时只跑该色。详情图同时复用 `main` 的锚点成片（`source`）与 `bg_white` 正背面商品图（`garment` / `garment_back`）。

## 常见问题

**doctor 提示没有可用 Key**：Key 没被读到。环境变量方式要重启 Agent；`.env` 方式要确认文件在 Agent 的当前工作目录。

**成品带素材站水印**：`logo/` 里的预览稿水印不会被当成图案的一部分。换有授权的无水印源文件再跑，不要把带水印的预览图直接上架。

**401 / 403**：Key 无效、过期，或账户没开通图片模型权限。

**找不到 uv**：安装后重开终端，或把 `~/.local/bin` 加进 `PATH`。

**中断了想续跑**：告诉 Agent 继续上次的任务。商品工作区、`facts.json`、`manifest.json` 都在 `output/<logo>/.forge/products/<product>/`，会沿用同一个 `product_dir` 接着出剩下的图。

**想换 logo / 商品名**：重新跑 `forge product init`；已存在的 `facts.json` 不会被覆盖。

**更新插件**：`npx skills update`；Claude Code 里 `/plugin marketplace update aionforge`；Grok 用 `grok plugin update aionforge`；Gemini 用 `gemini extensions update aionforge`。

## 进阶

### 全部配置项

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `XAI_BASE_URL` | `https://api.x.ai/v1` | xAI 接口地址 |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI 接口地址 |
| `GOOGLE_GEMINI_BASE_URL` | `https://generativelanguage.googleapis.com/v1beta` | Gemini 接口地址 |
| `DASHSCOPE_BASE_URL` | `https://dashscope.aliyuncs.com/api/v1` | 通义万相接口地址 |
| `ARK_BASE_URL` | `https://ark.cn-beijing.volces.com/api/v3` | 豆包接口地址 |
| `HUNYUAN_BASE_URL` | `https://api.hunyuan.cloud.tencent.com/v1` | 混元接口地址 |
| `QIANFAN_BASE_URL` | `https://qianfan.baidubce.com/v2` | 千帆接口地址 |
| `AIONFORGE_IMAGE_MODEL` | 见上表 | 覆盖默认模型 |
| `AIONFORGE_API_BASE` | — | 其它 OpenAI 兼容网关地址（仅 custom） |
| `AIONFORGE_STORAGE_ROOT` | `.`（Agent 工作目录） | 数据目录 |
| `AIONFORGE_LOG_LEVEL` | `INFO` | 日志级别 |
| `AIONFORGE_LOG_FILE` | `logs/forge.log` | 日志文件（相对当前目录） |
| `AIONFORGE_HTTP_TIMEOUT` | `120` | 图片接口超时秒数 |
| `AIONFORGE_HTTP_RETRIES` | `2` | 断连 / 5xx 自动重试次数 |
| `AIONFORGE_HTTP_BACKOFF` | `2` | 重试退避基数秒数（指数递增） |

读取顺序：进程环境 > 当前目录 `.env` > Skill `.env`。一等供应商的专用 Base 优先于 `AIONFORGE_API_BASE`（后者只用于其它 OpenAI 兼容网关）。

### forge CLI

Agent 会自动调用，一般不用手动跑。手动调用：`uv run --project skills/aionforge/scripts forge <命令>`

| 命令 | 作用 |
| --- | --- |
| `forge doctor --json` | 检查配置、Key、连通性、日志与数据目录；`--deep` 真实 POST 一次出图 |
| `forge product init --logo <logo> --product <product> --json` | 创建 logo 工作区、三个交付目录、商品工作区、facts 模板、manifest |
| `forge cutout --input <印花稿> --product-dir <dir> --name <id> --ai --json` | 平面印花提取：模型清洗白底，本地生成透明通道到 `refs/` |
| `forge extract-core-element --input <印花稿> --product-dir <dir> --name <id> --element-hint "<描述>" --json` | AI 提取一枚完整核心图标，输出 `refs/<id>.png`，带 `complete` / `margin_ratio` |
| `forge print metrics --input <印花> --json` | 印花客观体检：比例、色数、细节密度、笔画、透明孔洞；不写文件 |
| `forge print adapt --print <印花> --garment <成衣> --product-dir <dir> --name <id> --json` | 按成衣底色重映射印花颜色，返回对比度与颜色映射 |
| `forge composite --product-dir <dir> --placement <id> --color <color> --garment <成衣> --name <id> --json` | 按 facts 里的 placement 与颜色合成到成衣实拍；也可显式传 `--print` / `--x` / `--y` / `--width` / `--ink` |
| `forge generate --product-dir <dir> --bucket <bucket> --prompt-file <txt> --ref <图> --name <id> --json` | prompt + 参考图 → 一张成品，落到 `bg_white` / `main` / `detail` |
| `forge verify --image <图> --ratio 1:1 --white-bg --json` | 校验尺寸、比例、白底、印花透明通道与碎点 |
| `forge prompt check --file <txt> --facts <facts.json> --json` | 检查 Hex、图序号、VISIBLE_TEXT_BLOCK、印花原文 |

完整参数见 [`references/tools/index.md`](skills/aionforge/references/tools/index.md)；全局调用方式、JSON 信封与 bucket / store 规则见 [`references/cli.md`](skills/aionforge/references/cli.md)。

### 项目结构

```
.claude-plugin/
  plugin.json             # Claude Code / Grok Build 插件清单
  marketplace.json        # 插件市场目录
.codex-plugin/
  plugin.json             # Codex 插件清单
.agents/plugins/
  marketplace.json        # Codex 插件市场目录
plugin.json               # 通用 Agent Plugins 清单（Codex 新格式）
.cursor-plugin/
  plugin.json             # Cursor 插件清单（上架 Cursor 市场用）
gemini-extension.json     # Gemini CLI 扩展清单，上下文入口 GEMINI.md
scripts/
  bump-version.sh         # 统一修改版本号
skills/
  aionforge/              # 入口：路由、契约、工具卡、共享 Prompt、forge CLI
    SKILL.md
    .env.example
    evals/
    references/
      contracts/          # 目录 / facts / 参考图角色 / 流程依赖
      tools/              # 每个 forge 命令一张工具卡
      print/              # 正反面、核心图标、撞色适配规则
      prompts/            # Prompt 模板
      catalog/            # 姿势、平台字体与配色
    scripts/              # forge CLI（uv 项目）
  aionforge-print/        # 阶段 1：印花提取、正反面分析、左胸核心小标
  aionforge-product/      # 阶段 2：T 恤实拍底色冲突适配、正反面合成
  aionforge-main/         # 阶段 3：模特锁脸换衣 + 正背面多姿势主图
  aionforge-detail/       # 阶段 4：基于主图与商品图生成详情卖点图
```

入口 Skill `aionforge` 先定 logo / 商品、锁事实，再按阶段调度对应的 `aionforge-*` 流程。流程 Skill 严格遵循「思考 → 事实锁定 → 生成 → 检查」四步闭环；命令参数在 `references/tools/` 的工具卡里，共享资料和 `forge` 只放在入口目录。

## 开发

```bash
cd skills/aionforge/scripts
uv sync
uv run pytest -q
uv run ruff check .

# 校验 SKILL.md 是否符合 Agent Skills 规范（在仓库根目录）
cd ../..
for d in skills/aionforge skills/aionforge-print skills/aionforge-product \
  skills/aionforge-main skills/aionforge-detail; do
  npx -y skills-ref validate "$d"
done
```

发布新版本：

```bash
scripts/bump-version.sh            # 查看各清单当前版本是否一致
scripts/bump-version.sh X.Y.Z      # 统一改版本号并刷新 uv.lock
git commit -am "chore: release vX.Y.Z" && git tag -a vX.Y.Z -m vX.Y.Z && git push --follow-tags
git archive --format=zip -o dist/skills.zip HEAD:skills
gh release create vX.Y.Z dist/skills.zip --title vX.Y.Z --generate-notes
```

## License

[MIT](LICENSE)
