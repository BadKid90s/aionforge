# forge product init

| 项 | 值 |
| --- | --- |
| command | `forge product init` |
| kind | local |
| reads | 无 |
| writes | `output/<logo>/{bg_white,main,detail}`、`output/<logo>/.forge/products/<product>/`、`project.json`、`facts.json`、`manifest.json`、`refs/`、`prompts/`、`tmp/`、`history/` |

一步创建或复用 logo 工作区（含 `bg_white` / `main` / `detail` 三个交付目录）与商品工作区，生成 `facts.json` 和 `manifest.json` 模板。幂等：已存在的配置文件不会被覆盖。

## 参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--logo` / `-l` | 必填 | 图案 / 设计名，作为 `output/` 下第一层目录 |
| `--product` / `-p` | 必填 | 衣服款式短名，如 `short` / `long` / `tee` / `hoodie` |
| `--root` | `output` | 成品根目录 |
| `--json` | 关闭 | 输出 JSON 信封 |

## 输出

JSON 信封的 `extra.product_dir` 是后续所有命令要带的 `--product-dir`；`extra.facts` 是 `facts.json` 路径；`extra.buckets` 是三个成品目录列表。

## 保证

- 不覆盖用户已经编辑过的 `facts.json`。
- 自动补齐缺失目录，不创建成品图。

## 不适用

- 不要用图案名当 `--product`；product 是款式短名。
- 不要为同一个 logo + 款式重复建不同目录；全流程复用同一个 `product_dir`。

## 失败与处置

| 现象 | 处置 |
| --- | --- |
| logo / product 为空 | 先从素材推断或问用户 |
| 目录不可写 | 检查 `--root` 或当前目录权限 |

## 标准调用

```bash
forge product init --logo <logo> --product <product> --json
```
