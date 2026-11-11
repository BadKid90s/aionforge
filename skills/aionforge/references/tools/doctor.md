# forge doctor

| 项 | 值 |
| --- | --- |
| command | `forge doctor` |
| kind | local |
| reads | 配置、环境变量、网络、当前工作目录 |
| writes | 日志文件；`--deep` 会真实请求一次图片接口 |

检查图片模型配置、Key、网络、存储目录与日志是否可用。任何一项失败都应先修环境，不要继续出图。

## 参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--deep` | 关闭 | 真实 POST 一次出图接口，验证 Key 与模型权限 |
| `--json` | 关闭 | 输出 JSON 信封 |

## 输出

`checks[]`，每项含 `name` / `pass` / `detail` / `suggestion`。`ok` 为所有项都通过。

## 保证

- 只做检查，不改工作区、不出成品。
- 失败项带 `suggestion`，直接转告用户。

## 不适用

- 不是出图工具；不要用它验证 Prompt 或图片质量。
- 不要在没有 Key 时反复重试；先按 `suggestion` 配置。

## 失败与处置

| 现象 | 处置 |
| --- | --- |
| 没有可用 Key | 让用户配置环境变量或工作目录 `.env`，重启 Agent |
| 网络 / 401 / 403 | 按 `suggestion` 修配置，不要重试出图 |
| 存储不可写 | 检查当前工作目录权限或 `AIONFORGE_STORAGE_ROOT` |

## 标准调用

```bash
forge doctor --json
forge doctor --deep --json
```
