# 流程依赖与四步闭环契约

四个核心流程按业务阶段串联，共用同一个商品工作区（`product_dir`）。
**工具层**只提供确定性原子能力；**流程层**在每个阶段严格执行 **「思考 (Think) → 事实锁定 (Lock) → 生成 (Generate) → 检查 (Verify)」** 四步闭环，跨阶段只通过 `facts.json` 和通过质检的成品路径交接。

```text
素材（印花图案 / T恤正背面实拍图 / 模特图）
  ↓
[阶段 1: aionforge-print] 印花提取与正反面分析
  思考（指标测量 + 正反面判定 + 背面左胸核心图标选型）
  → 事实锁定（placements 确认）
  → 生成（cutout 抠主印花 + extract-core-element 提左胸小标）
  → 检查（verify --print 透明通道与完整性校验）
  ↓ facts.print.placements / refs/*
[阶段 2: aionforge-product] T恤实拍撞色适配与商品合成
  思考（实拍底图清点 + 逐色对比度冲突分析）
  → 事实锁定（colors[].color_adaptation 策略锁定）
  → 生成（print adapt 调色适配 + composite 正背面实拍合成）
  → 检查（verify + 看图质检 → 写入 bg_white / canonical.garment*）
  ↓ bg_white / bg_white_back (唯一衣服真相源)
[阶段 3: aionforge-main] 模特锁脸换衣与多姿势主图
  思考（模特五官解析 + 旧衣擦除清单 + 正背面姿势规划）
  → 事实锁定（facts.model 与拍摄计划锁定）
  → 生成（先出 hero 锚点 → 派生正面与背面回眸多姿势主图）
  → 检查（prompt check + verify + 锁脸/锁衣/头随身转质检 → canonical.anchor）
  ↓ main / canonical.anchor + bg_white*
[阶段 4: aionforge-detail] 详情卖点图
  思考（结合主图与实拍商品图提炼卖点与板式）
  → 事实锁定（selling_points + style_lock + 角色映射锁定）
  → 生成（逐屏写 Prompt → prompt check → generate）
  → 检查（verify + 版式留白/文字/货对板质检 → detail/*）
```

## 阶段职责与交接门槛

| 阶段流程 | 读取真相源 | 写入真相源与产物 | 准出门槛（Check） |
| --- | --- | --- | --- |
| `aionforge-print` | 原始印花稿、用户偏好 | `refs/<product>-print.png`、`refs/<product>-core.png`、`facts.print.*` | 正反面方案与左胸小标经用户确认；透明 PNG 无白边碎点、核心图标完整 |
| `aionforge-product` | `facts.print.placements`、各色正/背面 T 恤实拍 | `refs/*-fit.png`、`bg_white/*`、`canonical.garment*` | 撞色已适配（对比度 ≥3:1）；正背面不串位；文字零重绘 |
| `aionforge-main` | `canonical.garment`、`canonical.garment_back`、模特图 | `main/*`、`canonical.anchor` | 锚点主图先过检；五官一致、头随姿势自然转动、衣服与 `bg_white` 一致 |
| `aionforge-detail` | `canonical.anchor`（模特主图）+ `canonical.garment*`（商品图） | `detail/*`、`facts.selling_points` | 模特与衣服同源一致；留白 ≥45%；汉字清晰无乱码 |

## 全局硬性规则

1. **环境自检先行**：开始前先跑 `doctor` 确认配置、Key、网络与目录可写；失败立即告知用户并停止。
2. **未经事实锁定禁止生成**：`facts.json` 的商品事实、正反面 `placements`、左胸小标及撞色适配方案必须先锁定并经用户确认。
3. **真相源单向传递**：
   - 没有通过质检的正面 `bg_white`，禁止进入 `main` 或 `detail`。
   - 有背面主印花时，必须先有背面实拍合成的 `bg_white_back`，才能生成背面模特姿势或正反对比详情图；缺背面实拍底图时停下请用户补图。
4. **单张闭环与失败隔离**：每次生成单张图片并立即质检；不合格只用同一 `--name` 重做该张（旧图自动归档至 `history/`），连续两次失败记入 `manifest.json`。

参考图角色见 [reference-roles.md](reference-roles.md)，目录契约见 [workspace.md](workspace.md)，事实结构见 [facts.md](facts.md)。
