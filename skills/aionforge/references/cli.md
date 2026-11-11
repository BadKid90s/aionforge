# forge CLI 全局约定

所有工具都是 `forge` 的确定性子命令。命令参数只写在 [tools/](tools/index.md) 的工具卡里；流程 Skill 只写「思考 → 事实锁定 → 生成 → 检查」逻辑，不复制命令。

## 调用方式

`forge` 是 `uv run --project <skill目录>/scripts forge` 的简写。`<skill目录>` 是 `skills/aionforge` 的绝对路径。

- 在**用户工作目录**执行，不要 cd 进 Skill 目录；`output/` 会建在当前目录。
- 首次运行 `uv` 会自动创建 `.venv` 并安装依赖。
- 查询版本：`forge --version`。

Key 读取顺序：进程环境 > 当前目录 `.env` > Skill 目录 `.env`。改完环境变量要重启 Agent。

## JSON 信封

所有命令都支持 `--json`，返回：

```json
{
  "ok": true,
  "run_dir": "/abs/path",
  "images": ["/abs/path/out.png"],
  "error": null,
  "...": "命令自己的字段会平铺在顶层"
}
```

失败时：

```json
{
  "ok": false,
  "run_dir": null,
  "images": [],
  "error": {
    "stage": "params | execution",
    "reason": "...",
    "suggestion": "..."
  }
}
```

退出码：`0` 成功，`1` 参数或执行失败。`verify` / `prompt check` 的检查项不通过也返回 `1`。

## 交付落点与中间存储

- 成品命令（`composite`、`generate`）写入 `--bucket`：`bg_white` / `main` / `detail`。
- 印花提取与适配命令（`cutout`、`extract-core-element`、`print adapt`）自动写入商品工作区的 `refs/`，不污染成品目录。

目录与命名见 [contracts/workspace.md](contracts/workspace.md)。

## 参考图角色

`--ref` 可重复；带角色写 `角色名=路径`：

```text
garment=...  garment_back=...  model=...  print=...  source=...  pose=...
```

每张图只承担一个角色，Prompt 里用角色名指代，不写「图1 / 图2」。完整语义见 [contracts/reference-roles.md](contracts/reference-roles.md)。

## 工具索引

| 工具 | 文档 |
| --- | --- |
| `doctor` | [tools/doctor.md](tools/doctor.md) |
| `product init` | [tools/product-init.md](tools/product-init.md) |
| `cutout` | [tools/cutout.md](tools/cutout.md) |
| `extract-core-element` | [tools/extract-core-element.md](tools/extract-core-element.md) |
| `print metrics` | [tools/print-metrics.md](tools/print-metrics.md) |
| `print adapt` | [tools/print-adapt.md](tools/print-adapt.md) |
| `composite` | [tools/composite.md](tools/composite.md) |
| `generate` | [tools/generate.md](tools/generate.md) |
| `verify` | [tools/verify.md](tools/verify.md) |
| `prompt check` | [tools/prompt-check.md](tools/prompt-check.md) |

## 常见错误

| 现象 | 处置 |
| --- | --- |
| 没有可用 Key | 跑 `doctor`，按 `suggestion` 配 Key；不要重试出图 |
| 401 / 403 | 配置或权限问题，不要重试 |
| 网络 / 超时 / 限流 | 同参数重试 1 次 |
| 参数错误 | 回工具卡核对参数，不要猜 |
| 图已生成但质检失败 | 改 Prompt 点名出错部位，同一 `--name` 重跑 |
