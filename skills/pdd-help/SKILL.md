---
name: pdd-help
description: >
  拼多多（PDD）商品上架帮助技能：将本地的主图（main）、白底图（bg_white）、详情图（detail）与 SKU 图，
  按拼多多平台规范完成合规检测与尺寸适配，并通过浏览器自动化将商品正式上架或保存到拼多多商家后台草稿箱。
  参考 pdd-helper-studio 浏览器插件的 MMS 发布流，支持标题与违禁词校验、主图/详情/SKU/白底图批量上传、
  类目与规格填充、保存草稿及正式上架。
  当用户说「pdd 帮助」「上架拼多多」「保存到拼多多草稿箱」「正式上架拼多多」「导出拼多多素材」时使用。
  Use when the user runs /pdd-help.
---

# 拼多多（PDD）商品上架助手

本技能参考 `pdd-helper-studio` 浏览器扩展的拼多多商家后台（`mms.pinduoduo.com`）发布流，负责把本地生成的主图、白底图、详情图与 SKU 图完成**合规适配 → 上架参数确认 → 浏览器自动上传并保存草稿箱或正式上架**。

- 平台图片与文案规则见 [pdd-rules.md](references/pdd-rules.md)
- 拼多多商家后台浏览器操作流见 [pdd-mms-flow.md](references/pdd-mms-flow.md)

---

## 执行流程

### 第一步：盘点素材与合规检测（Check）

1. 确定目标商品工作区（如 `output/<logo>/`）或用户指定的图片文件夹，扫描 `main/`、`bg_white/`、`detail/`、`sku/`，并读取 `.forge/products/<product>/facts.json`（若存在）。
2. 运行合规检测：
   ```bash
   uv run --project skills/aionforge/scripts python skills/pdd-help/scripts/pdd_prepare.py check <工作区或图片目录>
   ```
   若存在 `FAIL` 项（如白底不纯、分辨率 < 480、体积 > 3MB），先提示处理。

### 第二步：自动适配与生成上架数据包（Prepare）

运行 `prepare` 导出拼多多合规图片与结构化上架数据 `pdd_listing.json`：

```bash
uv run --project skills/aionforge/scripts python skills/pdd-help/scripts/pdd_prepare.py prepare <工作区或图片目录>
```

输出目录 `<目标目录>/pdd_ready/` 包含：
- `01_main/`：`800×800` 轮播主图（最多 10 张）
- `02_white_bg/`：纯白 `#FFFFFF` `800×800` 白底商品图
- `03_detail/`：统一 `750px` 宽详情图（超 `1500px` 自动纵向切分）
- `04_sku/`：`800×800` SKU 规格图（无 `sku/` 时自动从 `bg_white/` 正面图提取）
- `pdd_manifest.json`、`pdd_attributes.json`（独立可编辑的属性文件，默认读取统一配置文件 [default-config.json](references/default-config.json) 中的**「短袖」「长袖」两套素禾母版**，支持 `--profile 短袖|长袖` 指定或自动识别，也可用 `--config-file` / `--attributes-file` 覆盖）、`05_auxiliary/`（商品白底图与 `2:3` 长图）与 `pdd_listing.json`

### 第三步：校验标题并确认上架参数（Lock）

1. 结合商品事实拟定拼多多标题（≤ 30 汉字 / 60 字符），并用脚本校验：
   ```bash
   uv run --project skills/aionforge/scripts python skills/pdd-help/scripts/pdd_prepare.py check-title "<待校验标题>"
   ```
2. 向用户确认关键上架参数（禁止擅自编造价格或直接正式发布）：
   - **上架模式**：`上架到草稿箱`（默认推荐）或 `正式上架`
   - **商品标题 & 类目**：确认最终标题与三级类目（如 `女装/女士精品 > T恤 > T恤`）
   - **商品属性**：核对 `pdd_listing.json` / `pdd_attributes.json` 中的属性（默认对齐 [default-config.json](references/default-config.json) 中「素禾优选女装」按长袖/短袖区分的 16 项属性母版）
   - **尺码模板 & 运费模板**：优先读取 [default-config.json](references/default-config.json)（或 `--config-file` / `--templates-file` / `pdd_listing.json`）；**若其中任一项未配置（为空），必须先通过 `list-templates` 读取页面可选项并询问用户选择哪个尺码模板与运费模板**，禁止擅自决定。
   - **拼单价 & 单买价 & 库存**：优先读取 [default-config.json](references/default-config.json)（按 **长袖 / 短袖** 分开配置，支持 `--config-file` / `--pricing-file` 覆盖）；**若任一价格未配置（`null`），必须询问用户确认后再执行批量设置**。
   - **商品辅助图与 SKU 规格**：确认白底图（`white_bg_image`）、长图（`long_image`）、颜色列表与 `04_sku/` 预览图映射

### 第四步：CDP 协议长连接自动上传与上架

**必须使用 CDP 协议建立 WebSocket 长连接**操作本地浏览器，严格按 [pdd-mms-flow.md](references/pdd-mms-flow.md) 执行：

1. **检测或启动 CDP 长连接端点**（支持 macOS / Linux / Windows，默认 `http://127.0.0.1:9222`）：
   ```bash
   uv run --with websockets python skills/pdd-help/scripts/pdd_cdp_publish.py check-cdp
   # 若未开启，可一键跨平台拉起带 CDP 端口的 Chrome/Edge/Chromium：
   uv run --with websockets python skills/pdd-help/scripts/pdd_cdp_publish.py launch-cdp
   ```
2. **建立 CDP 长连接并执行上架 / 草稿保存**：
   - **草稿箱模式（默认）**：
     ```bash
     uv run --with websockets python skills/pdd-help/scripts/pdd_cdp_publish.py run <pdd_ready>/pdd_listing.json --mode draft
     ```
   - **正式上架模式（必须先取得用户明确确认）**：
     ```bash
     uv run --with websockets python skills/pdd-help/scripts/pdd_cdp_publish.py run <pdd_ready>/pdd_listing.json --mode publish --confirm-publish
     ```
3. **长连接会话内自动处理**：
   - 未登录时保持同一条 CDP WebSocket 长连接等待用户扫码登录，登录后自动续跑；
   - 通过 CDP `DOM.setFileInputFiles` 直接上传本地 `01_main/`、`05_auxiliary/`（白底图与长图，先于商品属性上传）、`04_sku/` 颜色预览图；
   - 严格按顺序完成：**上传商品辅助图（白底图+长图）→ 填写商品属性 → 填写颜色分类与预览图 → 选择尺码表模板并确认弹窗 → 批量设置拼单价/单买价/库存 → 选择邮费模板 → 保存草稿/上架、处理弹窗并关闭浏览器标签页**（调试时可加 `--keep-tab` 保留标签页）。
