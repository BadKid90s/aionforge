# forge CLI 参考

出图一律调用本 Skill 自带的 CLI。下文 `forge ...` 都是 `uv run --project <skill目录>/scripts forge ...` 的简写，在用户工作目录执行；首次运行 uv 会自动装依赖。

Key 从环境变量读取，其次是当前目录 `.env`，再其次是 `<skill目录>/.env`（模板 `<skill目录>/.env.example`）。

## doctor

```bash
forge doctor --json
```

检查配置、Key、连通性、数据目录。任一项 `pass: false` 时把 `suggestion` 告诉用户并停下。

## job init

```bash
forge job init --workflow <extract|compose|tryon|vary|sku|pdp|deconstruct> --slug <短名> --json
```

| 参数 | 说明 |
| --- | --- |
| `--workflow` / `-w` | 工作流 id（`extract` / `compose` / `tryon` / `vary` / `sku` / `pdp` / `deconstruct`），默认 `pdp` |
| `--slug` / `-s` | 任务短名，进入目录名 |
| `--output-dir` | 任务根目录，默认 `output/<workflow>` |

生成的目录：

```
<run_dir>/
  project.json
  facts.json          # Agent 写，用户确认后的商品事实
  plan.json           # Agent 写，用户批准后的逐图任务
  manifest.json       # CLI 更新：每张 ok / failed
  images/
  work/prompts/
```

## generate

每次出一张图，写入 `<run_dir>/images/<name>.png`。

| 参数 | 说明 |
| --- | --- |
| `--prompt` / `-p` | 提示词字符串，与 `--prompt-file` 二选一 |
| `--prompt-file` | 从文件读提示词（推荐，放在 `work/prompts/`） |
| `--ref` / `-r` | 参考图，可重复；带角色写 `garment=./a.png`、`garment_back=./a_back.png`、`model=./b.jpg`、`print=`、`source=`、`style=`、`layout=`（严禁传入 `LONG_PAGE` 竖长条拼接图） |
| `--name` / `-n` | 结果文件名（不含扩展名），默认 `image` |
| `--ratio` | `W:H`，输出宽高均大于 480px |
| `--fit` | 比例不符时的处理：`expand`（默认，扩图铺满）/ `crop`（居中裁切）/ `pad`（不要用） |
| `--cutout` | 白底转透明并按图案裁切，本地处理 |
| `--padding` | `--cutout` 的透明边距像素，默认 8 |
| `--job-dir` | 已有任务目录 |
| `--output-dir` | 不给 `--job-dir` 时新建任务的根目录 |
| `--json` | 输出 JSON 信封 |

```bash
# 通用
forge generate --job-dir <run_dir> --prompt-file <run_dir>/work/prompts/main-01.txt \
  --ref garment.png --name main-01 --ratio 1:1 --json

# 换装
forge generate --job-dir <run_dir> --prompt-file <run_dir>/work/prompts/tryon-01.txt \
  --ref garment=./a.png --ref model=./b.jpg --name tryon-01 --json

# 竞品参考图版式迁移（仅限单屏参考图 SINGLE_POSTER）
forge generate --job-dir <run_dir> --prompt-file <run_dir>/work/prompts/deconstruct-01-layout.txt \
  --ref garment=./a.png --ref layout=./ref_poster.jpg --name deconstruct-01-layout --ratio 3:4 --json

# SKU 配色规格图
forge generate --job-dir <run_dir> --prompt-file <run_dir>/work/prompts/sku-black.txt \
  --ref source=./master.jpg --ref garment=./black.png --name sku-black --json

# 印花提取
forge generate --job-dir <run_dir> --prompt-file <run_dir>/work/prompts/print.txt \
  --ref ./photo.jpg --name print --cutout --json
```

## JSON 信封

```json
{"ok": true, "run_dir": "...", "images": ["..."], "error": null}
```

`ok: false` 时看 `error` 的 reason 分诊（见 SKILL.md「错误分诊」）。失败只重试该张 1 次。
