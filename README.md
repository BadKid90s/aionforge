# AionForge

女装电商 AI 出图插件。把衣服照片、模特照片、竞品参考图或印花丢给 Agent，它会看图锁定商品细节、写出图计划、逐张生成并自己质检。

- **印花提取**：从衣服照片抠出透明底图案
- **印花合成**：把图案印回白底成衣
- **模特换衣**：把成衣穿到指定模特身上，五官不变
- **多机位裂变**：同一张成片扩展出多个机位 / 姿势
- **竞品参考反推迁移**：拆解标杆海报的构图、留白与光影色调，1:1 或 4 向裂变迁移到自家成衣
- **整套上架图**：G1–G5 高转化主图漏斗 + 详情图（含 4 类高审美卖点信息图、3D 隐形人台立体陈列、6 大平台独立字体与排版美学），适配拼多多 / 淘宝 / 京东 / 抖音小红书 / Amazon / Shopify

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

> 其他 Agent：从 [Releases](https://github.com/BadKid90s/aionforge/releases) 下载 `skill.zip`，解压到 Agent 的 skills 目录（如 `~/.claude/skills/`）。

### 3. 配置图片模型 Key

至少配一个，任选其一：

| 供应商 | 环境变量 | 默认模型 | 获取 Key |
| --- | --- | --- | --- |
| xAI Grok | `XAI_API_KEY` | `grok-imagine-image-2.0` | [console.x.ai](https://console.x.ai) |
| OpenAI | `OPENAI_API_KEY` | `gpt-image-2.5-sunburst` | [platform.openai.com](https://platform.openai.com/api-keys) |
| 阿里通义万相 | `DASHSCOPE_API_KEY` | `wanx2.1-imageedit` | [阿里云百炼](https://bailian.console.aliyun.com) |
| 火山引擎豆包 Seedream | `ARK_API_KEY` | `seedream-4.0` | [火山方舟](https://console.volcengine.com/ark) |
| OpenAI 兼容网关 | `AIONFORGE_API_BASE` + `AIONFORGE_API_KEY` | 用 `AIONFORGE_IMAGE_MODEL` 指定 | 你的网关 |

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

> 配了多个 Key 时按 网关 > Grok > OpenAI > 通义万相 > 豆包 的顺序自动选；想指定就加 `AIONFORGE_PROVIDER=openai`（可选 `grok` / `openai` / `dashscope` / `ark` / `custom`），换模型用 `AIONFORGE_IMAGE_MODEL`。

### 4. 开始出图

在放素材的目录启动 Agent，先说：

```
帮我检查一下 aionforge 的环境
```

Agent 会跑 `forge doctor`，Key、网络、目录都通过就可以用了。然后把图片拖进对话框：

- 「提取这件 T 恤胸前的印花」
- 「把这个图案印到这件白 T 上」
- 「把这件成衣穿到这个模特身上」
- 「这张再裂变 6 个机位」
- 「参考这张竞品海报的排版和色调，出我的连衣裙」
- 「这件吊带出一套拼多多主图和卖点信息图」

Agent 会先让你确认商品细节和出图计划，确认后逐张生成。成品在当前目录的 `output/<工作流>/<任务>/images/`。说「你决定，直接出」可以跳过确认。

## 常见问题

**doctor 提示没有可用 Key**：Key 没被读到。环境变量方式要重启 Agent；`.env` 方式要确认文件在 Agent 的当前工作目录。

**401 / 403**：Key 无效、过期，或账户没开通图片模型权限。

**找不到 uv**：安装后重开终端，或把 `~/.local/bin` 加进 `PATH`。

**中断了想续跑**：告诉 Agent 继续上次的任务，它会沿用同一个任务目录接着出剩下的图。

**更新插件**：`npx skills update`；Claude Code 里 `/plugin marketplace update aionforge`；Grok 用 `grok plugin update aionforge`；Gemini 用 `gemini extensions update aionforge`。

## 进阶

### 全部配置项

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `AIONFORGE_PROVIDER` | 自动 | 强制使用某个供应商 |
| `AIONFORGE_IMAGE_MODEL` | 见上表 | 覆盖默认模型 |
| `AIONFORGE_API_BASE` | — | OpenAI 兼容网关地址 |
| `AIONFORGE_STORAGE_ROOT` | `~/.aionforge` | 数据目录 |
| `AIONFORGE_LOG_LEVEL` | `INFO` | 日志级别 |
| `AIONFORGE_LOG_FILE` | `logs/forge.log` | 日志文件（相对当前目录） |

读取顺序：环境变量 > 当前目录 `.env` > Skill 根目录 `.env`。

### forge CLI

Agent 会自动调用，一般不用手动跑。手动调用：`uv run --project skills/aionforge/scripts forge <命令>`

| 命令 | 作用 |
| --- | --- |
| `forge doctor --json` | 检查配置、Key、连通性、数据目录 |
| `forge job init --workflow <id> --slug <短名> --json` | 创建任务目录 |
| `forge generate --job-dir <run_dir> --prompt-file <txt> --ref <图> --name <id> --json` | prompt + 参考图 → 一张图 |

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
skills/aionforge/
  SKILL.md                # 入口：流程、全局规则、资源地图
  .env.example            # 配置模板
  evals/                  # 触发与行为回归评测集
  references/             # 工作流步骤、Prompt 模板、姿势/场景/风格/字体目录
  scripts/                # forge CLI（uv 项目）
```

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
git archive --format=zip -o dist/skill.zip HEAD:skills aionforge
gh release create vX.Y.Z dist/skill.zip --title vX.Y.Z --generate-notes
```

## License

[MIT](LICENSE)
