# T 恤展示姿势套餐与详情图型菜单

`aionforge-main` 用它挑选模特主图姿势，`aionforge-detail` 用它挑选详情页板式。

## main 模特姿势套餐

姿势数据定义在 `catalog/looks.json`。每条 shot 已按万象公式写好【场景】【风格】【镜头语言】【主体动作】，编写 Prompt 时整段粘贴。

| 用户关键词 | pack | 适用场景说明 |
| --- | --- | --- |
| 自拍 / 对镜 / 镜子 / 挡脸 | `mirror` | 手机挡脸对镜拍、拱形镜、单手插兜、拎包、微侧头 |
| 户外 / 街拍 / 草坪 / 街边 / 店门口 | `outdoor` | 阳光草坪站姿、街边自然行走、店门口休闲、回眸展示后背 |
| 咖啡 / 饮品 / 吧台 / 窗边 / 居家 | `cafe` | 吧台高脚坐、窗边手持饮品、石阶坐姿、沙发松弛感 |
| 半身 / 人像 / 扶发 / 抱臂 / 坐姿 | `portrait` | 近景半身突出左胸小标或胸前主印花、手扶发、抱臂 |
| 车内 / 副驾 / 后排 | `car` | 车内自然坐姿、靠窗侧脸 |
| 平铺 / 挂拍 / 静物 | `flat` | 成衣平铺、自然挂拍、领口与印花半身特写 |
| 走 / 动态 / lookbook | `walk` | 动态迈步、行进中回眸（适合展示背面大印花） |
| 窗光 / 生活 / 室内 / 种草 | `lifestyle` | 柔和窗光室内倚靠、坐姿、自然生活感 |
| 特写 / 细节 / 面料 / 工艺 | `detail` | 领口罗纹、纯棉面料、印花微距 |
| 未指定 / 默认主图 | `studio`（默认） | 棚拍正面、45° 微侧、侧背回眸（展示背面主印花）、半身 |

### 姿势选型铁律

1. **正反面印花联动**：
   - 仅有正面主印花：以正面、45° 微侧、半身特写为主。
   - **背面主印花 + 左胸核心小标**：必须包含**正面镜头**（展示左胸核心小图标与前胸版型，传 `garment`）和 **90°–135° 侧背 / 过肩回眸镜头**（展示后背大印花，传 `garment_back`）。
2. **锚点先行**：每张派生姿势图的 `source` 必须是同色已通过质检的 `hero` 锚点主图。
3. **头随身转**：严禁连续 3 张同一角度；回眸或侧身镜头头颈必须自然随身体转向。

## detail 详情图型菜单

详情页承接 `main` 主图与 `bg_white` 实拍合成图，每张图专注讲透一个核心卖点：

| 图型 ID | 解决的买家问题 | Prompt 模板 | 构图与参考图要点 |
| --- | --- | --- | --- |
| `detail-three-angle` | 正面左胸小标与背面大印花怎么呼应？ | [prompts/infographic.md](prompts/infographic.md) 三角度同框 | 正面 / 微侧 / 背面三栏同框；同时传 `garment` + `garment_back` + `source`；背面栏严禁扭头露正脸 |
| `detail-infographic` | 印花工艺、领口与面料有什么亮点？ | [prompts/infographic.md](prompts/infographic.md)（选 `magnifier` 或 `asymmetric`） | 留白 ≥45%；放大镜气泡指向左胸小标、背面胶印肌理、罗纹领口；60:40 分屏左放模特主图、右放两处微距 |
| `detail-benefit` | 上身版型显瘦吗？透气亲肤吗？ | [prompts/infographic.md](prompts/infographic.md)（选 `icon-list` 或 `annotation`） | 左衣右签或剪裁指示线（落肩袖、宽松直筒、双车线下摆） |
| `detail-multi-scene` | 日常不同场合怎么搭？ | [prompts/infographic.md](prompts/infographic.md) 多场景分屏 | 场景取自 `facts.target_scenes`，保持同一模特（`source`）与同一件 T 恤（`garment`） |
| `detail-scene` | 上身整体氛围感如何？ | [prompts/vary.md](prompts/vary.md) | 全身或七分生活场景收尾 |
