# AionForge

女装电商 AI 出图插件。把 logo 图案稿、空白成衣、模特照片丢给 Agent，它会从图案主标题推断 logo、从空白衣文件夹推断款式，锁定商品细节，按颜色合成白底成衣、把成衣穿到模特身上、派生姿势，并在你点名时补 SKU 规格图和详情图。

一组可互相引用的 Skill：入口 `aionforge` 负责调度、锁事实和质检；具体步骤在 `aionforge-white`、`aionforge-main`、`aionforge-sku`、`aionforge-detail`。

- **白底商品图**：把 logo 图案合成到每个颜色的白底空白成衣，按颜色输出 `bg_white`
- **模特换衣**：保留模特原脸和眼神，把白底成衣穿到模特身上，输出 `main`
- **姿势展示**：基于锚点主图派生多个机位 / 姿势，跨图锁同一张脸、同一件衣
- **SKU 配色规格图**：用 main 主图或产品图当母版，把每个颜色的白底成衣套进同一构图
- **详情图**：卖点信息图、放大镜气泡、标注线、60:40 分屏、三角度、一衣多穿、3D 隐形人台

输出以 **logo 为第一层目录**，每个 logo 下固定四个交付目录：`bg_white` / `main` / `sku` / `detail`。提示词、参考图、事实和 manifest 收在 `.forge`，不污染成品目录。

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

- 「把这个 logo 图案合成到这件短袖的黑、白、浅灰三个颜色上」
- 「保留这个模特的脸，把这张白底成衣穿上去，再出 6 个姿势」
- 「用这张 main 主图当母版，出黑、白、浅灰的 SKU 规格图」
- 「给这个图案的短袖出一套详情卖点图，平台是拼多多」

Agent 会先看图、从图案主标题推断 logo、从空白衣文件夹推断款式，把商品事实列给你确认；确认后先出白底，再出模特图，SKU / 详情只在你点名时生成。

## 输出目录

```text
output/
  锁定目标/
    bg_white/
      short-black.png
      short-白.png
      short-浅灰.png
    main/
      short-black-hero.png
      short-black-walk.png
      short-black-studio-3q.png
    sku/
      short-black.png
      short-白.png
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

- `bg_white` 是印花合成后的白底成衣，也是后续 main / sku / detail 的衣服唯一真相源。
- `main` 是模特换衣与姿势展示；先出 `hero`，后续姿势从它派生。
- `sku` / `detail` 只有用户点名才生成。
- 同名重跑覆盖成品，旧图自动进 `history/`；不会堆出一串时间戳目录。

## 工作流

| 意图 | Skill | 输出 |
| --- | --- | --- |
| 提取印花、合成白底、每个颜色一张白底衣图 | `aionforge-white` | `bg_white/<product>-<color>.png` |
| 模特换衣、保留原脸、多机位 / 多姿势 | `aionforge-main` | `main/<product>-<color>-<pose>.png` |
| SKU 规格图、按母版套多个配色 | `aionforge-sku` | `sku/<product>-<color>.png` |
| 详情图、卖点信息图、多场景、隐形人台 | `aionforge-detail` | `detail/<product>-<detail-id>.png` |

默认所有颜色都出；用户点名只出一个颜色时只跑该色。SKU 和详情可以用 `bg_white` 当衣服参考，也可以把 main 的锚点成片当 `source` 或母版。

## 常见问题

**doctor 提示没有可用 Key**：Key 没被读到。环境变量方式要重启 Agent；`.env` 方式要确认文件在 Agent 的当前工作目录。

**成品带素材站水印**：`logo/` 里的预览稿水印不会被当成图案的一部分。换有授权的无水印源文件再跑，不要把带水印的预览图直接上架。

**401 / 403**：Key 无效、过期，或账户没开通图片模型权限。

**找不到 uv**：安装后重开终端，或把 `~/.local/bin` 加进 `PATH`。

**中断了想续跑**：告诉 Agent 继续上次的任务。商品工作区、`facts.json`、`manifest.json` 都在 `output/<logo>/.forge/products/<product>/`，会沿用同一个 `product_dir` 接着出剩下的图。

**想换 logo / 商品名**：重新跑 `forge workspace init` / `forge product init`；已存在的 `facts.json` 不会被覆盖。

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
| `AIONFORGE_STORAGE_ROOT` | `~/.aionforge` | 数据目录 |
| `AIONFORGE_LOG_LEVEL` | `INFO` | 日志级别 |
| `AIONFORGE_LOG_FILE` | `logs/forge.log` | 日志文件（相对当前目录） |

读取顺序：进程环境 > 当前目录 `.env` > Skill `.env`。一等供应商的专用 Base 优先于 `AIONFORGE_API_BASE`（后者只用于其它 OpenAI 兼容网关）。

### forge CLI

Agent 会自动调用，一般不用手动跑。手动调用：`uv run --project skills/aionforge/scripts forge <命令>`

| 命令 | 作用 |
| --- | --- |
| `forge doctor --json` | 检查配置、Key、连通性、数据目录 |
| `forge workspace init --logo <logo> --json` | 创建 logo 工作区和四个交付目录 |
| `forge product init --logo <logo> --product <product> --json` | 创建商品工作区、facts 模板、manifest |
| `forge cutout --input <logo稿> --product-dir <dir> --name <id> --json` | 本地抠平面 logo 稿，输出透明底到 `refs/` |
| `forge generate --product-dir <dir> --bucket <bucket> --prompt-file <txt> --ref <图> --name <id> --json` | prompt + 参考图 → 一张成品，落到 bucket |
| `forge generate --product-dir <dir> --store refs --prompt-file <txt> --ref <图> --name <id> --json` | 中间产物（印花 / 白底素材）落到商品工作区 |
| `forge verify --image <图> --ratio 1:1 --white-bg --json` | 校验尺寸、比例、白底、alpha |
| `forge prompt check --file <txt> --facts <facts.json> --json` | 检查 Hex、图序号、VISIBLE_TEXT_BLOCK、印花原文 |
| `forge list --logo <logo> --json` | 列出四个 bucket 的成品 |

完整参数见 [`references/cli.md`](skills/aionforge/references/cli.md)。

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
  aionforge/              # 入口：调度、标准流程、全局规则、forge CLI
    SKILL.md
    .env.example
    evals/
    references/           # 共享 Prompt 模板、姿势/场景/风格/字体目录
    scripts/              # forge CLI（uv 项目）
  aionforge-white/        # 印花提取 + 白底合成
  aionforge-main/         # 模特换衣 + 姿势裂变
  aionforge-sku/          # SKU 配色规格图
  aionforge-detail/       # 详情图与卖点信息图
```

入口 Skill `aionforge` 先定 logo / 商品、锁事实，再加载对应的 `aionforge-*` Skill。共享资料和 `forge` 只放在入口目录。

## 开发

```bash
cd skills/aionforge/scripts
uv sync
uv run pytest -q
uv run ruff check .
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
