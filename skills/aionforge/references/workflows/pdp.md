# 工作流：女装主图 + 详情（pdp）

日常主力。输入至少一张白底成衣。需要锁脸锁衣的镜头，用换装 Prompt + `--ref garment= --ref model=`；其余用成衣参考图。全部走 `forge generate`。

## 默认交付

- 主图 5 张，比例 `1:1`（拼多多 / 淘宝）或按 `references/platforms.md`
- 详情 6 张，比例 `3:4`
- 图型与顺序以 `references/shots-womenswear.md` 为准；用户点名张数时听用户

## 步骤

1. doctor
2. `forge job init --workflow pdp --slug <商品短名> --json`，记下 `run_dir`
3. 看图写 `facts.json` 到 `run_dir`，展示卖点与结构，等人确认
4. 写 Style Lock，写入 `facts.json` 的 `style_lock` 字段
5. 按图型清单写 `plan.json`：

```json
{
  "tasks": [
    {
      "name": "main-01",
      "prompt": "tryon",
      "ratio": "1:1",
      "goal": "正面主视觉，服装占画面 85%"
    },
    {
      "name": "detail-01",
      "prompt": "detail",
      "ratio": "3:4",
      "goal": "面料质感微距"
    }
  ]
}
```

需要模特身份的镜头用 `references/workflows/tryon.md`。多机位补图用 `references/workflows/vary.md`。平铺、微距、印花特写自己写构图 Prompt。印花文件先走 `references/workflows/extract.md`。

6. 等人批准计划
7. 为每张写 `work/prompts/<name>.txt`：Style Lock 原文 + 对应模板或构图 + facts 锁定项
8. 执行：

```
# 换装类
forge generate --job-dir <run_dir> \
  --prompt-file <run_dir>/work/prompts/main-01.txt \
  --ref garment=<成衣> --ref model=<模特> \
  --name main-01 --ratio 1:1 --json

# 通用类
forge generate --job-dir <run_dir> \
  --prompt-file <run_dir>/work/prompts/detail-01.txt \
  --ref <成衣> --name detail-01 --ratio 3:4 --json
```

9. 质检；失败只重跑该 `--name`
10. 交付 `images/` 路径列表

## 素材不齐

- 无模特：主图改为平铺/挂拍，详情里需要真人的镜头改为平铺细节或省略并告知
- 无白底成衣、只有挂拍或街拍：仍可 generate，Prompt 中写明以该图为衣服标准，并标 Assumption
- 有印花且用户要单独印花文件：先跑 `references/workflows/extract.md`，再继续本流程
