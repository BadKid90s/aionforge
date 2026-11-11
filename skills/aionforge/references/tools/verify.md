# forge verify

| 项 | 值 |
| --- | --- |
| command | `forge verify` |
| kind | local（纯 Pillow） |
| reads | 图片 |
| writes | 无 |

对成品做客观检查：文件、尺寸、比例、白底、alpha、印花白边与碎点。**只做确定性检查**，审美、商品事实、五官一致性由 Agent 看图判断。

## 参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--image` / `-i` | 必填 | 待检查图片 |
| `--ratio` | 空 | 目标比例 `W:H`，2% 容差 |
| `--white-bg` | 关闭 | 检查四边是否近纯白 |
| `--alpha` | 关闭 | 检查是否带 alpha 且不是全透明 / 全不透明 |
| `--print` | 关闭 | 印花检查：隐含 `--alpha`，并检查白边比例与 <4px 碎点 |
| `--min-side` | 480 | 最短边下限；检查印花时可传 0，因为印花短边经常小于成品图 |
| `--json` | 关闭 | 输出 JSON 信封 |

## 输出

`checks[]`，每项含 `name` / `pass` / `detail` / `suggestion`。`ok` 为所有项都通过；非 JSON 输出逐项打印 PASS / FAIL。

## 保证

- 不修改图片。
- 失败项给出可执行的 `suggestion`。
- `--print` 的 `white_edge` 阈值是 20%，`specks` 要求 0 个小于 4px 的 alpha 孤岛。

## 不适用

- 不要用它判断印花是否好看、文字是否写对、模特是否同一人。
- 不要用它检查 Prompt；Prompt 用 `prompt check`。

## 失败与处置

| 现象 | 处置 |
| --- | --- |
| `size` 失败 | 提高输出尺寸或换比例 |
| `ratio` 失败 | 用 `--fit expand` 重跑，不要用 `pad` |
| `white_bg` 失败 | 检查背景是否纯白，必要时重跑白底清理 |
| `print.white_edge` 失败 | 重新抠图或调小 `--tolerance` |
| `print.specks` 失败 | 加 `--denoise 4` 重新提取 |

## 标准调用

```bash
forge verify --image <成品.png> --ratio 1:1 --white-bg --json
forge verify --image <印花.png> --print --json
```
