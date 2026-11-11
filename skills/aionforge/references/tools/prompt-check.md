# forge prompt check

| 项 | 值 |
| --- | --- |
| command | `forge prompt check` |
| kind | local（纯文本） |
| reads | Prompt 文件、可选 facts |
| writes | 无 |

对 Prompt 做静态检查：Hex 色号、图序号写法、`VISIBLE_TEXT_BLOCK`、印花原文是否逐字出现。不调用模型。

## 参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--file` / `-f` | 必填 | Prompt 文本文件 |
| `--facts` | 空 | facts.json；提供时检查印花文字 |
| `--visible-text` | 关闭 | 要求出现 `VISIBLE_TEXT_BLOCK` |
| `--json` | 关闭 | 输出 JSON 信封 |

## 输出

`issues[]`；有 issue 时退出码 1。非 JSON 输出逐条打印。

## 保证

- 不读图片、不调用模型。
- 检查的是格式与事实一致性，不是文案质量。

## 不适用

- 不要用它判断 Prompt 出图效果；那要靠生成后的看图质检。
- 不要用它替代 `verify`；`verify` 检查成品文件。

## 失败与处置

| issue | 处置 |
| --- | --- |
| 缺少 Hex | 从 `style_lock` 或 `typography.json` 补 6 位 Hex |
| 出现「图1 / 图2」 | 改成角色名：成衣图 / 模特图 / 印花图 |
| 缺少 `VISIBLE_TEXT_BLOCK` | 图内有文字时补文字块，文案用 `「...」` 包裹 |
| 印花原文不一致 | 按 `facts.print.text_exact` 逐字改 |

## 标准调用

```bash
forge prompt check --file <prompt.txt> --facts <product_dir>/facts.json --json
forge prompt check --file <prompt.txt> --facts <product_dir>/facts.json --visible-text --json
```
