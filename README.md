# AionForge

女装电商 AI 出图插件：Agent 负责看图、锁商品事实、写计划和逐图 Prompt、质检；随插件附带的 `forge` CLI 每次只出一张图。

覆盖印花提取（抠出透明底图案）、印花合成（图案贴回白衣）、模特换衣（锁五官）、电商图多机位裂变、主图 + 详情整套上架图（拼多多 / 淘宝 / 京东 / 抖音 / Amazon 等）。

支持 Claude Code、Grok Build、Codex（ChatGPT 桌面版）。

## 前置条件

1. 安装 [uv](https://docs.astral.sh/uv/)：`curl -LsSf https://astral.sh/uv/install.sh | sh`
2. 至少一个图片模型 Key：Grok（`XAI_API_KEY`）/ OpenAI（`OPENAI_API_KEY`）/ 通义万相（`DASHSCOPE_API_KEY`）/ 豆包 Seedream（`ARK_API_KEY`）/ 任意 OpenAI 兼容网关（`AIONFORGE_API_BASE` + `AIONFORGE_API_KEY`）

## 安装

### Claude Code

```
/plugin marketplace add BadKid90s/aionforge
/plugin install aionforge@aionforge
```

Claude Code 2.1.275 及以上也可以一步安装：`/plugin install aionforge --marketplace BadKid90s/aionforge`

### Grok Build

```bash
grok plugin install BadKid90s/aionforge
```

### Codex / ChatGPT 桌面版

```bash
codex plugin marketplace add BadKid90s/aionforge
```

然后在 ChatGPT 桌面版的 Plugins 里安装 `aionforge`。

### 只要 Skill

把 `skills/aionforge/` 整个目录拷进任意 Agent 的 skills 目录（如 `~/.claude/skills/`），或下载 Release 里的 `skill.zip` 解压进去。

## 配置 Key

Key 查找顺序：环境变量 > 当前工作目录 `.env` > Skill 根目录 `.env`。推荐直接导出环境变量：

```bash
export XAI_API_KEY=xai-...
```

或者在工作目录放一个 `.env`，模板见 [`skills/aionforge/.env.example`](skills/aionforge/.env.example)。

## 使用

装好后直接对 Agent 说，例如：

- 「提取这件 T 恤胸前的印花」
- 「把这个图案印到白 T 上」
- 「把这件成衣穿到这个模特身上」
- 「这张再裂变 6 个机位」
- 「这件吊带出一套拼多多主图」

Agent 第一次会先跑 `forge doctor` 检查 Key 和网络，uv 会自动安装依赖。生成结果在当前目录的 `output/<工作流>/<任务>/images/`。

## 结构

```
.claude-plugin/
  plugin.json             # Claude Code / Grok Build 插件清单
  marketplace.json        # 插件市场目录
plugin.json               # Codex 插件清单
.agents/plugins/
  marketplace.json        # Codex 插件市场目录
skills/aionforge/
  SKILL.md                # 入口：流程、全局规则、资源地图
  .env.example            # Key 模板
  references/
    workflows/            # 每个工作流的步骤
    prompts/              # Prompt 模板
    catalog/              # 姿势 / 场景 / 风格 JSON（CLI 也读取）
    cli.md analysis.md style-lock.md shots-womenswear.md platforms.md
  scripts/                # forge CLI（uv 项目）
    pyproject.toml uv.lock
    aionforge/            # Python 包
    tests/
```

## forge CLI

下面的 `forge` 指 `uv run --project skills/aionforge/scripts forge`。

| 命令 | 作用 |
| --- | --- |
| `forge doctor --json` | 配置、Key、连通性、数据目录 |
| `forge job init --workflow <id> --slug <短名> --json` | 创建空任务目录 |
| `forge generate --job-dir <run_dir> --prompt-file <txt> --ref <图> --name <id> --json` | prompt + 可选参考图 → 一张图 |

换装、提取、合成、裂变的区别全在 Prompt 里，完整参数见 [`references/cli.md`](skills/aionforge/references/cli.md)。

## 开发

```bash
cd skills/aionforge/scripts
uv sync
uv run pytest -q
uv run ruff check .
```

打包单独的 Skill：

```bash
git archive --format=zip -o dist/skill.zip HEAD:skills aionforge
```

## License

[MIT](LICENSE)
