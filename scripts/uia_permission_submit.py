"""Click Antigravity permission Submit via Windows UI Automation.

The Desktop app exposes Chrome DevTools Protocol, so the CDP injector can
press Submit there. The Antigravity extension inside Antigravity IDE or
Visual Studio Code does not: those hosts are launched without
--remote-debugging-port, so there is no DevToolsActivePort and no /json targets.

The permission dialog (Allow running / Allow listing / Allow testing)
is still in the accessibility tree as a Button named "Submit ↵" next to Skip.
This module invokes that button. No extra runtime besides comtypes.

The Antigravity web UI opened as a browser tab (https://127.0.0.1:PORT/c/...)
is matched only when its address bar proves it is the local Antigravity UI,
never the open web.
"""

from __future__ import annotations

import ctypes
import os
import threading
import time
from ctypes import wintypes
from typing import Callable

_UIA = None
_UIA_LOCK = threading.Lock()
_LAST_CLICK_MONO = 0.0
_MIN_CLICK_GAP_SEC = 1.5


def _load_uia():
    global _UIA
    if _UIA is not None:
        return _UIA
    from comtypes.client import CreateObject, GetModule

    GetModule("UIAutomationCore.dll")
    from comtypes.gen.UIAutomationClient import CUIAutomation

    _UIA = CreateObject(CUIAutomation)
    return _UIA


# Antigravity.exe is the Desktop app and is handled by CDP. Do not match it here.
_HOST_PROCESS_NAMES = {
    "antigravity ide.exe",
    "code.exe",
    "code - insiders.exe",
}

# A browser tab showing the local Antigravity web UI (no CDP there either).
# Browsers additionally need address-bar proof (see _browser_local_url).
_BROWSER_PROCESS_NAMES = {
    "chrome.exe",
    "msedge.exe",
}


def _is_agent_host_window(title: str, image_name: str = "") -> bool:
    """True for Antigravity IDE, or VS Code hosting the Antigravity extension."""
    folded_title = (title or "").casefold()
    folded_image = (image_name or "").casefold()
    if "antigravity ide" in folded_title:
        return True
    if "visual studio code" in folded_title:
        return True
    return folded_image in _HOST_PROCESS_NAMES


def _host_label(title: str, image_name: str = "") -> str:
    folded = f"{title or ''} {image_name or ''}".casefold()
    if (
        "visual studio code" in folded
        or "code.exe" in folded
        or "code - insiders.exe" in folded
    ):
        return "VS Code"
    if "msedge.exe" in folded:
        return "Edge"
    if "chrome.exe" in folded:
        return "Chrome"
    return "Antigravity IDE"


def _browser_local_url(auto, scan_root) -> str:
    """Address-bar URL when a browser shows the local Antigravity web UI.

    Returns "" otherwise, so Submit on any other website is never touched.
    """
    from comtypes.gen.UIAutomationClient import (
        IUIAutomationValuePattern,
        TreeScope_Descendants,
        UIA_ControlTypePropertyId,
        UIA_EditControlTypeId,
        UIA_ValuePatternId,
    )

    try:
        cond = auto.CreatePropertyCondition(
            UIA_ControlTypePropertyId, UIA_EditControlTypeId
        )
        edits = scan_root.FindAll(TreeScope_Descendants, cond)
    except Exception:
        return ""
    try:
        total = int(edits.Length)
    except Exception:
        return ""
    for index in range(min(total, 25)):
        try:
            element = edits.GetElement(index)
            pattern = element.GetCurrentPattern(UIA_ValuePatternId)
            if not pattern:
                continue
            value = pattern.QueryInterface(IUIAutomationValuePattern).CurrentValue or ""
        except Exception:
            continue
        lowered = value.strip().lower()
        if ("127.0.0.1" in lowered or "localhost" in lowered) and (
            "/c/" in lowered or "antigravity" in lowered
        ):
            return value.strip()
    return ""


def _native_hwnd(element) -> int:
    try:
        return int(element.CurrentNativeWindowHandle or 0)
    except Exception:
        return 0


def _is_visible_window(hwnd: int) -> bool:
    if hwnd <= 0:
        return True
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.IsWindowVisible.argtypes = [wintypes.HWND]
        user32.IsWindowVisible.restype = wintypes.BOOL
        return bool(user32.IsWindowVisible(hwnd))
    except Exception:
        return True


def _process_image_name(pid: int) -> str:
    """Basename of the process image. Used when VS Code's window title is customized."""
    if pid <= 0:
        return ""
    process_query_limited_information = 0x1000
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            return ""
        try:
            buffer = ctypes.create_unicode_buffer(32768)
            size = wintypes.DWORD(len(buffer))
            if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                return ""
            return os.path.basename(buffer.value)
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return ""


def _refresh_window_element(auto, window_el, hwnd: int):
    """Re-bind from the HWND so a VS Code webview fragment is included."""
    if hwnd <= 0:
        return window_el
    try:
        refreshed = auto.ElementFromHandle(hwnd)
    except Exception:
        return window_el
    return refreshed or window_el


def _is_permission_submit(name: str) -> bool:
    raw = name or ""
    lowered = raw.strip().lower()
    if not lowered.startswith("submit"):
        return False
    # Permission dialog uses "Submit ↵". A bare "Submit" is accepted only
    # when the same subtree also has Skip (checked by the caller).
    return ("↵" in raw) or ("enter" in lowered) or lowered == "submit"


def _is_skip(name: str) -> bool:
    return (name or "").strip().lower() == "skip"


def _is_allow_prompt(name: str) -> bool:
    lowered = (name or "").strip().lower()
    return (
        lowered.startswith("allow ")
        or "yes, allow this time" in lowered
        or "allow running" in lowered
        or "allow testing" in lowered
        or "allow verifying" in lowered
        or "allow generating" in lowered
    )


def _safe_name(element) -> str:
    try:
        return element.CurrentName or ""
    except Exception:
        return ""


def _click_bounding_rect(element) -> bool:
    """Chromium often ignores UIA Invoke; a real mouse click at the button center works."""
    import ctypes

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    try:
        rect = element.CurrentBoundingRectangle
        x = int((rect.left + rect.right) / 2)
        y = int((rect.top + rect.bottom) / 2)
        if x <= 0 or y <= 0:
            return False
        original = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(original))
        ctypes.windll.user32.SetCursorPos(x, y)
        ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)  # LEFTDOWN
        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)  # LEFTUP
        ctypes.windll.user32.SetCursorPos(original.x, original.y)
        return True
    except Exception:
        return False


def _invoke(element) -> bool:
    """Invoke the button without touching the mouse when possible.

    UIA Invoke activates the control in place (no cursor move, works on
    background windows). The physical mouse click is only a fallback for
    Chromium hosts that ignore Invoke.
    """
    from comtypes.gen.UIAutomationClient import IUIAutomationInvokePattern, UIA_InvokePatternId

    try:
        pattern = element.GetCurrentPattern(UIA_InvokePatternId)
        if pattern:
            invoker = pattern.QueryInterface(IUIAutomationInvokePattern)
            invoker.Invoke()
            return True
    except Exception:
        pass
    return _click_bounding_rect(element)


def _match_permission_submit(auto, window_el):
    """Return (button, host_label, title) when this window has a permission Submit."""
    from comtypes.gen.UIAutomationClient import (
        TreeScope_Descendants,
        UIA_ButtonControlTypeId,
        UIA_ControlTypePropertyId,
        UIA_RadioButtonControlTypeId,
        UIA_TextControlTypeId,
    )

    hwnd = _native_hwnd(window_el)
    if not _is_visible_window(hwnd):
        return None

    title = _safe_name(window_el)
    image = ""
    browser = False
    if not _is_agent_host_window(title):
        try:
            image = _process_image_name(int(window_el.CurrentProcessId))
        except Exception:
            image = ""
        if not _is_agent_host_window(title, image):
            browser = (image or "").casefold() in _BROWSER_PROCESS_NAMES
            if not browser or "antigravity" not in (title or "").casefold():
                return None

    scan_root = _refresh_window_element(auto, window_el, hwnd)
    if browser and not _browser_local_url(auto, scan_root):
        # A browser tab is only a host when the address bar proves it shows
        # the local Antigravity web UI; never touch the open web.
        return None
    button_cond = auto.CreatePropertyCondition(
        UIA_ControlTypePropertyId, UIA_ButtonControlTypeId
    )
    try:
        buttons = scan_root.FindAll(TreeScope_Descendants, button_cond)
    except Exception:
        return None

    submit_el = None
    has_skip = False
    for index in range(int(buttons.Length)):
        try:
            element = buttons.GetElement(index)
            name = _safe_name(element)
        except Exception:
            continue
        if _is_skip(name):
            has_skip = True
        elif _is_permission_submit(name):
            submit_el = element

    has_allow = False
    if submit_el is not None and not has_skip:
        for control_type in (UIA_TextControlTypeId, UIA_RadioButtonControlTypeId):
            try:
                cond = auto.CreatePropertyCondition(
                    UIA_ControlTypePropertyId, control_type
                )
                nodes = scan_root.FindAll(TreeScope_Descendants, cond)
                for index in range(int(nodes.Length)):
                    try:
                        if _is_allow_prompt(_safe_name(nodes.GetElement(index))):
                            has_allow = True
                            break
                    except Exception:
                        continue
            except Exception:
                continue
            if has_allow:
                break

    if submit_el is None:
        return None
    if not (has_skip or has_allow or "↵" in _safe_name(submit_el)):
        return None
    return submit_el, _host_label(title, image), title


def _scan_permission_submits(auto) -> list[tuple]:
    root = auto.GetRootElement()
    walker = auto.ControlViewWalker
    child = walker.GetFirstChildElement(root)
    found: list[tuple] = []
    while child is not None:
        try:
            match = _match_permission_submit(auto, child)
        except Exception:
            match = None
        if match is not None:
            found.append(match)
        try:
            child = walker.GetNextSiblingElement(child)
        except Exception:
            break
    return found


def click_ide_permission_submit(log: Callable[[str], None] | None = None) -> bool:
    """Return True if a permission Submit in Antigravity IDE or VS Code was invoked."""
    global _LAST_CLICK_MONO
    now = time.monotonic()
    if now - _LAST_CLICK_MONO < _MIN_CLICK_GAP_SEC:
        return False

    with _UIA_LOCK:
        auto = _load_uia()
        found = _scan_permission_submits(auto)
        if not found:
            return False
        submit_el, label, title = found[0]
        if _invoke(submit_el):
            _LAST_CLICK_MONO = time.monotonic()
            if log:
                log(f"[UIA] Da bam Submit tren {label} ({title[:60]})")
            return True
    return False
