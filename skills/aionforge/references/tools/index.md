# 工具索引

流程 Skill 只按名称引用工具，不复制命令与参数。调用任何工具前先读对应工具卡；不要凭记忆拼参数。

| 工具 | 一句话 | 类型 | 文档 |
| --- | --- | --- | --- |
| `doctor` | 检查配置、Key、网络、存储与日志 | local | [doctor.md](doctor.md) |
| `product init` | 创建 logo 与商品工作区、三个交付目录、facts 与 manifest 模板 | local | [product-init.md](product-init.md) |
| `cutout` | 平面印花抠图，输出透明 PNG | hybrid | [cutout.md](cutout.md) |
| `extract-core-element` | AI 语义提取一枚完整核心图标（左胸小标） | model | [extract-core-element.md](extract-core-element.md) |
| `print metrics` | 印花客观体检：比例、色数、细节、笔画 | local | [print-metrics.md](print-metrics.md) |
| `print adapt` | 按成衣底色重映射印花颜色，提升对比度 | local | [print-adapt.md](print-adapt.md) |
| `composite` | 本地 alpha 合成印花到成衣实拍，不重绘文字 | local | [composite.md](composite.md) |
| `generate` | 模型生成成品图（模特主图 / 详情图），一张一次 | model | [generate.md](generate.md) |
| `verify` | 尺寸、比例、白底、透明印花质量检查 | local | [verify.md](verify.md) |
| `prompt check` | Prompt 静态检查：Hex、图序号、文字块、印花原文 | local | [prompt-check.md](prompt-check.md) |

全局调用方式、JSON 信封、bucket 与参考图角色语法见 [cli.md](../cli.md)。

## 选择原则

- 能在本地确定性完成的，不用模型：提取优先 `cutout`，合成优先 `composite`，调色优先 `print adapt`。
- 需要语义理解或生成实景时才用模型：`extract-core-element` 提取左胸核心图标，`generate` 出模特主图 / 详情图。
- 一张成品一次 `generate`；不要试图一次出多张。
