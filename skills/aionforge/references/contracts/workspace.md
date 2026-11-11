# 目录契约

一个 logo + 一个商品 = 一个商品工作区。三个成品 bucket 只放通过质检的交付图；`.forge` 收纳事实、Prompt、透明印花、适配印花、manifest 和历史版本。

## 目录树

```text
output/<logo>/
  bg_white/<product>-<color>.png            # 正面 T 恤实拍合成商品图（后续正面衣服唯一真相源）
  bg_white/<product>-<color>-back.png       # 背面 T 恤实拍合成商品图（有背面印花时存在）
  main/<product>-<color>-<pose>.png         # 模特锁脸换衣主图与多姿势图
  detail/<product>-<color>-<detail-id>.png  # 基于主图和商品图生成的详情图
  .forge/
    workspace.json
    products/<product>/
      project.json
      facts.json
      manifest.json
      refs/        # 透明主印花、左胸核心小图标、各色撞色适配印花、模特参考图
      prompts/     # 按 bucket / store 分目录的 Prompt 文本
      tmp/         # 抠图与扩图等中间文件
      history/     # 同名重跑前的旧版本自动归档
    history/
```

## 命名规范

- `<product>` 是衣服款式短名：`short` / `long` / `tee` / `hoodie`。
- `<color>` 用英文短名或素材中文色名：`black` / `white` / `白` / `浅灰`。
- 背面实拍合成商品图固定加 `-back`；正面不加后缀。
- 模特主图锚点固定为 `<product>-<color>-hero.png`，派生姿势用 `looks.json` 的 shot id；详情图用 `<detail-id>`。
- 单色商品可省略 color，例如 `<product>-hero.png`。

## bucket 职责边界

| bucket | 放什么 | 绝不放什么 |
| --- | --- | --- |
| `bg_white` | 印花合成后的正面 T 恤实拍图；`-back` 为背面实拍合成图 | 原始未印花的空白衣、透明印花 PNG、Prompt |
| `main` | 模特锁脸换衣锚点主图与多姿势主图 | 原始模特图、姿势参考图 |
| `detail` | 卖点信息图、正反对比图、微距细节图、多场景详情图 | 中间素材图 |

## 同名重跑与历史归档

- 写入目标路径前，自动将同名旧文件备份到商品 `history/`，随后覆盖目标路径。
- 不要在成品文件名里拼接时间戳；始终保持干净可预测的文件名。

## 路径解析顺序

`facts.json` 里的相对路径通过 `Product.resolve` 解析：
1. 先按商品工作区根解析（如 `refs/short-print.png`、`prompts/...`）。
2. 再按 logo 工作区根解析（如 `bg_white/short-black.png`、`main/short-black-hero.png`）。
