# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "websockets>=12.0",
# ]
# ///
"""通过纯 CDP (Chrome DevTools Protocol) WebSocket 长连接控制本地浏览器，执行拼多多上架/草稿保存。"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Self

DEFAULT_CDP_HTTP = "http://127.0.0.1:9222"
MMS_GOODS_ADD_URL = "https://mms.pinduoduo.com/goods/category?msfrom=mms_sidenav"


def find_browser_executable(platform: str | None = None) -> str | None:
    """跨平台查找 Chrome / Chromium / Edge 可执行文件路径。"""
    plat = platform or sys.platform
    if plat.startswith("win"):
        candidates = [
            Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
            / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
            / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("LOCALAPPDATA", ""))
            / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
            / "Microsoft/Edge/Application/msedge.exe",
        ]
        for path in candidates:
            if path.is_file():
                return str(path)
        for name in ("chrome", "msedge"):
            found = shutil.which(name)
            if found:
                return found
        return None

    if plat == "darwin":
        mac_candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
        for path in mac_candidates:
            if Path(path).is_file():
                return path
        return None

    for name in (
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "microsoft-edge",
    ):
        found = shutil.which(name)
        if found:
            return found
    return None


def chrome_launch_hint(port: int = 9222, platform: str | None = None) -> str:
    """返回对应操作系统的 CDP 调试浏览器启动命令。"""
    plat = platform or sys.platform
    profile_dir = Path(tempfile.gettempdir()) / "pdd-chrome-profile"
    if plat.startswith("win"):
        exe = find_browser_executable(plat) or r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        return f'"{exe}" --remote-debugging-port={port} --user-data-dir="{profile_dir}"'
    if plat == "darwin":
        exe = (
            find_browser_executable(plat)
            or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        )
        return f'"{exe}" --remote-debugging-port={port} --user-data-dir="{profile_dir}"'
    exe = find_browser_executable(plat) or "google-chrome"
    return f'{exe} --remote-debugging-port={port} --user-data-dir="{profile_dir}"'


def _http_json(url: str, method: str = "GET") -> Any:
    req = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def discover_targets(cdp_http: str) -> list[dict[str, Any]]:
    base = cdp_http.rstrip("/")
    data = _http_json(f"{base}/json/list")
    if not isinstance(data, list):
        return []
    return [t for t in data if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]


def open_new_target(cdp_http: str, url: str) -> dict[str, Any]:
    base = cdp_http.rstrip("/")
    encoded = urllib.parse.quote(url, safe="")
    try:
        return _http_json(f"{base}/json/new?{encoded}", method="PUT")
    except urllib.error.HTTPError:
        return _http_json(f"{base}/json/new?{encoded}", method="GET")


def close_target(cdp_http: str, target_id: str) -> None:
    base = cdp_http.rstrip("/")
    req = urllib.request.Request(f"{base}/json/close/{target_id}", method="GET")
    with urllib.request.urlopen(req, timeout=5):
        pass


def pick_or_create_mms_target(cdp_http: str) -> dict[str, Any]:
    targets = discover_targets(cdp_http)
    mms_targets = [t for t in targets if "mms.pinduoduo.com" in str(t.get("url", ""))]
    for pattern in ("goods_add", "goods_edit", "goods/category"):
        for target in mms_targets:
            if pattern in str(target.get("url", "")):
                return target
    if mms_targets:
        return mms_targets[0]
    return open_new_target(cdp_http, MMS_GOODS_ADD_URL)


class CDPClient:
    """基于 WebSocket 的 CDP 长连接客户端。"""

    def __init__(self, ws_url: str) -> None:
        self.ws_url = ws_url
        self._ws: Any = None
        self._cmd_id = 0

    async def __aenter__(self) -> Self:
        try:
            import websockets
        except ImportError as exc:
            raise RuntimeError(
                "未安装 websockets，请使用 `uv run --with websockets python ...` 运行"
            ) from exc
        self._ws = await websockets.connect(self.ws_url, max_size=32 * 1024 * 1024)
        await self.call("Page.enable")
        await self.call("DOM.enable")
        await self.call("Runtime.enable")
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None

    async def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._ws is None:
            raise RuntimeError("CDP WebSocket 长连接尚未建立")
        self._cmd_id += 1
        req_id = self._cmd_id
        payload = {"id": req_id, "method": method, "params": params or {}}
        await self._ws.send(json.dumps(payload, ensure_ascii=False))

        while True:
            raw = await self._ws.recv()
            msg = json.loads(raw)
            if msg.get("id") == req_id:
                if "error" in msg:
                    raise RuntimeError(f"CDP {method} 失败: {msg['error']}")
                return msg.get("result", {})

    async def eval_js(self, expression: str) -> Any:
        res = await self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
            },
        )
        if "exceptionDetails" in res:
            raise RuntimeError(f"JS 执行异常: {res['exceptionDetails']}")
        return res.get("result", {}).get("value")

    async def set_file_input(self, selector: str, files: list[str]) -> bool:
        doc = await self.call("DOM.getDocument", {"depth": -1})
        root_id = doc["root"]["nodeId"]
        node = await self.call("DOM.querySelector", {"nodeId": root_id, "selector": selector})
        node_id = node.get("nodeId", 0)
        if not node_id:
            return False
        await self.call("DOM.setFileInputFiles", {"nodeId": node_id, "files": files})
        return True


async def _wait_until_logged_in(cdp: CDPClient, timeout_sec: int = 180) -> bool:
    deadline = asyncio.get_running_loop().time() + timeout_sec
    notified = False
    while asyncio.get_running_loop().time() < deadline:
        state = await cdp.eval_js(
            """(() => {
                const href = location.href.toLowerCase();
                const text = document.body ? document.body.innerText : '';
                const isLogin = href.includes('login') || href.includes('passport')
                    || text.includes('商家登录') || text.includes('扫码登录');
                return { href, isLogin };
            })()"""
        )
        if not state.get("isLogin"):
            return True
        if not notified:
            print("检测到未登录拼多多商家后台，保持 CDP 长连接等待您在 Chrome 中扫码登录...")
            notified = True
        await asyncio.sleep(2.0)
    return False


async def _upload_auxiliary_images(
    cdp: CDPClient, white_bg_image: str, long_image: str
) -> dict[str, bool]:
    """在填写商品属性之前上传商品辅助图（白底图与长图）。"""
    status = {"white_bg": False, "long_image": False}
    tasks = [
        ("white_bg", "白底图", white_bg_image),
        ("long_image", "长图", long_image),
    ]
    for key, label, img_path in tasks:
        if not img_path or not Path(img_path).is_file():
            continue
        marked = await cdp.eval_js(
            f"""(() => {{
                document.querySelectorAll('input[data-pdd-aux-upload]')
                    .forEach(el => el.removeAttribute('data-pdd-aux-upload'));
                const labelText = {json.dumps(label)};
                const group = document.querySelector('.activity-materials-pic')
                    || Array.from(document.querySelectorAll('.mui-form-group, div'))
                        .find(el => (el.innerText || '').includes('商品辅助图'));
                if (!group) return false;
                group.scrollIntoView({{ block: 'center' }});
                const labels = Array.from(group.querySelectorAll('span, label, div'))
                    .filter(el => (el.innerText || '').trim() === labelText);
                for (const lbl of labels) {{
                    let box = lbl.parentElement;
                    for (let d = 0; d < 4 && box && box !== group; d++, box = box.parentElement) {{
                        const files = box.querySelectorAll('input[type="file"]');
                        if (files.length === 1) {{
                            files[0].setAttribute('data-pdd-aux-upload', {json.dumps(key)});
                            return true;
                        }}
                    }}
                }}
                return false;
            }})()"""
        )
        if not marked:
            continue
        doc = await cdp.call("DOM.getDocument", {"depth": -1})
        root_id = doc["root"]["nodeId"]
        qres = await cdp.call(
            "DOM.querySelector",
            {
                "nodeId": root_id,
                "selector": f'input[data-pdd-aux-upload="{key}"]',
            },
        )
        node_id = qres.get("nodeId", 0)
        if node_id:
            await cdp.call(
                "DOM.setFileInputFiles",
                {"nodeId": node_id, "files": [str(Path(img_path).resolve())]},
            )
            status[key] = True
            await asyncio.sleep(0.8)
        await cdp.eval_js(
            "document.querySelectorAll('input[data-pdd-aux-upload]').forEach(el => el.removeAttribute('data-pdd-aux-upload'))"
        )
    return status


async def _fill_attributes(cdp: CDPClient, attributes: dict[str, str]) -> dict[str, list[str]]:
    """在完整编辑页按属性标签自动填充输入框或下拉选择框。"""
    if not attributes:
        return {"filled": [], "skipped": []}

    result = await cdp.eval_js(
        f"""(async () => {{
            const attrs = {json.dumps(attributes, ensure_ascii=False)};
            const filled = [];
            const skipped = [];
            const clean = (s) => String(s || '').replace(/[:：*\\s]/g, '');

            const findRow = (key) => {{
                // 拼多多属性区每行 .property-item 包含左右两列，必须定位到包含单个控件的列容器
                const scope = document.querySelector('.propertys-area, .goods-propertys, .goods-property')
                    || document;
                const labels = Array.from(scope.querySelectorAll('.be-form-item-label, label, span'));
                const matchLabel = labels.find(el => clean(el.textContent) === key)
                    || labels.find(el => clean(el.textContent).endsWith(key))
                    || labels.find(el => {{
                        const t = clean(el.textContent);
                        return t && t.length <= 16 && (t.includes(key) || key.includes(t));
                    }});
                if (!matchLabel) return null;
                let box = matchLabel.parentElement;
                while (box && box !== scope) {{
                    const ctrl = box.querySelector(
                        '.be-select, .ant-select, [role="combobox"], [class*="select"], '
                        + 'input:not([type="file"]), textarea'
                    );
                    if (ctrl) return box;
                    if (box.classList?.contains('property-item')) break;
                    box = box.parentElement;
                }}
                return null;
            }};

            const fillOne = async (rawKey, rawVal) => {{
                const key = clean(rawKey);
                const val = String(rawVal || '').trim();
                if (!key || !val) return 'skip_empty';

                const row = findRow(key);
                if (!row) return 'not_found';
                row.scrollIntoView({{ block: 'center' }});
                await new Promise(r => setTimeout(r, 150));

                const selectTrigger = row.querySelector(
                    '[class*="ST_head"], .be-select, .ant-select, [role="combobox"], [class*="ST_outerWrapper"], [class*="select"]'
                );
                if (selectTrigger) {{
                    const curText = (selectTrigger.innerText || '').trim();
                    if (curText === val || (curText && !curText.includes('请选择') && curText.includes(val))) {{
                        return 'filled';
                    }}
                    document.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Escape', keyCode: 27, bubbles: true }}));
                    document.body.dispatchEvent(new MouseEvent('mousedown', {{ bubbles: true }}));
                    document.body.click();
                    await new Promise(r => setTimeout(r, 250));
                    selectTrigger.dispatchEvent(new MouseEvent('mousedown', {{ bubbles: true }}));
                    selectTrigger.click();
                    await new Promise(r => setTimeout(r, 450));
                    const findOpt = () => {{
                        const opts = Array.from(document.querySelectorAll(
                            '[class*="cIL_item"], [class*="ST_item"], .be-select-item, .ant-select-item, '
                            + '[role="option"], [class*="select-item"], [class*="dropdown"] li'
                        )).filter(el => el.getBoundingClientRect().height > 0);
                        return opts.find(el => (el.innerText || '').trim() === val)
                            || opts.find(el => (el.innerText || '').includes(val));
                    }};
                    let match = findOpt();
                    if (!match) {{
                        // 优先滚动虚拟列表查找目标值（避免先向不可过滤的输入框写值导致下拉异常）
                        const panels = Array.from(document.querySelectorAll(
                            '[class*="ST_virtualList"], [class*="ST_dropdownPanel"], [class*="cIL_list"], '
                            + '[class*="ST_dropdown"], .be-select-dropdown-menu, '
                            + '.be-select-list, [role="listbox"], [class*="select-dropdown"] [class*="list"]'
                        )).filter(el => el.getBoundingClientRect().height > 0);
                        let listBox = null;
                        for (const p of [...panels].reverse()) {{
                            if (p.scrollHeight > p.clientHeight && p.clientHeight > 40) {{
                                listBox = p;
                                break;
                            }}
                            const inner = Array.from(p.querySelectorAll('*'))
                                .find(el => el.scrollHeight > el.clientHeight && el.clientHeight > 40);
                            if (inner) {{
                                listBox = inner;
                                break;
                            }}
                        }}
                        if (listBox) {{
                            for (let s = 0; s < 40 && !match; s++) {{
                                listBox.scrollTop += 160;
                                await new Promise(r => setTimeout(r, 180));
                                match = findOpt();
                            }}
                        }}
                    }}
                    if (!match) {{
                        const searchInput = Array.from(row.querySelectorAll('input'))
                            .find(inp => inp.type !== 'file' && !inp.readOnly && inp.getBoundingClientRect().height > 0);
                        if (searchInput) {{
                            const proto = Object.getOwnPropertyDescriptor(
                                window.HTMLInputElement.prototype, 'value'
                            );
                            proto?.set?.call(searchInput, val);
                            searchInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            await new Promise(r => setTimeout(r, 450));
                            match = findOpt();
                        }}
                    }}
                    if (match) {{
                        match.scrollIntoView({{ block: 'nearest' }});
                        match.click();
                        await new Promise(r => setTimeout(r, 300));
                        document.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Escape', keyCode: 27, bubbles: true }}));
                        await new Promise(r => setTimeout(r, 150));
                        return 'filled';
                    }}
                    document.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Escape', keyCode: 27, bubbles: true }}));
                    await new Promise(r => setTimeout(r, 150));
                    return 'skipped';
                }}

                const input = row.querySelector('input:not([type="file"]), textarea');
                if (input) {{
                    const proto = Object.getOwnPropertyDescriptor(
                        input.tagName === 'TEXTAREA'
                            ? window.HTMLTextAreaElement.prototype
                            : window.HTMLInputElement.prototype,
                        'value'
                    );
                    proto?.set?.call(input, val);
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    await new Promise(r => setTimeout(r, 150));
                    return 'filled';
                }}
                return 'skipped';
            }};

            const pending = [];
            for (const [rawKey, rawVal] of Object.entries(attrs)) {{
                const status = await fillOne(rawKey, rawVal);
                if (status === 'filled') filled.push(rawKey);
                else if (status === 'not_found') pending.push([rawKey, rawVal]);
                else skipped.push(rawKey);
            }}
            if (pending.length > 0) {{
                await new Promise(r => setTimeout(r, 600));
                for (const [rawKey, rawVal] of pending) {{
                    const status = await fillOne(rawKey, rawVal);
                    if (status === 'filled') filled.push(rawKey);
                    else skipped.push(rawKey);
                }}
            }}
            return {{ filled, skipped }};
        }})()"""
    )
    if isinstance(result, dict):
        return {
            "filled": list(result.get("filled", [])),
            "skipped": list(result.get("skipped", [])),
        }
    return {"filled": [], "skipped": list(attributes.keys())}


async def _fetch_page_templates(cdp: CDPClient) -> dict[str, list[str]]:
    """通过 CDP 从当前拼多多编辑页读取「尺码模板」和「运费模板」的可选项列表。"""
    res = await cdp.eval_js(
        """(async () => {
            const readSizeTemplates = async () => {
                const hints = Array.from(document.querySelectorAll('span, label'))
                    .filter(el => (el.textContent || '').includes('可从尺码表模板选择尺码'));
                const anchor = hints[hints.length - 1] || Array.from(document.querySelectorAll('label, span'))
                    .find(el => (el.textContent || '').replace(/\\s+/g, '') === '尺码');
                if (!anchor) return [];
                let box = anchor.parentElement;
                while (box && box !== document.body && !box.querySelector('.be-select, .ant-select, [role="combobox"], [class*="select"]')) {
                    box = box.parentElement;
                }
                const sel = box?.querySelector('.be-select, .ant-select, [role="combobox"], [class*="select"]');
                if (!sel) return [];
                sel.scrollIntoView({ block: 'center' });
                document.body.click();
                await new Promise(r => setTimeout(r, 100));
                sel.click();
                await new Promise(r => setTimeout(r, 350));
                const opts = Array.from(document.querySelectorAll(
                    '.be-select-item, .ant-select-item, [role="option"], [class*="select-item"], [class*="dropdown"] li'
                )).filter(el => el.getBoundingClientRect().height > 0)
                  .map(el => (el.innerText || '').trim())
                  .filter(Boolean);
                document.body.click();
                return Array.from(new Set(opts));
            };

            const readShippingTemplates = async () => {
                const lbl = Array.from(document.querySelectorAll('label, span, .be-form-item-label'))
                    .find(el => (el.textContent || '').replace(/[:：*\\s]/g, '') === '运费模板');
                if (!lbl) return [];
                let box = lbl.parentElement;
                while (box && box !== document.body && !box.innerText.includes('其他模板')) {
                    box = box.parentElement;
                }
                if (!box) return [];
                box.scrollIntoView({ block: 'center' });
                const otherRadio = Array.from(box.querySelectorAll('label'))
                    .find(el => (el.innerText || '').trim() === '其他模板');
                if (otherRadio) {
                    otherRadio.click();
                    await new Promise(r => setTimeout(r, 400));
                }
                const scope = box.parentElement || box;
                const sel = scope.querySelector(
                    '.template-box-select [class*="ST_select"], '
                    + '.template-box-select [class*="selectWrapper"], '
                    + '.be-select, .ant-select, [role="combobox"]'
                );
                if (!sel) return [];
                const visibleOpts = () => Array.from(document.querySelectorAll(
                    '[class*="cIL_item"], [class*="ST_item"]'
                )).filter(el => el.getBoundingClientRect().height > 0);
                if (visibleOpts().length === 0) {
                    sel.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                    sel.click();
                    await new Promise(r => setTimeout(r, 400));
                }
                const opts = visibleOpts()
                    .map(el => (el.innerText || '').trim())
                    .filter(Boolean);
                return Array.from(new Set(['新疆西藏收费默认模板', ...opts]));
            };

            return {
                size_templates: await readSizeTemplates(),
                shipping_templates: await readShippingTemplates()
            };
        })()"""
    )
    if isinstance(res, dict):
        return {
            "size_templates": list(res.get("size_templates", [])),
            "shipping_templates": list(res.get("shipping_templates", [])),
        }
    return {"size_templates": [], "shipping_templates": []}


async def _select_template_dropdown(cdp: CDPClient, kind: str, value: str) -> bool:
    """在拼多多编辑页选择指定的尺码模板（size）或运费模板（shipping）。"""
    if not value:
        return False
    ok = await cdp.eval_js(
        f"""(async () => {{
            const kind = {json.dumps(kind)};
            const target = {json.dumps(value)};
            let sel = null;

            if (kind === 'size') {{
                const hints = Array.from(document.querySelectorAll('span, label, div'))
                    .filter(el => !el.closest('[class*="mms-header"]'))
                    .filter(el => {{
                        const t = el.textContent || '';
                        return t.includes('可从尺码表模板选择尺码') || t.includes('尺码表模版') || t.includes('尺码表模板');
                    }});
                const labels = Array.from(document.querySelectorAll('label, span'))
                    .filter(el => !el.closest('[class*="mms-header"]'))
                    .filter(el => (el.textContent || '').replace(/\\s+/g, '') === '尺码');
                const anchor = hints[hints.length - 1] || labels[labels.length - 1];
                let box = anchor?.parentElement;
                while (box && box !== document.body && !box.querySelector('[class*="ST_head"], .be-select, .ant-select, [role="combobox"]')) {{
                    box = box.parentElement;
                }}
                sel = box?.querySelector('[class*="ST_head"], .be-select, .ant-select, [role="combobox"], [class*="ST_outerWrapper"]');
            }} else {{
                const lbl = Array.from(document.querySelectorAll('label, span, .be-form-item-label'))
                    .filter(el => !el.closest('[class*="mms-header"]'))
                    .find(el => (el.textContent || '').replace(/[:：*\\s]/g, '') === '运费模板');
                let box = lbl?.parentElement;
                while (box && box !== document.body && !box.innerText.includes('其他模板')) {{
                    box = box.parentElement;
                }}
                if (!box) return false;
                if (target.includes('新疆西藏收费默认模板') || target === '同城配送') {{
                    const radio = Array.from(box.querySelectorAll('label'))
                        .find(el => (el.innerText || '').includes(target));
                    if (radio) {{ radio.click(); return true; }}
                    return false;
                }}
                const otherRadio = Array.from(box.querySelectorAll('label'))
                    .find(el => (el.innerText || '').trim() === '其他模板');
                if (otherRadio) {{
                    otherRadio.click();
                    await new Promise(r => setTimeout(r, 400));
                }}
                const scope = box.parentElement || box;
                sel = scope.querySelector(
                    '.template-box-select [class*="ST_head"], '
                    + '.template-box-select [class*="ST_outerWrapper"], '
                    + '.be-select, .ant-select, [role="combobox"]'
                );
            }}

            if (!sel) return false;
            const cur = (sel.innerText || '').trim();
            if (cur === target || (cur && !cur.includes('请选择') && cur.includes(target))) return true;
            document.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Escape', keyCode: 27, bubbles: true }}));
            await new Promise(r => setTimeout(r, 150));
            sel.scrollIntoView({{ block: 'center' }});
            const queryOpts = () => Array.from(document.querySelectorAll(
                kind === 'shipping'
                    ? '[class*="cIL_item"], [class*="ST_item"]'
                    : '.be-select-item, .ant-select-item, [role="option"], [class*="cIL_item"], [class*="ST_item"]'
            )).filter(el => el.getBoundingClientRect().height > 0);
            sel.dispatchEvent(new MouseEvent('mousedown', {{ bubbles: true }}));
            sel.click();
            await new Promise(r => setTimeout(r, 450));
            let opts = queryOpts();
            let hit = opts.find(el => (el.innerText || '').trim() === target)
                || opts.find(el => (el.innerText || '').includes(target));
            if (!hit && kind === 'size') {{
                const inp = sel.querySelector('input') || sel.parentElement?.querySelector('input');
                if (inp) {{
                    const proto = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');
                    proto?.set?.call(inp, target);
                    inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    await new Promise(r => setTimeout(r, 450));
                    opts = queryOpts();
                    hit = opts.find(el => (el.innerText || '').trim() === target)
                        || opts.find(el => (el.innerText || '').includes(target));
                }}
            }}
            if (hit) {{
                hit.click();
                await new Promise(r => setTimeout(r, 450));
                if (kind === 'size') {{
                    const modals = Array.from(document.querySelectorAll(
                        '[role="dialog"], .be-modal-wrap, .be-modal, .ant-modal-wrap, .ant-modal, [class*="Modal"]'
                    )).filter(m => {{
                        const st = window.getComputedStyle(m);
                        return st.display !== 'none' && st.visibility !== 'hidden' && m.getBoundingClientRect().height > 0;
                    }});
                    for (const modal of modals) {{
                        const btns = Array.from(modal.querySelectorAll('button, [role="button"], .be-btn, .ant-btn'))
                            .filter(b => b.getBoundingClientRect().height > 0);
                        const confirmBtn = btns.find(b => {{
                            const t = (b.innerText || '').trim();
                            return t === '确定' || t === '确认' || t === '确认切换' || t === '继续' || t === '我知道了';
                        }}) || btns.find(b => {{
                            const t = (b.innerText || '').trim();
                            return (t.includes('确定') || t.includes('确认')) && !t.includes('取消');
                        }}) || modal.querySelector('.be-btn-primary, .ant-btn-primary');
                        if (confirmBtn) {{
                            confirmBtn.click();
                            await new Promise(r => setTimeout(r, 350));
                            break;
                        }}
                    }}
                }}
                return true;
            }}
            return false;
        }})()"""
    )
    return bool(ok)


async def _fill_sku_colors_and_images(
    cdp: CDPClient, sku_colors: list[dict[str, Any]]
) -> dict[str, Any]:
    """依次填写商品颜色名称并通过 CDP DOM.setFileInputFiles 上传对应颜色预览图（严格限定在单行颜色容器内）。"""
    added: list[str] = []
    uploaded: list[str] = []

    for item in sku_colors:
        color = str(item.get("color") or "").strip()
        img_path = str(item.get("image") or "").strip()
        if not color:
            continue

        row_state = await cdp.eval_js(
            f"""(() => {{
                document.querySelectorAll('input[data-pdd-sku-upload]')
                    .forEach(el => el.removeAttribute('data-pdd-sku-upload'));
                const color = {json.dumps(color)};
                const inputs = Array.from(document.querySelectorAll(
                    '.goods-spec-sku-v2 input[placeholder*="主色"], '
                    + '.goods-spec-sku-body input[placeholder*="主色"]'
                ));
                let idx = inputs.findIndex(el => (el.value || '').trim() === color);
                if (idx < 0) {{
                    idx = inputs.findIndex(el => !(el.value || '').trim());
                    if (idx < 0) return {{ ok: false }};
                    const target = inputs[idx];
                    target.scrollIntoView({{ block: 'center' }});
                    const proto = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value'
                    );
                    proto?.set?.call(target, color);
                    target.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    target.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    target.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                }}
                const target = inputs[idx];
                let row = target.closest('.new-spec-single-color');
                if (!row) {{
                    let p = target.parentElement;
                    for (let d = 0; d < 8 && p; d++, p = p.parentElement) {{
                        if (p.querySelectorAll('input[placeholder*="主色"]').length === 1
                            && p.querySelector('input[type="file"], img')) {{
                            row = p;
                            break;
                        }}
                    }}
                }}
                const hasImg = !!(row && (
                    row.querySelector('img, [class*="imgContainer"]')
                    || Array.from(row.querySelectorAll('*')).some(el => getComputedStyle(el).backgroundImage !== 'none')
                ));
                const fileInp = !hasImg && row ? row.querySelector('input[type="file"]') : null;
                if (fileInp) {{
                    fileInp.setAttribute('data-pdd-sku-upload', '1');
                }}
                return {{ ok: true, hasImg, hasFileInput: !!fileInp }};
            }})()"""
        )
        if not isinstance(row_state, dict) or not row_state.get("ok"):
            continue
        added.append(color)
        await asyncio.sleep(0.35)

        if img_path and Path(img_path).is_file() and row_state.get("hasFileInput"):
            doc = await cdp.call("DOM.getDocument", {"depth": -1})
            root_id = doc["root"]["nodeId"]
            qres = await cdp.call(
                "DOM.querySelector",
                {
                    "nodeId": root_id,
                    "selector": 'input[data-pdd-sku-upload="1"]',
                },
            )
            node_id = qres.get("nodeId", 0)
            if node_id:
                await cdp.call(
                    "DOM.setFileInputFiles",
                    {"nodeId": node_id, "files": [str(Path(img_path).resolve())]},
                )
                uploaded.append(color)
                await asyncio.sleep(0.5)
            await cdp.eval_js(
                "document.querySelectorAll('input[data-pdd-sku-upload]').forEach(el => el.removeAttribute('data-pdd-sku-upload'))"
            )

    return {"added": added, "uploaded": uploaded}


async def _batch_set_sku_prices(
    cdp: CDPClient,
    group_price: float,
    single_price: float,
    stock: int = 100,
) -> bool:
    """点击并填写 SKU 批量设置（库存、拼单价、单买价）。"""
    ok = await cdp.eval_js(
        f"""(async () => {{
            const skuBox = document.querySelector('.goods-spec-sku-v2, .goods-spec-sku-body');
            if (!skuBox) return false;
            const batchBtn = Array.from(skuBox.querySelectorAll('button'))
                .find(el => (el.innerText || '').trim() === '批量设置');
            if (!batchBtn) return false;
            batchBtn.scrollIntoView({{ block: 'center' }});
            batchBtn.click();
            await new Promise(r => setTimeout(r, 350));

            const setVal = (inp, val) => {{
                if (!inp) return false;
                const proto = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                );
                proto?.set?.call(inp, String(val));
                inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return true;
            }};

            // 兼容弹窗或行内批量输入区域
            const scope = document.querySelector('.MDL_container_5-194-0, [role="dialog"], .be-modal')
                || skuBox;
            const allInputs = Array.from(scope.querySelectorAll('input[type="text"], input[type="number"], input:not([type])'))
                .filter(el => el.getBoundingClientRect().height > 0);
            const findByLabel = (needle) => {{
                const hit = allInputs.find(el => (el.placeholder || '').includes(needle));
                if (hit) return hit;
                const lbl = Array.from(scope.querySelectorAll('span, label, th, div'))
                    .find(el => (el.innerText || '').includes(needle) && el.querySelector('input'));
                return lbl?.querySelector('input') || null;
            }};

            const stockInp = findByLabel('库存');
            const groupInp = findByLabel('拼单价');
            const singleInp = findByLabel('单买价');
            const gOk = setVal(groupInp, {json.dumps(str(group_price))});
            const sOk = setVal(singleInp, {json.dumps(str(single_price))});
            if (stockInp) setVal(stockInp, {json.dumps(str(stock))});

            const confirmBtn = Array.from(scope.querySelectorAll('button'))
                .find(el => ['确定', '确认', '应用', '批量设置'].includes((el.innerText || '').trim()));
            if (confirmBtn) {{
                confirmBtn.click();
                await new Promise(r => setTimeout(r, 250));
            }}
            return Boolean(gOk && sOk);
        }})()"""
    )
    return bool(ok)


async def _run_cdp_flow(
    cdp_http: str,
    listing: dict[str, Any],
    mode: str,
    title: str,
    dry_run: bool,
    new_tab: bool = False,
    close_tab: bool = True,
) -> int:
    target = (
        open_new_target(cdp_http, MMS_GOODS_ADD_URL)
        if new_tab
        else pick_or_create_mms_target(cdp_http)
    )
    ws_url = target["webSocketDebuggerUrl"]
    print(f"已建立 CDP WebSocket 长连接: {ws_url}")

    async with CDPClient(ws_url) as cdp:
        if new_tab:
            await asyncio.sleep(2.5)
        current_url = await cdp.eval_js("location.href")
        if "mms.pinduoduo.com" not in str(current_url):
            await cdp.call("Page.navigate", {"url": MMS_GOODS_ADD_URL})
            await asyncio.sleep(2.0)

        if not await _wait_until_logged_in(cdp):
            print("等待登录超时，请登录后重试。", file=sys.stderr)
            return 3

        if dry_run:
            url_now = await cdp.eval_js("location.href")
            print(
                f"[DRY-RUN] CDP 长连接就绪: {url_now}\n"
                f"  - 模式: {mode}\n"
                f"  - 标题: {title}\n"
                f"  - 类目: {listing.get('category', '')}\n"
                f"  - 主图数: {len(listing.get('main_images', []))}\n"
                f"  - 详情图数: {len(listing.get('detail_images', []))}\n"
                f"  - SKU 颜色数: {len(listing.get('sku_colors', []))}"
            )
            return 0

        if (
            "goods/category" not in str(current_url)
            and "goods_add" not in str(current_url)
            and "goods_edit" not in str(current_url)
        ):
            await cdp.call("Page.navigate", {"url": MMS_GOODS_ADD_URL})
            await asyncio.sleep(2.5)

        # 1. 填写标题
        title_ok = await cdp.eval_js(
            f"""(() => {{
                const selectors = [
                    'input[placeholder*="商品标题"]',
                    'input[placeholder*="最多输入30"]',
                    'input[name="goods_name"]',
                    'textarea[placeholder*="商品标题"]'
                ];
                for (const sel of selectors) {{
                    const el = document.querySelector(sel);
                    if (el && el.offsetParent !== null) {{
                        const proto = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype, 'value'
                        );
                        proto?.set?.call(el, {json.dumps(title[:30])});
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        return true;
                    }}
                }}
                return false;
            }})()"""
        )

        # 2. 通过 CDP DOM.setFileInputFiles 直接上传本地主图
        main_files = [
            str(Path(p).resolve()) for p in listing.get("main_images", [])[:10] if Path(p).is_file()
        ]
        main_ok = False
        if main_files:
            main_ok = await cdp.set_file_input('input[type="file"]', main_files)
            if main_ok:
                await asyncio.sleep(min(8.0, 1.5 + 0.5 * len(main_files)))

        # 3. 匹配分类（优先推荐卡片；无推荐时自动打开「选择分类」弹窗选择）并点击「下一步，完善商品信息」
        full_cat = str(listing.get("category") or "女装/女士精品 > T恤 > T恤")
        cat_parts = [p.strip() for p in full_cat.split(">") if p.strip()]
        root_cat = cat_parts[0].split("/")[0].strip() if cat_parts else "女装"
        leaf_cat = cat_parts[-1] if cat_parts else "T恤"
        compact_cat = ">".join(cat_parts)
        next_ok = await cdp.eval_js(
            f"""(async () => {{
                const rootCat = {json.dumps(root_cat)};
                const leafCat = {json.dumps(leaf_cat)};
                const compactCat = {json.dumps(compact_cat)};
                const cards = Array.from(document.querySelectorAll(
                    '[class*="chooseCategory"], [class*="cateItemCard"], [class*="CateItem"]'
                )).filter(el => el.getBoundingClientRect().height > 0);
                const hit = cards.find(el =>
                    (el.innerText || '').includes(rootCat)
                    && (el.innerText || '').includes(leafCat)
                ) || cards.find(el => (el.innerText || '').includes(leafCat));
                if (hit) {{
                    hit.click();
                    await new Promise(r => setTimeout(r, 300));
                }} else {{
                    const chooseBtn = Array.from(document.querySelectorAll('button, a, span, div'))
                        .filter(el => !el.closest('[class*="mms-header"]') && el.getBoundingClientRect().height > 0)
                        .find(el => (el.innerText || '').trim() === '选择分类');
                    if (chooseBtn) {{
                        chooseBtn.click();
                        await new Promise(r => setTimeout(r, 600));
                        const recent = Array.from(document.querySelectorAll('.choose-category, [class*="choose-category"]'))
                            .filter(el => el.getBoundingClientRect().height > 0);
                        const norm = (s) => (s || '').replace(/\\s+/g, '');
                        let picked = recent.find(el => norm(el.innerText) === norm(compactCat))
                            || recent.find(el => (el.innerText || '').includes(rootCat) && (el.innerText || '').includes(leafCat));
                        if (picked) {{
                            picked.click();
                            await new Promise(r => setTimeout(r, 350));
                        }} else {{
                            const searchInp = document.querySelector('input[placeholder*="搜索分类"]');
                            if (searchInp) {{
                                const proto = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');
                                proto?.set?.call(searchInp, leafCat);
                                searchInp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                await new Promise(r => setTimeout(r, 500));
                                const resItems = Array.from(document.querySelectorAll('[class*="cate-select"] li, [class*="search"] li, [class*="cateItem"]'))
                                    .filter(el => el.getBoundingClientRect().height > 0);
                                const resHit = resItems.find(el => (el.innerText || '').includes(rootCat) && (el.innerText || '').includes(leafCat))
                                    || resItems.find(el => (el.innerText || '').includes(leafCat));
                                if (resHit) {{
                                    resHit.click();
                                    await new Promise(r => setTimeout(r, 350));
                                }}
                            }}
                        }}
                        const modals = Array.from(document.querySelectorAll('[role="dialog"], .be-modal, .ant-modal, [class*="cate-select-modal"]'))
                            .filter(m => m.getBoundingClientRect().height > 0);
                        for (const modal of modals) {{
                            const okBtn = Array.from(modal.querySelectorAll('button, [role="button"]'))
                                .filter(b => b.getBoundingClientRect().height > 0)
                                .find(b => ['确定', '确认', '完成'].includes((b.innerText || '').trim()));
                            if (okBtn) {{
                                okBtn.click();
                                await new Promise(r => setTimeout(r, 400));
                                break;
                            }}
                        }}
                    }}
                }}
                const needles = ['下一步，完善商品信息', '下一步, 完善商品信息', '下一步完善商品信息', '完善商品信息'];
                const btns = Array.from(document.querySelectorAll('button, a, [role="button"]'));
                const nextBtn = btns.find(el => needles.some(n => (el.innerText || '').includes(n)));
                if (nextBtn) {{
                    nextBtn.click();
                    return true;
                }}
                return false;
            }})()"""
        )
        print(
            f"首屏预填: 标题={'OK' if title_ok else 'SKIP'}, "
            f"主图={'OK' if main_ok else 'SKIP'}, "
            f"下一步={'OK' if next_ok else 'WAIT'}"
        )
        if next_ok:
            await asyncio.sleep(3.5)

        # 4. 上传商品辅助图（白底图与长图）—— 在填写商品属性之前完成
        white_bg_img = str(listing.get("white_bg_image") or "").strip()
        long_img = str(listing.get("long_image") or "").strip()
        if white_bg_img or long_img:
            aux_res = await _upload_auxiliary_images(cdp, white_bg_img, long_img)
            print(
                f"商品辅助图上传: 白底图={'OK' if aux_res['white_bg'] else 'SKIP'}, "
                f"长图={'OK' if aux_res['long_image'] else 'SKIP'}"
            )

        # 5. 填充商品属性（材质、领型、袖长、版型等）
        raw_attrs = listing.get("attributes")
        if isinstance(raw_attrs, dict) and raw_attrs:
            attr_res = await _fill_attributes(cdp, {str(k): str(v) for k, v in raw_attrs.items()})
            print(
                f"商品属性填充: 成功 {len(attr_res['filled'])} 项 "
                f"({', '.join(attr_res['filled']) or '无'}), "
                f"跳过 {len(attr_res['skipped'])} 项"
            )

        # 5. 先填写颜色分类和预览图
        sku_colors = listing.get("sku_colors")
        if isinstance(sku_colors, list) and sku_colors:
            sku_res = await _fill_sku_colors_and_images(cdp, sku_colors)
            print(
                f"SKU 颜色与预览图: 添加 {len(sku_res['added'])} 色, "
                f"上传预览图 {len(sku_res['uploaded'])} 张"
            )

        # 6. 选择尺码表模板（切换后自动确认弹窗）
        size_tpl = str(listing.get("size_template") or "").strip()
        ship_tpl = str(listing.get("shipping_template") or "").strip()
        if not size_tpl or not ship_tpl:
            avail = await _fetch_page_templates(cdp)
            missing = []
            if not size_tpl:
                missing.append(f"尺码模板(可选: {avail['size_templates'] or '未检测到'})")
            if not ship_tpl:
                missing.append(f"运费模板(可选: {avail['shipping_templates'] or '未检测到'})")
            print(f"NEEDS_TEMPLATE_SELECTION: 未配置 {', '.join(missing)}，请先询问用户选择后重试。")
            if not listing.get("_allow_missing_templates"):
                return 4

        sz_ok = await _select_template_dropdown(cdp, "size", size_tpl) if size_tpl else False
        if sz_ok:
            # 切换尺码表后会联动刷新价格及库存区域，等待渲染完成再批量设价
            await asyncio.sleep(0.8)

        # 7. 批量设置拼单价/单买价/库存
        group_price = listing.get("group_price")
        single_price = listing.get("single_price")
        stock = int(listing.get("stock") or 100)
        if group_price is None or single_price is None:
            print(
                "NEEDS_PRICING_CONFIG: 未配置 拼单价(group_price) / 单买价(single_price)，"
                "请先询问用户并配置到 default-config.json 或通过 --group-price/--single-price 传入。"
            )
            if not listing.get("_allow_missing_prices"):
                return 5
        else:
            price_ok = await _batch_set_sku_prices(
                cdp, float(group_price), float(single_price), stock
            )
            print(
                f"批量设置价格: 拼单价={group_price}, 单买价={single_price}, "
                f"库存={stock} -> {'OK' if price_ok else 'SKIP'}"
            )

        # 8. 选择邮费模板
        sh_ok = await _select_template_dropdown(cdp, "shipping", ship_tpl) if ship_tpl else False
        print(
            f"模板选择: 尺码模板({size_tpl})={'OK' if sz_ok else 'SKIP'}, "
            f"运费模板({ship_tpl})={'OK' if sh_ok else 'SKIP'}"
        )

        # 7. 保存草稿或正式上架（点击后等待并关闭弹窗，再关闭浏览器窗口）
        done_action = False
        if mode == "draft":
            saved = await cdp.eval_js(
                """(async () => {
                    const btns = Array.from(document.querySelectorAll('button, a, [role="button"]'))
                        .filter(el => el.getBoundingClientRect().height > 0 && (el.innerText || '').includes('保存草稿'));
                    const btn = btns[btns.length - 1];
                    if (!btn) return false;
                    btn.scrollIntoView({ block: 'center' });
                    btn.click();
                    await new Promise(r => setTimeout(r, 1200));
                    const modals = Array.from(document.querySelectorAll(
                        '[role="dialog"], .be-modal-wrap, .be-modal, .ant-modal-wrap, .ant-modal, [class*="Modal"]'
                    )).filter(m => {
                        const st = window.getComputedStyle(m);
                        return st.display !== 'none' && st.visibility !== 'hidden' && m.getBoundingClientRect().height > 0;
                    });
                    for (const modal of modals) {
                        const mBtns = Array.from(modal.querySelectorAll('button, [role="button"], .be-btn, .ant-btn, [class*="close"]'))
                            .filter(b => b.getBoundingClientRect().height > 0);
                        const okBtn = mBtns.find(b => ['确定', '确认', '我知道了', '关闭', '完成'].includes((b.innerText || '').trim()))
                            || mBtns.find(b => {
                                const t = (b.innerText || '').trim();
                                return (t.includes('确定') || t.includes('确认') || t.includes('关闭')) && !t.includes('取消');
                            })
                            || modal.querySelector('.be-modal-close, .ant-modal-close, .be-btn-primary, .ant-btn-primary');
                        if (okBtn) {
                            okBtn.click();
                            await new Promise(r => setTimeout(r, 800));
                            break;
                        }
                    }
                    return true;
                })()"""
            )
            done_action = bool(saved)
            print(f"保存草稿: {'已触发并处理弹窗' if saved else '未找到保存草稿按钮，请检查页面必填项'}")
        elif mode == "publish":
            submitted = await cdp.eval_js(
                """(() => {
                    const btn = document.querySelector('#submit_button')
                        || Array.from(document.querySelectorAll('button')).find(
                            el => (el.innerText || '').includes('提交并上架')
                        );
                    if (btn && !btn.disabled) { btn.click(); return true; }
                    return false;
                })()"""
            )
            done_action = bool(submitted)
            print(f"正式上架: {'已触发' if submitted else '未找到提交并上架按钮，请检查页面必填项'}")

        final_url = await cdp.eval_js("location.href")
        print(f"当前页面 URL: {final_url}")
        if done_action and close_tab:
            await asyncio.sleep(2.0)

    if done_action and close_tab and target.get("id"):
        try:
            close_target(cdp_http, str(target["id"]))
            print("已关闭商品编辑窗口")
        except (OSError, urllib.error.URLError):
            pass
    return 0


def cmd_check_cdp(args: argparse.Namespace) -> int:
    try:
        targets = discover_targets(args.cdp_url)
    except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError) as exc:
        print(f"CDP 连接失败 ({args.cdp_url}): {exc}", file=sys.stderr)
        print(f"请先使用远程调试端口启动浏览器:\n  {chrome_launch_hint()}", file=sys.stderr)
        return 1

    print(f"CDP 端口可用: {args.cdp_url}，发现 {len(targets)} 个页面标签")
    for t in targets:
        print(f"  - [{t.get('id')}] {t.get('url')} -> {t.get('webSocketDebuggerUrl')}")
    return 0


def cmd_launch_cdp(args: argparse.Namespace) -> int:
    cdp_http = f"http://127.0.0.1:{args.port}"
    try:
        targets = discover_targets(cdp_http)
        print(f"CDP 端口已就绪: {cdp_http}（当前 {len(targets)} 个标签页）")
        return 0
    except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError):
        pass

    exe = args.browser or find_browser_executable()
    if not exe:
        print(
            "未自动找到 Chrome / Chromium / Edge，请手动传入 --browser 路径或按以下命令启动:\n"
            f"  {chrome_launch_hint(args.port)}",
            file=sys.stderr,
        )
        return 1

    profile_dir = Path(args.user_data_dir or Path(tempfile.gettempdir()) / "pdd-chrome-profile")
    profile_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        exe,
        f"--remote-debugging-port={args.port}",
        f"--user-data-dir={profile_dir}",
        MMS_GOODS_ADD_URL,
    ]
    popen_kwargs: dict[str, Any] = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if sys.platform.startswith("win"):
        popen_kwargs["creationflags"] = (
            subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        popen_kwargs["start_new_session"] = True

    subprocess.Popen(cmd, **popen_kwargs)
    for _ in range(20):
        time.sleep(0.5)
        try:
            discover_targets(cdp_http)
            print(f"已启动浏览器并开启 CDP 端口: {cdp_http}")
            return 0
        except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError):
            continue

    print(f"已拉起浏览器进程，但等待 CDP 端口 {cdp_http} 就绪超时。", file=sys.stderr)
    return 1


def cmd_list_templates(args: argparse.Namespace) -> int:
    async def _fetch() -> dict[str, list[str]]:
        target = pick_or_create_mms_target(args.cdp_url)
        async with CDPClient(target["webSocketDebuggerUrl"]) as cdp:
            return await _fetch_page_templates(cdp)

    try:
        res = asyncio.run(_fetch())
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    except (OSError, RuntimeError, ValueError, urllib.error.URLError) as exc:
        print(f"读取页面模板失败: {exc}", file=sys.stderr)
        return 1


def cmd_run(args: argparse.Namespace) -> int:
    listing_path = Path(args.listing).resolve()
    if not listing_path.is_file():
        print(f"错误: 上架数据文件不存在: {listing_path}", file=sys.stderr)
        return 1

    listing = json.loads(listing_path.read_text(encoding="utf-8"))
    attrs_override: Path | None = None
    if args.attributes_file:
        attrs_override = Path(args.attributes_file).resolve()
    elif (listing_path.parent / "pdd_attributes.json").is_file():
        attrs_override = listing_path.parent / "pdd_attributes.json"
    if attrs_override and attrs_override.is_file():
        loaded_attrs = json.loads(attrs_override.read_text(encoding="utf-8"))
        if isinstance(loaded_attrs, dict):
            merged_attrs = dict(listing.get("attributes") or {})
            merged_attrs.update({str(k): str(v) for k, v in loaded_attrs.items()})
            listing["attributes"] = merged_attrs

    tpl_override = Path(args.templates_file).resolve() if args.templates_file else None
    if tpl_override and tpl_override.is_file():
        loaded_tpl = json.loads(tpl_override.read_text(encoding="utf-8"))
        if isinstance(loaded_tpl, dict):
            prof = str(listing.get("profile") or "长袖")
            t_block = (
                loaded_tpl.get("profiles", {}).get(prof, {})
                if isinstance(loaded_tpl.get("profiles"), dict)
                else loaded_tpl
            )
            if isinstance(t_block, dict):
                for key in ("size_template", "shipping_template"):
                    if t_block.get(key):
                        listing[key] = str(t_block[key]).strip()
    if args.size_template:
        listing["size_template"] = args.size_template.strip()
    if args.shipping_template:
        listing["shipping_template"] = args.shipping_template.strip()
    if args.allow_missing_templates:
        listing["_allow_missing_templates"] = True

    if args.pricing_file:
        p_file = Path(args.pricing_file).resolve()
        if p_file.is_file():
            raw_p = json.loads(p_file.read_text(encoding="utf-8"))
            prof = str(listing.get("profile") or "长袖")
            p_block = (
                raw_p.get("profiles", {}).get(prof, {})
                if isinstance(raw_p.get("profiles"), dict)
                else raw_p
            )
            for key in ("group_price", "single_price", "stock"):
                if p_block.get(key) is not None:
                    listing[key] = p_block[key]
    if args.group_price is not None:
        listing["group_price"] = args.group_price
    if args.single_price is not None:
        listing["single_price"] = args.single_price
    if args.stock is not None:
        listing["stock"] = args.stock
    if args.allow_missing_prices:
        listing["_allow_missing_prices"] = True

    mode = args.mode or listing.get("mode", "draft")
    if mode == "publish" and not args.confirm_publish:
        print(
            "安全拦截: 正式上架 (--mode publish) 必须显式传入 --confirm-publish 确认参数。",
            file=sys.stderr,
        )
        return 2

    title = str(args.title or listing.get("title") or "").strip()
    if not title:
        print("错误: 缺少商品标题", file=sys.stderr)
        return 1

    try:
        return asyncio.run(
            _run_cdp_flow(
                args.cdp_url,
                listing,
                mode,
                title,
                args.dry_run,
                bool(args.new_tab),
                not bool(args.keep_tab),
            )
        )
    except (OSError, RuntimeError, ValueError, urllib.error.URLError) as exc:
        print(f"CDP 执行失败: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdd_cdp_publish",
        description="通过 CDP WebSocket 长连接控制本地 Chrome，执行拼多多上架/草稿保存",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_chk = sub.add_parser("check-cdp", help="检测本地 Chrome CDP 调试端口与页面 WebSocket 目标")
    p_chk.add_argument(
        "--cdp-url", default=DEFAULT_CDP_HTTP, help="CDP HTTP 地址（默认 http://127.0.0.1:9222）"
    )
    p_chk.set_defaults(func=cmd_check_cdp)

    p_launch = sub.add_parser("launch-cdp", help="跨平台启动带 CDP 端口的 Chrome/Edge/Chromium")
    p_launch.add_argument("--port", type=int, default=9222, help="远程调试端口（默认 9222）")
    p_launch.add_argument("--browser", help="手动指定浏览器可执行文件路径")
    p_launch.add_argument("--user-data-dir", help="独立浏览器配置目录")
    p_launch.set_defaults(func=cmd_launch_cdp)

    p_tpl = sub.add_parser("list-templates", help="读取当前拼多多编辑页可选的尺码模板与运费模板")
    p_tpl.add_argument(
        "--cdp-url", default=DEFAULT_CDP_HTTP, help="CDP HTTP 地址（默认 http://127.0.0.1:9222）"
    )
    p_tpl.set_defaults(func=cmd_list_templates)

    p_run = sub.add_parser("run", help="读取 pdd_listing.json 并建立 CDP 长连接操作拼多多后台")
    p_run.add_argument("listing", help="pdd_listing.json 文件路径")
    p_run.add_argument(
        "--cdp-url", default=DEFAULT_CDP_HTTP, help="CDP HTTP 地址（默认 http://127.0.0.1:9222）"
    )
    p_run.add_argument("--mode", choices=["draft", "publish"], help="上架模式（覆盖 listing 中的 mode）")
    p_run.add_argument("--title", help="覆盖商品标题")
    p_run.add_argument(
        "--attributes-file",
        help="覆盖商品属性的 JSON 文件（未指定时自动读取同目录 pdd_attributes.json）",
    )
    p_run.add_argument("--templates-file", help="覆盖尺码/运费模板配置的 JSON 文件")
    p_run.add_argument("--size-template", help="指定尺码模板名称")
    p_run.add_argument("--shipping-template", help="指定运费模板名称")
    p_run.add_argument(
        "--allow-missing-templates",
        action="store_true",
        help="未配置尺码/运费模板时不中断，仅打印可选列表",
    )
    p_run.add_argument("--pricing-file", help="覆盖拼单价/单买价/库存的 JSON 文件")
    p_run.add_argument("--group-price", type=float, help="批量拼单价（元）")
    p_run.add_argument("--single-price", type=float, help="批量单买价（元）")
    p_run.add_argument("--stock", type=int, help="批量库存（默认 100）")
    p_run.add_argument(
        "--allow-missing-prices",
        action="store_true",
        help="未配置拼单价/单买价时不中断",
    )
    p_run.add_argument(
        "--new-tab",
        action="store_true",
        help="新建一个空白商品发布标签页从头创建（不复用已打开的编辑页）",
    )
    p_run.add_argument(
        "--keep-tab",
        action="store_true",
        help="保存草稿或提交上架后保留浏览器标签页（默认会自动关闭）",
    )
    p_run.add_argument(
        "--confirm-publish",
        action="store_true",
        help="正式上架安全确认开关（--mode publish 时必填）",
    )
    p_run.add_argument("--dry-run", action="store_true", help="仅建立 CDP 长连接并校验数据，不操作页面")
    p_run.set_defaults(func=cmd_run)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
