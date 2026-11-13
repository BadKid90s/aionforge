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

## 四、阶段 2：完整编辑页填充（详情图 + 白底图 + SKU）

进入完整商品编辑页（`/goods/goods_add/index` 或 `/goods/goods_edit`）后，在同一 CDP 长连接会话中依次完成：

1. **商品详情图（`03_detail/`）**：按顺序传入所有 `750px` 宽详情图切片。
2. **商品白底图（`02_white_bg/`）**：上传主推色正面纯白底图。
3. **商品属性填充（`attributes`）**：遍历 `.be-form-item` / `[class*="property"]` 属性行，自动识别输入框（React 原生 setter + `input`/`change`）或下拉选择框（点击展开 `.be-select` / `.ant-select` 并匹配选项），填入 `面料/材质`、`领型`、`袖长`、`版型`、`衣长`、`图案`、`风格`、`适用季节` 等属性。
4. **SKU 颜色与尺码（`04_sku/`）**：添加颜色规格并上传对应 `04_sku/` 规格图，勾选尺码（如 `S/M/L/XL`），填入用户确认的拼单价、单买价、库存及运费模板。

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
