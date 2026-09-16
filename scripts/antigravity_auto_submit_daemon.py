"""
Antigravity Desktop & IDE 2.0 - Auto-Submit Daemon
===================================================
Tu dong phat hien va ket noi qua Chrome DevTools Protocol (CDP)
cua Antigravity Desktop, va bam nut Submit cua Antigravity 2.0
Extension tren Antigravity IDE qua Windows UI Automation.

Tac gia: Nakazasen
Repository: https://github.com/Nakazasen/antigravity-desktop-auto-submit
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import socket
import subprocess
import sys
import threading
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
    print("[LOI] Thieu thu vien 'websockets'. Vui long chay: pip install websockets", flush=True)
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# Danh sach cac duong dan file Port cua ca Antigravity Desktop va Antigravity IDE
PORT_FILES = [
    os.path.expandvars(r"%APPDATA%\Antigravity\DevToolsActivePort"),
    os.path.expandvars(r"%APPDATA%\Antigravity IDE\DevToolsActivePort"),
    os.path.expandvars(r"%LOCALAPPDATA%\Antigravity IDE\DevToolsActivePort"),
]

# Cac cong Remote Debugging tieu chuan khi mo bang co --remote-debugging-port
DEFAULT_DEBUG_PORTS = [9222, 9229, 9333, 9230, 9223]

# Antigravity normally writes its random CDP port to DevToolsActivePort. Some
# releases/restarts leave that file stale, so periodically discover TCP ports
# owned by Antigravity.exe and validate them with the CDP HTTP endpoint.
PROCESS_PORT_SCAN_INTERVAL_SEC = 10.0
_DISCOVERED_DEBUG_PORTS: set[int] = set()
_LAST_PROCESS_PORT_SCAN_MONO = 0.0

JS_PAYLOAD_TEMPLATE = """
(() => {
  if (window.__agAutoSubmitActive) return 'already_active';
  window.__agAutoSubmitActive = true;

  console.log('[Antigravity Auto-Submit] Daemon active (shadow DOM + iframe + vscode-button)...');

  const isVisible = (el) => {
    if (!el || el.disabled || el.getAttribute('aria-disabled') === 'true') return false;
    const style = window.getComputedStyle ? window.getComputedStyle(el) : null;
    if (style && (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0')) {
      return false;
    }
    const rects = el.getClientRects ? el.getClientRects() : [];
    if (rects && rects.length > 0) return true;
    return !!(el.offsetParent || el.offsetWidth || el.offsetHeight);
  };

  const buttonText = (el) => ((el.innerText || el.textContent || el.getAttribute('aria-label') || '') + '').trim().toLowerCase();

  const visit = (root, out) => {
    if (!root) return;
    try {
      const nodes = root.querySelectorAll
        ? root.querySelectorAll('button, [role="button"], vscode-button, a.monaco-button, .monaco-button')
        : [];
      nodes.forEach((el) => out.push(el));
      const all = root.querySelectorAll ? root.querySelectorAll('*') : [];
      all.forEach((el) => {
        if (el.shadowRoot) visit(el.shadowRoot, out);
      });
      const frames = root.querySelectorAll ? root.querySelectorAll('iframe') : [];
      frames.forEach((frame) => {
        try {
          if (frame.contentDocument) visit(frame.contentDocument, out);
        } catch (e) {}
      });
    } catch (e) {}
  };

  const getAllButtons = () => {
    const out = [];
    visit(document, out);
    return out;
  };

  const isSubmit = (text) =>
    text === 'submit' ||
    text.startsWith('submit') ||
    text.includes('submit ↵');

  const isAllow = (text) =>
    text === 'allow' ||
    text === 'allow this time' ||
    text === 'yes, allow this time' ||
    text === 'approve' ||
    text === 'confirm';

  window.__agAutoSubmitTimer = setInterval(() => {
    try {
      const buttons = getAllButtons();
      const submitBtn = buttons.find((b) => isSubmit(buttonText(b)) && isVisible(b));
      if (submitBtn) {
        console.log('[Antigravity Auto-Submit] Found Submit button. Clicking...');
        submitBtn.focus();
        submitBtn.click();
        return;
      }
      const allowBtn = buttons.find((b) => isAllow(buttonText(b)) && isVisible(b));
      if (allowBtn) {
        console.log('[Antigravity Auto-Submit] Found Allow/Approve button. Clicking...');
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


def is_port_listening(port: int) -> bool:
    """Kiem tra nhanh xem port co dang mo hay khong (tranh timeout khi file port cu)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False


def _port_speaks_cdp(port: int) -> bool:
    try:
        url = f"http://127.0.0.1:{port}/json/version"
        with urllib.request.urlopen(url, timeout=0.6) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            return bool(payload.get("webSocketDebuggerUrl") or payload.get("Browser"))
    except Exception:
        try:
            url = f"http://127.0.0.1:{port}/json"
            with urllib.request.urlopen(url, timeout=0.6) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
                return isinstance(data, list)
        except Exception:
            return False


def _ports_from_files() -> list[int]:
    found: list[int] = []
    for p_file in PORT_FILES:
        if not os.path.exists(p_file):
            continue
        try:
            with open(p_file, "r", encoding="utf-8") as handle:
                port = handle.readline().strip()
                if port.isdigit() and is_port_listening(int(port)):
                    found.append(int(port))
        except Exception:
            continue
    return found


def _run_hidden(command: list[str], timeout: float = 2.0) -> str:
    """Run a Windows diagnostic command without flashing a console window."""
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return completed.stdout or ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _antigravity_desktop_pids() -> set[int]:
    """Return PIDs whose image name is exactly Antigravity.exe."""
    output = _run_hidden(
        [
            "tasklist",
            "/FI",
            "IMAGENAME eq Antigravity.exe",
            "/FO",
            "CSV",
            "/NH",
        ]
    )
    pids: set[int] = set()
    for row in csv.reader(output.splitlines()):
        if len(row) < 2 or row[0].strip().casefold() != "antigravity.exe":
            continue
        try:
            pids.add(int(row[1].replace(",", "").strip()))
        except ValueError:
            continue
    return pids


def _ports_from_antigravity_processes() -> list[int]:
    """Find TCP local ports owned by Antigravity Desktop processes."""
    pids = _antigravity_desktop_pids()
    if not pids:
        return []

    ports: set[int] = set()
    for line in _run_hidden(["netstat", "-ano", "-p", "tcp"]).splitlines():
        parts = line.split()
        if len(parts) < 4 or parts[0].upper() != "TCP":
            continue
        try:
            pid = int(parts[-1])
        except ValueError:
            continue
        if pid not in pids:
            continue

        port_text = parts[1].rsplit(":", 1)[-1]
        if port_text.isdigit():
            ports.add(int(port_text))
    return sorted(ports)


def _live_cdp_ports(candidates: list[int]) -> list[str]:
    live: list[str] = []
    for port in candidates:
        if is_port_listening(port) and _port_speaks_cdp(port):
            live.append(str(port))
    return live


def get_active_ports() -> list[str]:
    """Tat ca cong CDP dang song. IDE thuong khong co CDP; Submit tren IDE di qua UIA."""
    global _LAST_PROCESS_PORT_SCAN_MONO

    candidates: list[int] = []
    for port in _ports_from_files() + DEFAULT_DEBUG_PORTS + sorted(_DISCOVERED_DEBUG_PORTS):
        if port not in candidates:
            candidates.append(port)

    live = _live_cdp_ports(candidates)

    now = time.monotonic()
    scan_due = not live or now - _LAST_PROCESS_PORT_SCAN_MONO >= PROCESS_PORT_SCAN_INTERVAL_SEC
    if scan_due:
        _LAST_PROCESS_PORT_SCAN_MONO = now
        discovered = _ports_from_antigravity_processes()
        new_candidates = [port for port in discovered if port not in candidates]
        live.extend(_live_cdp_ports(new_candidates))

    live = sorted(set(live), key=int)
    live_numbers = {int(port) for port in live}
    _DISCOVERED_DEBUG_PORTS.intersection_update(live_numbers)
    _DISCOVERED_DEBUG_PORTS.update(live_numbers)
    return live


def get_target_pages(port: str) -> list[dict]:
    """Lay danh sach cac tab / webview / iframe cua Antigravity dang mo."""
    try:
        url = f"http://127.0.0.1:{port}/json"
        with urllib.request.urlopen(url, timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            wanted = {"page", "webview", "iframe", "background_page", "app", "other"}
            return [
                p
                for p in data
                if p.get("type") in wanted and p.get("webSocketDebuggerUrl")
            ]
    except Exception:
        return []


async def inject_page(ws_url: str, check_interval_ms: int = 500) -> bool:
    """Ket noi vao trang qua WebSocket CDP va inject doan ma Javascript tu dong bam nut."""
    payload = JS_PAYLOAD_TEMPLATE.replace("__CHECK_INTERVAL_MS__", str(check_interval_ms))
    try:
        async with websockets.connect(ws_url, open_timeout=2) as ws:
            req_eval = {
                "id": 1,
                "method": "Runtime.evaluate",
                "params": {"expression": payload, "returnByValue": True},
            }
            await ws.send(json.dumps(req_eval))
            resp_eval = json.loads(await ws.recv())

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


def _uia_log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


def start_uia_worker(poll_interval: float) -> None:
    """Luong STA rieng: bam Submit cua extension tren Antigravity IDE."""

    def worker() -> None:
        try:
            import comtypes

            comtypes.CoInitialize()
        except Exception as exc:
            print(
                f"[{time.strftime('%H:%M:%S')}] [CANH BAO] Khong khoi tao duoc UI Automation ({exc}). "
                f"Phan bam Submit tren Antigravity IDE se khong chay. Cai: pip install comtypes",
                flush=True,
            )
            return
        try:
            from uia_permission_submit import click_ide_permission_submit
        except Exception as exc:
            print(
                f"[{time.strftime('%H:%M:%S')}] [CANH BAO] Khong nap duoc module UIA ({exc}).",
                flush=True,
            )
            return
        print(
            f"[{time.strftime('%H:%M:%S')}] [UIA] Da bat giam sat nut Submit tren Antigravity IDE (extension).",
            flush=True,
        )
        while True:
            try:
                click_ide_permission_submit(log=_uia_log)
            except Exception as exc:
                print(
                    f"[{time.strftime('%H:%M:%S')}] [UIA] Loi khi quet IDE: {exc}",
                    flush=True,
                )
            time.sleep(max(0.4, poll_interval / 2))

    thread = threading.Thread(target=worker, name="ag-uia-submit", daemon=True)
    thread.start()


async def main_loop(poll_interval: float = 2.0, check_interval_ms: int = 500):
    print("===================================================================", flush=True)
    print("   ANTIGRAVITY DESKTOP & IDE 2.0 - AUTO SUBMIT DAEMON              ", flush=True)
    print("   CDP: Desktop  |  UI Automation: IDE extension                   ", flush=True)
    print("===================================================================", flush=True)
    print(f"[{time.strftime('%H:%M:%S')}] [KHOI DONG] Daemon dang chay (PID: {os.getpid()})...", flush=True)
    print(
        f"[{time.strftime('%H:%M:%S')}] [THEO DOI] Desktop qua CDP; IDE/extension qua UI Automation",
        flush=True,
    )
    print(
        f"[{time.strftime('%H:%M:%S')}] [THIET LAP] Toc do tim nut CDP: {check_interval_ms}ms, chu ky quet port: {poll_interval}s\n",
        flush=True,
    )

    start_uia_worker(poll_interval)

    # None makes the initial "no CDP" state visible instead of silently looking healthy.
    last_ports: set[str] | None = None
    injected_pages: set[str] = set()

    while True:
        try:
            ports = get_active_ports()
            current = set(ports)
            if current != last_ports:
                if not current:
                    print(
                        f"[{time.strftime('%H:%M:%S')}] [MAT KET NOI CDP] Khong con cong DevTools. "
                        f"Van tiep tuc bam Submit tren IDE bang UI Automation.",
                        flush=True,
                    )
                else:
                    print(
                        f"[{time.strftime('%H:%M:%S')}] [KET NOI CDP] Cong active: {', '.join(ports)}",
                        flush=True,
                    )
                last_ports = current
                injected_pages.clear()

            active_page_ids: set[str] = set()
            for port in ports:
                pages = get_target_pages(port)
                for page in pages:
                    page_id = page.get("id")
                    if page_id:
                        active_page_ids.add(f"{port}:{page_id}")
                    ws_url = page.get("webSocketDebuggerUrl")
                    key = f"{port}:{page_id}"
                    if page_id and key not in injected_pages and ws_url:
                        success = await inject_page(ws_url, check_interval_ms)
                        if success:
                            injected_pages.add(key)
                            title = (page.get("title") or "Antigravity View")[:45]
                            print(
                                f"[{time.strftime('%H:%M:%S')}] [THANH CONG] Da kich hoat Auto-Submit CDP cho: '{title}' "
                                f"(Port: {port}, Page: {str(page_id)[:8]})",
                                flush=True,
                            )
            injected_pages = injected_pages.intersection(active_page_ids)
        except Exception:
            pass

        await asyncio.sleep(poll_interval)


def parse_args():
    parser = argparse.ArgumentParser(description="Antigravity Desktop & IDE 2.0 Auto-Submit Daemon")
    parser.add_argument("--interval", type=float, default=2.0, help="Chu ky quet tien trinh / cong port (giay, mac dinh: 2.0)")
    parser.add_argument("--button-check-ms", type=int, default=500, help="Chu ky tim nut Submit trong giao dien (ms, mac dinh: 500)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        asyncio.run(main_loop(poll_interval=args.interval, check_interval_ms=args.button_check_ms))
    except KeyboardInterrupt:
        print("\n[Antigravity Auto-Submit Daemon] Da dung boi nguoi dung.", flush=True)
        sys.exit(0)
