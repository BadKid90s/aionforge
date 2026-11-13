# 拼多多商家后台（MMS）CDP 长连接上架操作流

本流程参考 `pdd-helper-studio` 浏览器扩展的实测页面流转与选择器，**强制通过 CDP（Chrome DevTools Protocol）WebSocket 长连接**接管本地已打开/已登录的 Chrome 浏览器，在 `https://mms.pinduoduo.com` 上完成本地主图、白底图、详情图、SKU 图的自动上传与保存草稿/正式上架。

---

## 一、CDP 长连接准备与检测（支持 macOS / Linux / Windows）

1. 可直接用脚本自动跨平台拉起带远程调试端口（默认 `9222`）的 Chrome / Chromium / Edge：
   ```bash
   uv run --with websockets python skills/pdd-help/scripts/pdd_cdp_publish.py launch-cdp
   ```
   或按系统手动启动：
   - **Linux**：`google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/pdd-chrome-profile`
   - **Windows (PowerShell / CMD)**：`"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%TEMP%\pdd-chrome-profile"`
   - **macOS**：`"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222 --user-data-dir=/tmp/pdd-chrome-profile`
2. 使用脚本检测 CDP 端点（`/json/list`）及各标签页 `webSocketDebuggerUrl`：
   ```bash
   uv run --with websockets python skills/pdd-help/scripts/pdd_cdp_publish.py check-cdp
   ```
3. **长连接优势**：
   - 复用本地 Chrome 真实登录态与 Anti-Content 环境；
   - 通过 `DOM.setFileInputFiles` 直接传入本地图片绝对路径，无需额外中转上传；
   - 全程保持同一条 `ws://127.0.0.1:9222/devtools/page/<targetId>` WebSocket 长连接。

---

## 二、登录态检测与保持等待

1. 脚本通过 CDP `Page.navigate` 打开 `https://mms.pinduoduo.com/goods/category?msfrom=mms_sidenav`。
2. 若检测到登录页（URL 含 `login`/`passport` 或页面出现「商家登录」「扫码登录」）：
   - **保持当前 CDP WebSocket 长连接不断开**，每 2 秒通过 `Runtime.evaluate` 轮询登录状态；
   - 用户在 Chrome 窗口完成扫码登录后，自动无缝继续执行后续步骤。

---

## 三、阶段 1：新版发布页预填（主图 + 标题 + 类目）

1. **填写商品标题**（≤ 30 汉字 / 60 字符）：
   - 通过 `Runtime.evaluate` 调用原生 `HTMLInputElement.prototype.value` setter 并派发 `input` / `change` 事件，确保 React 受控状态同步。
2. **上传轮播主图（`01_main/`，最多 10 张）**：
   - 通过 `DOM.getDocument` → `DOM.querySelector('input[type="file"]')` → `DOM.setFileInputFiles` 直接注入本地 `01_main/` 文件列表。
3. **选定商品类目并进入下一步**：
   - 匹配推荐分类卡片（如 `女装/女士精品 > T恤 > T恤`），点击「下一步，完善商品信息」进入完整编辑页。

---

## 四、阶段 2：完整编辑页填充（辅助图 → 属性 → 颜色 → 尺码表 → 价格库存 → 邮费模板）

进入完整商品编辑页（`/goods/goods_add/index` 或 `/goods/goods_edit`）后，在同一 CDP 长连接会话中严格按以下顺序完成：

1. **商品辅助图（白底图 + 长图）**：在填写商品属性之前，定位 `.activity-materials-pic` 区域，分别上传 `white_bg_image`（`1:1` 纯白底图）与 `long_image`（`2:3` 竖版长图）。
2. **商品属性填充（`attributes`）**：遍历商品属性行，自动识别输入框或下拉/虚拟滚动列表（如 `品牌`、`重要面料俗称`、`成分含量`、`重要上市时节` 等）。
3. **颜色分类与预览图（`04_sku/`）**：在各单行 `.new-spec-single-color` 容器内填写主色名称并上传对应颜色预览图（不触碰价格及库存批量设置栏）。
4. **选择尺码表模板**：选择对应款式的尺码模板（如 `长袖T恤` / `短袖T恤`），并自动点击确认切换弹窗。
5. **批量设置价格与库存**：在尺码表联动刷新价格及库存区域后，点击「批量设置」填入 `stock`、`group_price`（拼单价）与 `single_price`（单买价）。
6. **选择邮费模板**：选定「其他模板」并选择对应运费模板（如 `T恤包邮`）。
7. **保存/上架与关闭窗口**：点击底部「保存草稿」或「提交并上架」，自动关闭确认弹窗后再关闭当前浏览器标签页（传入 `--keep-tab` 时保留标签页）。

---

## 五、阶段 3：保存草稿箱 vs 正式上架（安全闸门）

```bash
# 1. 默认：保存到草稿箱（安全模式）
uv run --with websockets python skills/pdd-help/scripts/pdd_cdp_publish.py run <pdd_listing.json> --mode draft

# 2. 正式上架（必须用户明确确认后才允许加 --confirm-publish）
uv run --with websockets python skills/pdd-help/scripts/pdd_cdp_publish.py run <pdd_listing.json> --mode publish --confirm-publish
```

| 目标动作 | 页面操作 | 确认门槛 |
| --- | --- | --- |
| **上架到草稿箱（默认）** | 点击「保存草稿」，确认保存成功并输出草稿页面 URL | 用户选择草稿模式即可执行 |
| **正式上架** | 点击「提交并上架」（`#submit_button`） | **必须先向用户汇报标题、价格、库存、SKU 与图片核对结果，取得明确确认后再加 `--confirm-publish` 执行** |
