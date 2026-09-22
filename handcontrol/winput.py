"""Thin ctypes wrappers over user32 for input injection. Windows only."""

from __future__ import annotations

import ctypes
import logging
from ctypes import wintypes

log = logging.getLogger(__name__)

_user32 = ctypes.WinDLL("user32", use_last_error=True)

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_WHEEL = 0x0800
VK_LWIN = 0x5B
WHEEL_DELTA = 120

ULONG_PTR = ctypes.c_size_t


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


_user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
_user32.SendInput.restype = wintypes.UINT
_user32.GetCursorPos.argtypes = (ctypes.POINTER(wintypes.POINT),)
_user32.GetCursorPos.restype = wintypes.BOOL
_user32.SetCursorPos.argtypes = (ctypes.c_int, ctypes.c_int)
_user32.SetCursorPos.restype = wintypes.BOOL
_user32.GetForegroundWindow.restype = wintypes.HWND
_user32.GetWindowRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
_user32.GetWindowRect.restype = wintypes.BOOL


def _send(*inputs: INPUT) -> None:
    array = (INPUT * len(inputs))(*inputs)
    sent = _user32.SendInput(len(inputs), array, ctypes.sizeof(INPUT))
    if sent != len(inputs):
        log.warning("SendInput delivered %d of %d events (error %d)", sent, len(inputs), ctypes.get_last_error())


def tap_key(vk: int) -> None:
    """Press and release a virtual key."""
    down = INPUT(type=INPUT_KEYBOARD)
    down.ki.wVk = vk
    up = INPUT(type=INPUT_KEYBOARD)
    up.ki.wVk = vk
    up.ki.dwFlags = KEYEVENTF_KEYUP
    _send(down, up)


def scroll_wheel(delta: int) -> None:
    """Vertical wheel: +120 is one notch up (content moves down), -120 one notch down."""
    event = INPUT(type=INPUT_MOUSE)
    event.mi.mouseData = delta & 0xFFFFFFFF  # DWORD field carrying a signed value
    event.mi.dwFlags = MOUSEEVENTF_WHEEL
    _send(event)


def cursor_pos() -> tuple[int, int]:
    point = wintypes.POINT()
    _user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def set_cursor_pos(x: int, y: int) -> None:
    _user32.SetCursorPos(int(x), int(y))


def foreground_window_rect() -> tuple[int, int, int, int] | None:
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return None
    rect = wintypes.RECT()
    if not _user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    return rect.left, rect.top, rect.right, rect.bottom
