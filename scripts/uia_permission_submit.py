"""Click Antigravity IDE permission Submit via Windows UI Automation.

The Desktop app exposes Chrome DevTools Protocol, so the CDP injector can
press Submit there. The Antigravity 2.0 *extension* inside Antigravity IDE
does not: the IDE is a VS Code fork launched without --remote-debugging-port,
so there is no DevToolsActivePort and no /json targets.

The permission dialog (Allow running / Allow testing / Allow generating)
is still in the IDE accessibility tree as a Button named "Submit ↵" next
to Skip. This module invokes that button. No extra runtime besides comtypes.
"""

from __future__ import annotations

import threading
import time
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


def _is_ide_window(name: str) -> bool:
    title = name or ""
    return "Antigravity IDE" in title


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
    from comtypes.gen.UIAutomationClient import IUIAutomationInvokePattern, UIA_InvokePatternId

    invoked = False
    try:
        pattern = element.GetCurrentPattern(UIA_InvokePatternId)
        if pattern:
            invoker = pattern.QueryInterface(IUIAutomationInvokePattern)
            invoker.Invoke()
            invoked = True
    except Exception:
        invoked = False
    clicked = _click_bounding_rect(element)
    return invoked or clicked


def click_ide_permission_submit(log: Callable[[str], None] | None = None) -> bool:
    """Return True if a permission Submit in Antigravity IDE was invoked."""
    global _LAST_CLICK_MONO
    now = time.monotonic()
    if now - _LAST_CLICK_MONO < _MIN_CLICK_GAP_SEC:
        return False

    from comtypes.gen.UIAutomationClient import (
        TreeScope_Descendants,
        UIA_ButtonControlTypeId,
        UIA_ControlTypePropertyId,
        UIA_TextControlTypeId,
        UIA_RadioButtonControlTypeId,
    )

    with _UIA_LOCK:
        auto = _load_uia()
        root = auto.GetRootElement()
        walker = auto.ControlViewWalker
        child = walker.GetFirstChildElement(root)
        while child is not None:
            title = _safe_name(child)
            if _is_ide_window(title):
                button_cond = auto.CreatePropertyCondition(
                    UIA_ControlTypePropertyId, UIA_ButtonControlTypeId
                )
                try:
                    buttons = child.FindAll(TreeScope_Descendants, button_cond)
                except Exception:
                    child = walker.GetNextSiblingElement(child)
                    continue

                submit_el = None
                has_skip = False
                length = int(buttons.Length)
                for index in range(length):
                    try:
                        el = buttons.GetElement(index)
                        name = _safe_name(el)
                    except Exception:
                        continue
                    if _is_skip(name):
                        has_skip = True
                    elif _is_permission_submit(name):
                        submit_el = el

                has_allow = False
                if submit_el is not None and not has_skip:
                    for control_type in (UIA_TextControlTypeId, UIA_RadioButtonControlTypeId):
                        try:
                            cond = auto.CreatePropertyCondition(
                                UIA_ControlTypePropertyId, control_type
                            )
                            nodes = child.FindAll(TreeScope_Descendants, cond)
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

                if submit_el is not None and (has_skip or has_allow or "↵" in _safe_name(submit_el)):
                    if _invoke(submit_el):
                        _LAST_CLICK_MONO = time.monotonic()
                        if log:
                            log(
                                f"[UIA] Da bam Submit tren Antigravity IDE ({title[:60]})"
                            )
                        return True
            try:
                child = walker.GetNextSiblingElement(child)
            except Exception:
                break
    return False
