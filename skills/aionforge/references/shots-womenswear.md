# 女装姿势套餐与详情图型

`main` 用它选姿势，`detail` 用它选详情图型。图型是菜单，不是固定槽位；用户点名就照做。

## main 姿势套餐

姿势数据在 `catalog/looks.json`。每条 shot 已按万象公式写好【场景】【风格】【镜头语言】【主体动作】，Prompt 里整段粘贴，不要拆开重配。

| 用户关键词 | pack | 说明 |
| --- | --- | --- |
| 自拍 / 对镜 / 镜子 / 挡脸 | `mirror` | 手机挡脸、拱形镜、插兜、拎包、侧头 |
| 户外 / 街拍 / 草坪 / 街边 / 店门口 / 自然光 | `outdoor` | 草坪站姿、抬臂扶帽、街边行走、路边蹲姿、店门口 |
| 咖啡 / 饮品 / 吧台 / 窗边 / 居家 / 客厅 / 周末 | `cafe` | 吧台高脚坐、窗边饮品、石阶坐、沙发抱膝 |
| 半身 / 人像 / 扶发 / 抱臂 / 坐姿 | `portrait` | 手扶发、抱臂、矮凳坐、低头侧脸 |
| 车内 / 副驾 / 后排 | `car` | 车内坐姿、靠窗侧脸 |
| 平铺 / 挂拍 / 静物 / 净版 | `flat` | 白底平铺、隐形挂拍、领口图案半身 |
| 走 / 动态 / lookbook | `walk` | 行进、回头、停步、走远 |
| 窗光 / 生活 / 室内 / 种草 | `lifestyle` | 窗边、倚靠、坐姿、低头、吧凳、迈步 |
| 特写 / 细节 / 面料 / 工艺 | `detail` | 领口、面料、印花微距 |
| 没点名 / 主图 | `studio`（默认） | 棚拍正侧背、半身、下摆、口袋、发丝、侧背、扭身 |

`mirror` / `outdoor` / `cafe` / `car` 来自真实店铺主图的高频场景：镜面自拍、公园草坪、咖啡馆窗台、车内出行。用户素材是街拍或竞品图时，只映射姿势、机位和风格，不复制对方衣服的款式、图案或品牌。

规则：

1. 默认 `studio`。用户给了单屏姿势参考图时，先按参考图写该张，再从 pack 里补未占用的 shot。
2. 张数：用户点名 > 该 pack 全部 shot。`name` = `<product>-<color>-<shot-id>`，例如 `dress-black-studio-3q`。
3. 有姿势参考图时 `--ref pose=`，Prompt 写：身体、手脚、头朝向以姿势参考图为准，本张套餐文字作补充。
4. 无印花时跳过 `requires: ["print"]` 的 shot。
5. 不要连续 3 张同一角度。展示后背用 90° 或 110°–135° 侧背，不要 180° 死板正背面。
6. 每张姿势图的 `--ref source=` 必须是同色已通过的 `hero`，`--ref garment=` 必须是同色 `bg_white`。

## detail 图型菜单

详情回答主图没讲完的问题：版型、一衣多穿、做工、多角度。不要用整屏印花微距充数，也不要六张都是信息图。

| id | 买家问题 | Prompt 模板 | 构图要点 |
| --- | --- | --- | --- |
| `detail-infographic` | 三个卖点一眼看懂 | `prompts/infographic.md`（按卖点选板式） | 留白 ≥45%；板式见下 |
| `detail-multi-scene` | 一衣多穿 | `infographic.md` 多场景分屏 | 场景取自 `facts.target_scenes` |
| `detail-benefit` | 穿着利益（显瘦、亲肤、百搭） | `infographic.md` 的 `icon-list` | 左衣右签 |
| `detail-craft` | 领、袖、下摆、车线 | `infographic.md` 标注线或放大镜 | 对着 `selling_points[].visual_keywords` |
| `detail-three-angle` | 正 / 侧 / 背同框 | `infographic.md` 三角度骨架 | 背面栏不扭头露正脸；后背按 `garment_back` |
| `detail-ghost` | 净版立体 | `ghost-mannequin.md` | 无真人四肢 |
| `detail-scene` | 生活场景收尾 | `vary.md` | 全身或七分，场景来自 `target_scenes` |

信息图板式（放大镜 / 图标列表 / 标注线 / 60:40 分屏）在真正选了信息图时再按 `aionforge-detail` 挑，不要每套详情都六种板式出一遍。

## 组装

用户点名图型或张数 → 照做。

有参考图 → 先映射参考图的图型、景别和动作，再按目标张数补缺口。衣服用自家成衣，不抄参考图款式。

无参考、用户只说「一套详情」→ 从菜单组一套，**每张只回答一个还没回答的买家问题**。建议（可增删、可换序）：

- `conversion_driver` 为 `visual`：多场景 / 三角度 / 场景收尾偏多。
- `pattern`：图案放大镜 / 标注线 / 多角度上身偏多。
- `pain_point`：利益点 / 信息图偏多。
- `craft`：做工 / 面料微距 / 隐形人台偏多。
- 详情图里出现模特时，`--ref source=` 用 main 锚点，保证和主图同一个人、同一件衣服。
- 详情背景可在 `typography.json` 对应平台的 `palette.background` 与 `background_alt` 之间交替。
