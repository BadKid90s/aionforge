# 3D 立体隐形人台 Prompt 模板（`ghost-mannequin`）

当用户未提供真人模特图、模特脸部不便出镜，或需要在主图收口（`main-ghost`）/ Amazon 白底主图中展示**立体胸腰剪裁与自然垂坠感**时使用。比平面平铺（Flat Lay）更能体现女装的立体廓形与肩袖结构。

写入 `work/prompts/<name>.txt` 后执行：

```bash
forge generate --job-dir <run_dir> --prompt-file <run_dir>/work/prompts/<name>.txt \
  --ref garment=<成衣> --name <name> --ratio 1:1 --json
```

```
# Role: 女装 3D 立体隐形人台商拍师（Ghost Mannequin Photography）

Professional 3D ghost-mannequin (invisible hollow mannequin) commercial product photography of the womenswear garment on a clean seamless background [背景 Hex，如 #FFFFFF 或 #F7F5F2].

## Campaign Style Lock
（粘贴 facts.style_lock 原文）

## 参考图角色（用画面内容区分，不要用先后顺序猜测）
- 成衣图（文件名 garment）：整件衣服版型、领口、肩线、袖型、袖口、腰线、下摆、面料、颜色与印花的唯一标准。若原图有衣架、人台支架或模特四肢，输出中必须完全移除。

## 画面与立体结构要求（3D Hollow Mannequin Effect）
1. **立体充盈廓形**：衣服如同穿在隐形透明的立体女性人体模型上，自然撑起肩部线条、胸部立体省道、腰部曲线与袖管弧度，下摆自然垂直垂坠，展现真实的 3D 内部空间感与体积感。
2. **领口内里可见**：领口处自然露出轻微的后领内侧布料（hollow neck effect），无塑料假人脖子、无金属支架杆、无衣架挂钩。
3. **居中与占比**：整件衣服正面（或微转 10°）完整居中，占画面 80–85%，四周留白均匀（至少 15–20%），成衣正下方带有极淡的自然柔和落地投影。
4. **服装细节 100% 锁定（来自 facts.json）**：
   - 品类与版型：
   - 面料颜色与织纹质感：
   - 领口 / 袖口 / 下摆：
   - 印花位置与文字（若有，逐字一致，只出现一次）：

## 负面约束（Negative Constraints）
严禁出现：真人头部、脖子、手脚、皮肤、塑料人台、木质人台、金属立杆、衣架、夹子、吊牌、额外文字、水印、假 Logo、杂乱背景。只输出一张纯净的 3D 隐形人台成衣图。
```
