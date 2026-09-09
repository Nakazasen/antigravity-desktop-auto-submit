"""
Antigravity Desktop 2.0 Auto-Submit Daemon
Tu dong phat hien va ket noi qua Chrome DevTools Protocol (CDP) cua Antigravity Desktop
de tu dong nhan nut 'Submit' / 'Allow' moi khi agent hoi quyen chay lenh.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import urllib.request

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import websockets

PORT_FILE = os.path.expandvars(r"%APPDATA%\Antigravity\DevToolsActivePort")

JS_PAYLOAD = """
(() => {
  if (window.__agAutoSubmitActive) return 'already_active';
  window.__agAutoSubmitActive = true;

  console.log('[Antigravity Auto-Submit] Daemon active and monitoring buttons...');

  window.__agAutoSubmitTimer = setInterval(() => {
    try {
      const buttons = Array.from(document.querySelectorAll('button'));
      
      // 1. Tim nut Submit (uu tien cao nhat)
      const submitBtn = buttons.find(b => {
        const text = (b.innerText || b.textContent || '').trim().toLowerCase();
        return (text === 'submit' || text.startsWith('submit') || text.includes('submit ↵')) &&
               !b.disabled &&
               b.offsetParent !== null;
      });

      if (submitBtn) {
        console.log('[Antigravity Auto-Submit] Found Submit button. Clicking...');
        submitBtn.focus();
        submitBtn.click();
        return;
      }

      // 2. Tim nut Allow neu co hop thoai truc tiep
      const allowBtn = buttons.find(b => {
        const text = (b.innerText || b.textContent || '').trim().toLowerCase();
        return (text === 'allow' || text === 'allow this time' || text === 'yes, allow this time') &&
               !b.disabled &&
               b.offsetParent !== null;
      });

      if (allowBtn) {
        console.log('[Antigravity Auto-Submit] Found Allow button. Clicking...');
        allowBtn.focus();
        allowBtn.click();
      }
    } catch (err) {
      console.error('[Antigravity Auto-Submit] Error in timer:', err);
    }
  }, 500);

  return 'injected_successfully';
})()
"""


def get_active_port() -> str | None:
    if not os.path.exists(PORT_FILE):
        return None
    try:
        with open(PORT_FILE, "r", encoding="utf-8") as f:
            port = f.readline().strip()
            return port if port.isdigit() else None
    except Exception:
        return None


def get_target_pages(port: str) -> list[dict]:
    try:
        url = f"http://127.0.0.1:{port}/json"
        with urllib.request.urlopen(url, timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [p for p in data if p.get("type") == "page" and p.get("webSocketDebuggerUrl")]
    except Exception:
        return []


async def inject_page(ws_url: str) -> bool:
    try:
        async with websockets.connect(ws_url, open_timeout=2) as ws:
            # Gui script chay ngay lap tuc
            req_eval = {
                "id": 1,
                "method": "Runtime.evaluate",
                "params": {"expression": JS_PAYLOAD, "returnByValue": True},
            }
            await ws.send(json.dumps(req_eval))
            resp_eval = json.loads(await ws.recv())

            # Dang ky script tu dong chay khi chuyen trang
            req_preload = {
                "id": 2,
                "method": "Page.addScriptToEvaluateOnNewDocument",
                "params": {"source": JS_PAYLOAD},
            }
            await ws.send(json.dumps(req_preload))
            await ws.recv()

            result_val = resp_eval.get("result", {}).get("result", {}).get("value")
            return result_val in ("injected_successfully", "already_active")
    except Exception:
        return False


async def main_loop():
    print(f"[{time.strftime('%H:%M:%S')}] [KHOI DONG] Antigravity Auto-Submit Daemon dang chay...", flush=True)
    print(f"[{time.strftime('%H:%M:%S')}] [THEO DOI] Dang theo doi tien trinh Antigravity Desktop...", flush=True)
    
    last_injected_port = None
    injected_pages = set()

    while True:
        try:
            port = get_active_port()
            if not port:
                await asyncio.sleep(2)
                continue

            if port != last_injected_port:
                last_injected_port = port
                injected_pages.clear()

            pages = get_target_pages(port)
            for p in pages:
                page_id = p.get("id")
                ws_url = p.get("webSocketDebuggerUrl")
                if page_id and page_id not in injected_pages and ws_url:
                    success = await inject_page(ws_url)
                    if success:
                        injected_pages.add(page_id)
                        print(
                            f"[{time.strftime('%H:%M:%S')}] [THANH CONG] Da kich hoat Auto-Submit cho cua so Antigravity (Port {port}, Page {page_id[:8]})",
                            flush=True,
                        )
        except Exception:
            pass

        await asyncio.sleep(2)


if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\n[Antigravity Auto-Submit Daemon] Da dung.")
        sys.exit(0)
