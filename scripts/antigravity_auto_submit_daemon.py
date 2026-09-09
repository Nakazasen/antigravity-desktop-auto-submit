"""
Antigravity Desktop 2.0 Auto-Submit Daemon
=========================================
Tu dong phat hien va ket noi qua Chrome DevTools Protocol (CDP) cua Antigravity Desktop
de tu dong nhan nut 'Submit ↵' / 'Allow' moi khi agent hoi quyen chay lenh.

Tac gia: Nakazasen
Repository: https://github.com/Nakazasen/antigravity-desktop-auto-submit
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.request

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    import websockets
except ImportError:
    print("[LOI] Thieu thu vien 'websockets'. Vui long chay: pip install websockets")
    sys.exit(1)

PORT_FILES = [
    os.path.expandvars(r"%APPDATA%\Antigravity\DevToolsActivePort"),
    os.path.expandvars(r"%APPDATA%\Antigravity IDE\DevToolsActivePort"),
    os.path.expandvars(r"%LOCALAPPDATA%\Antigravity\DevToolsActivePort"),
    os.path.expandvars(r"%LOCALAPPDATA%\Antigravity IDE\DevToolsActivePort"),
]
PORT_FILE = PORT_FILES[0]

JS_PAYLOAD_TEMPLATE = """
(() => {
  if (window.__agAutoSubmitActive) return 'already_active';
  window.__agAutoSubmitActive = true;

  console.log('[Antigravity Auto-Submit] Daemon active and monitoring buttons...');

  window.__agAutoSubmitTimer = setInterval(() => {
    try {
      const getAllButtons = (root) => {
        let btns = Array.from(root.querySelectorAll('button'));
        root.querySelectorAll('iframe').forEach(frame => {
          try {
            if (frame.contentDocument) btns.push(...getAllButtons(frame.contentDocument));
          } catch(e) {}
        });
        return btns;
      };
      const buttons = getAllButtons(document);
      
      // 1. Tim nut Submit (uu tien cao nhat theo UI Antigravity 2.0 Desktop)
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
  }, __CHECK_INTERVAL_MS__);

  return 'injected_successfully';
})()
"""


def kill_previous_daemon_instances():
    """Dam bao chi co 1 instance daemon chay, tat sach cac instance cu bi treo de tranh xung dot."""
    my_pid = os.getpid()
    ps_cmd = f"""
    Get-CimInstance Win32_Process | Where-Object {{
        $cmd = $_.CommandLine
        $cmd -and ($cmd -like "*antigravity_auto_submit_daemon.py*") -and ($_.ProcessId -ne {my_pid})
    }} | ForEach-Object {{
        Stop-Process -Id $_.ProcessId -Force
        Write-Host "[DON DEP] Da tat tien trinh daemon cu PID: $($_.ProcessId)"
    }}
    """
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.stdout.strip():
            print(res.stdout.strip(), flush=True)
    except Exception:
        pass


def is_antigravity_running() -> bool:
    """Kiem tra xem tien trinh Antigravity hoac Antigravity IDE co dang chay tren may khong."""
    try:
        res = subprocess.run(
            ["tasklist", "/NH", "/FI", "IMAGENAME eq Antigravity*"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        return "Antigravity" in res.stdout
    except Exception:
        return False


def is_port_listening(port: int) -> bool:
    """Kiem tra nhanh xem port co dang mo hay khong (tranh timeout khi file port cu)."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            return s.connect_ex(('127.0.0.1', int(port))) == 0
    except Exception:
        return False


def get_active_port() -> str | None:
    """Doc cong active DevTools tu file cua Antigravity / Antigravity IDE hoac cong mac dinh 9222."""
    for p_file in PORT_FILES:
        if os.path.exists(p_file):
            try:
                with open(p_file, "r", encoding="utf-8") as f:
                    port = f.readline().strip()
                    if port.isdigit() and is_port_listening(int(port)):
                        return port
            except Exception:
                continue

    # Quet cac cong remote debugging pho bien (khi mo Antigravity IDE voi --remote-debugging-port=9222)
    for default_port in [9222, 9229, 9333]:
        if is_port_listening(default_port):
            return str(default_port)

    return None


def get_target_pages(port: str) -> list[dict]:
    """Lay danh sach cac tab / webview cua Antigravity Desktop dang mo."""
    try:
        url = f"http://127.0.0.1:{port}/json"
        with urllib.request.urlopen(url, timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [p for p in data if p.get("type") in ("page", "webview", "iframe") and p.get("webSocketDebuggerUrl")]
    except Exception:
        return []


async def inject_page(ws_url: str, check_interval_ms: int = 500) -> bool:
    """Ket noi vao trang qua WebSocket CDP va inject doan ma Javascript tu dong bam nut."""
    payload = JS_PAYLOAD_TEMPLATE.replace("__CHECK_INTERVAL_MS__", str(check_interval_ms))
    try:
        async with websockets.connect(ws_url, open_timeout=2) as ws:
            # 1. Chay ngay tren trang hien tai
            req_eval = {
                "id": 1,
                "method": "Runtime.evaluate",
                "params": {"expression": payload, "returnByValue": True},
            }
            await ws.send(json.dumps(req_eval))
            resp_eval = json.loads(await ws.recv())

            # 2. Dang ky tu dong inject neu nguoi dung load lai trang hoac doi hoi thoai
            req_preload = {
                "id": 2,
                "method": "Page.addScriptToEvaluateOnNewDocument",
                "params": {"source": payload},
            }
            await ws.send(json.dumps(req_preload))
            await ws.recv()

            result_val = resp_eval.get("result", {}).get("result", {}).get("value")
            return result_val in ("injected_successfully", "already_active")
    except Exception:
        return False


async def main_loop(poll_interval: float = 2.0, check_interval_ms: int = 500):
    print("===================================================================", flush=True)
    print("      ANTIGRAVITY DESKTOP 2.0 - AUTO SUBMIT DAEMON (CDP)           ", flush=True)
    print("===================================================================", flush=True)
    print(f"[{time.strftime('%H:%M:%S')}] [KHOI DONG] Daemon dang chay (PID: {os.getpid()})...", flush=True)
    print(f"[{time.strftime('%H:%M:%S')}] [THEO DOI] File Port uu tien: {PORT_FILE}", flush=True)
    print(f"[{time.strftime('%H:%M:%S')}] [THIET LAP] Toc do quet nut: {check_interval_ms}ms, quet tien trinh: {poll_interval}s\n", flush=True)
    
    last_injected_port: str | None = None
    injected_pages: set[str] = set()
    no_port_warn_counter = 0

    while True:
        try:
            port = get_active_port()

            # Truong hop 1: Khong tim thay cong DevTools dang mo
            if not port:
                if last_injected_port is not None:
                    print(
                        f"[{time.strftime('%H:%M:%S')}] [MAT KET NOI] Cong DevTools ({last_injected_port}) da dong. "
                        f"Dang cho Antigravity ket noi lai...",
                        flush=True,
                    )
                    last_injected_port = None
                    injected_pages.clear()

                no_port_warn_counter += 1
                # Canh bao sau moi ~10 giay (5 vong lap 2s)
                if no_port_warn_counter % 5 == 1:
                    if is_antigravity_running():
                        print(
                            f"[{time.strftime('%H:%M:%S')}] [CANH BAO] Phat hien Antigravity dang chay nhung CONG DEVTOOLS 9222 DANG DONG!\n"
                            f"           -> Nguyen nhan: Antigravity duoc mo ma thieu co '--remote-debugging-port=9222'.\n"
                            f"           -> Giai phap: Vui long mo app bang shortcut da cap nhat tren Desktop hoac file Khoi_Dong_Antigravity_IDE.bat!",
                            flush=True,
                        )
                    else:
                        print(
                            f"[{time.strftime('%H:%M:%S')}] [CHO DOI] Dang cho ung dung Antigravity Desktop / IDE khoi dong...",
                            flush=True,
                        )

                await asyncio.sleep(poll_interval)
                continue

            # Truong hop 2: Co cong DevTools mo
            no_port_warn_counter = 0

            # Neu doi cong hoac ket noi moi sau khi app restart: reset toan bo state
            if port != last_injected_port:
                print(
                    f"[{time.strftime('%H:%M:%S')}] [KET NOI] Da tim thay cong DevTools active: {port}! Dang quet cac trang...",
                    flush=True,
                )
                last_injected_port = port
                injected_pages.clear()

            pages = get_target_pages(port)
            active_page_ids = {p.get("id") for p in pages if p.get("id")}
            
            # Prune cac trang da dong de lam sach bo nho
            injected_pages = injected_pages.intersection(active_page_ids)

            for p in pages:
                page_id = p.get("id")
                ws_url = p.get("webSocketDebuggerUrl")
                if page_id and page_id not in injected_pages and ws_url:
                    success = await inject_page(ws_url, check_interval_ms)
                    if success:
                        injected_pages.add(page_id)
                        title = p.get("title", "Antigravity View")[:40]
                        print(
                            f"[{time.strftime('%H:%M:%S')}] [THANH CONG] Da kich hoat Auto-Submit cho: '{title}' (Port: {port}, Page: {page_id[:8]})",
                            flush=True,
                        )
        except Exception:
            pass

        await asyncio.sleep(poll_interval)


def parse_args():
    parser = argparse.ArgumentParser(description="Antigravity Desktop 2.0 Auto-Submit Daemon")
    parser.add_argument("--interval", type=float, default=2.0, help="Chu ky quet tien trinh / cong port (giay, mac dinh: 2.0)")
    parser.add_argument("--button-check-ms", type=int, default=500, help="Chu ky tim nut Submit trong giao dien (ms, mac dinh: 500)")
    return parser.parse_args()


if __name__ == "__main__":
    # Dam bao Single-Instance: tat sach cac daemon cu dang bi treo truoc khi chay
    kill_previous_daemon_instances()

    args = parse_args()
    try:
        asyncio.run(main_loop(poll_interval=args.interval, check_interval_ms=args.button_check_ms))
    except KeyboardInterrupt:
        print("\n[Antigravity Auto-Submit Daemon] Da dung boi nguoi dung.")
        sys.exit(0)
