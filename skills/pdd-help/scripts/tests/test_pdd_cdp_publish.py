"""Unit tests for pdd_cdp_publish.py."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pdd_cdp_publish


class _FakeWebSocket:
    def __init__(self, responses: dict[str, dict[str, Any]]) -> None:
        self.responses = responses
        self.sent: list[dict[str, Any]] = []
        self._queue: list[str] = []

    async def send(self, raw: str) -> None:
        msg = json.loads(raw)
        self.sent.append(msg)
        method = msg["method"]
        result = self.responses.get(method, {})
        self._queue.append(json.dumps({"id": msg["id"], "result": result}))

    async def recv(self) -> str:
        return self._queue.pop(0)

    async def close(self) -> None:
        return None


def test_publish_requires_confirm_flag(tmp_path: Path) -> None:
    listing = tmp_path / "pdd_listing.json"
    listing.write_text(json.dumps({"title": "纯棉短袖T恤", "mode": "publish"}), encoding="utf-8")

    parser = pdd_cdp_publish.build_parser()
    args = parser.parse_args(["run", str(listing), "--mode", "publish"])
    assert args.func(args) == 2


def test_cdp_client_persistent_calls_and_set_file_input() -> None:
    fake_ws = _FakeWebSocket(
        {
            "DOM.getDocument": {"root": {"nodeId": 1}},
            "DOM.querySelector": {"nodeId": 42},
            "DOM.setFileInputFiles": {},
            "Runtime.evaluate": {"result": {"value": "https://mms.pinduoduo.com/goods/goods_add"}},
        }
    )

    async def _run() -> None:
        client = pdd_cdp_publish.CDPClient("ws://127.0.0.1:9222/devtools/page/1")
        client._ws = fake_ws
        url = await client.eval_js("location.href")
        assert url == "https://mms.pinduoduo.com/goods/goods_add"
        ok = await client.set_file_input('input[type="file"]', ["/tmp/a.jpg"])
        assert ok is True
        assert fake_ws.sent[-1]["method"] == "DOM.setFileInputFiles"
        assert fake_ws.sent[-1]["params"] == {"nodeId": 42, "files": ["/tmp/a.jpg"]}

    asyncio.run(_run())


def test_pick_existing_mms_target(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        pdd_cdp_publish,
        "discover_targets",
        lambda _url: [
            {"id": "1", "url": "https://www.baidu.com", "webSocketDebuggerUrl": "ws://1"},
            {
                "id": "2",
                "url": "https://mms.pinduoduo.com/goods/goods_add/index",
                "webSocketDebuggerUrl": "ws://2",
            },
        ],
    )
    target = pdd_cdp_publish.pick_or_create_mms_target("http://127.0.0.1:9222")
    assert target["id"] == "2"
    assert target["webSocketDebuggerUrl"] == "ws://2"


def test_cross_platform_chrome_hints(monkeypatch: Any) -> None:
    monkeypatch.setattr(pdd_cdp_publish, "find_browser_executable", lambda _plat=None: None)
    win_hint = pdd_cdp_publish.chrome_launch_hint(9222, platform="win32")
    linux_hint = pdd_cdp_publish.chrome_launch_hint(9222, platform="linux")
    mac_hint = pdd_cdp_publish.chrome_launch_hint(9222, platform="darwin")

    assert "chrome.exe" in win_hint
    assert "--remote-debugging-port=9222" in win_hint
    assert "google-chrome" in linux_hint
    assert "Google Chrome" in mac_hint


def test_fill_attributes_via_cdp() -> None:
    fake_ws = _FakeWebSocket(
        {
            "Runtime.evaluate": {
                "result": {"value": {"filled": ["面料/材质", "领型"], "skipped": []}}
            }
        }
    )

    async def _run() -> None:
        client = pdd_cdp_publish.CDPClient("ws://127.0.0.1:9222/devtools/page/1")
        client._ws = fake_ws
        res = await pdd_cdp_publish._fill_attributes(
            client, {"面料/材质": "棉", "领型": "圆领"}
        )
        assert res == {"filled": ["面料/材质", "领型"], "skipped": []}
        assert fake_ws.sent[-1]["method"] == "Runtime.evaluate"

    asyncio.run(_run())


def test_fetch_and_select_templates_via_cdp() -> None:
    fake_ws = _FakeWebSocket(
        {
            "Runtime.evaluate": {
                "result": {
                    "value": {
                        "size_templates": ["短袖T恤", "长袖T恤"],
                        "shipping_templates": ["新疆西藏收费默认模板", "短袖T恤包邮"],
                    }
                }
            }
        }
    )

    async def _run() -> None:
        client = pdd_cdp_publish.CDPClient("ws://127.0.0.1:9222/devtools/page/1")
        client._ws = fake_ws
        res = await pdd_cdp_publish._fetch_page_templates(client)
        assert "短袖T恤" in res["size_templates"]
        assert "短袖T恤包邮" in res["shipping_templates"]

    asyncio.run(_run())


def test_batch_set_sku_prices_via_cdp() -> None:
    fake_ws = _FakeWebSocket({"Runtime.evaluate": {"result": {"value": True}}})

    async def _run() -> None:
        client = pdd_cdp_publish.CDPClient("ws://127.0.0.1:9222/devtools/page/1")
        client._ws = fake_ws
        ok = await pdd_cdp_publish._batch_set_sku_prices(client, 39.9, 49.9, 100)
        assert ok is True
        assert fake_ws.sent[-1]["method"] == "Runtime.evaluate"

    asyncio.run(_run())


def test_select_size_template_includes_confirm_modal_handler() -> None:
    fake_ws = _FakeWebSocket({"Runtime.evaluate": {"result": {"value": True}}})

    async def _run() -> None:
        client = pdd_cdp_publish.CDPClient("ws://127.0.0.1:9222/devtools/page/1")
        client._ws = fake_ws
        ok = await pdd_cdp_publish._select_template_dropdown(client, "size", "长袖T恤")
        assert ok is True
        expr = fake_ws.sent[-1]["params"]["expression"]
        assert "确认切换" in expr and "确定" in expr

    asyncio.run(_run())
