"""Desktop helpers: capture the game window and drive the mouse/keyboard safely and human-like."""
import ctypes
import json
import os
import random
import sys
import time

import cv2
import mss
import numpy as np
import pyautogui
import pyperclip

# Make window coordinates and screenshots use real pixels on scaled displays (Windows).
try:
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

# Safety: slam the mouse into a screen corner to abort the bot.
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

HERE = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(HERE, "config.json")


def load_cfg():
    with open(CFG_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_cfg(cfg):
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


CFG = load_cfg()
_sct = mss.mss()


def list_titles():
    try:
        import pygetwindow as gw

        return [t for t in gw.getAllTitles() if t.strip()]
    except Exception:
        return []


def _pick_window(title):
    """The game window: an exact title match wins over windows that merely contain the text
    (e.g. a browser tab called 'LastZ guide')."""
    import pygetwindow as gw

    wins = [w for w in gw.getWindowsWithTitle(title) if w.width > 50 and w.height > 50]
    exact = [w for w in wins if (w.title or "").strip().lower() == title.strip().lower()]
    return (exact or wins or [None])[0]


def region():
    """Screen rectangle we capture and click relative to: the game window, or the whole screen."""
    title = CFG.get("window_title", "").strip()
    if title:
        w = _pick_window(title)
        if w is None:
            raise RuntimeError(f"No window with title containing '{title}' found")
        if getattr(w, "isMinimized", False):
            raise RuntimeError("Game window is minimized")
        return {"left": int(w.left), "top": int(w.top), "width": int(w.width), "height": int(w.height)}
    return dict(_sct.monitors[1])


def screenshot():
    shot = _sct.grab(region())
    return cv2.cvtColor(np.array(shot), cv2.COLOR_BGRA2BGR)


def scroll_chat_to_bottom(amount=-240):
    """Scroll the visible chat down without stealing focus or leaving the mouse over it."""
    title = CFG.get("window_title", "").strip()
    if not title:
        return False
    import pygetwindow as gw

    target = _pick_window(title)
    active = gw.getActiveWindow()
    if target is None or active is None or not _same_window(active, target):
        return False

    x1, y1, x2, y2 = CFG["chat_box"]
    r = region()
    x = r["left"] + (x1 + x2) // 2
    y = r["top"] + (y1 + y2) // 2
    old_pos = pyautogui.position()
    try:
        pyautogui.moveTo(x, y)
        pyautogui.scroll(amount)
    finally:
        pyautogui.moveTo(old_pos.x, old_pos.y)
    return True


def click(x, y, jitter=0):
    """Glide the mouse to the spot (many Unity games ignore teleport-clicks), then click."""
    r = region()
    jx = random.randint(-jitter, jitter) if jitter else 0
    jy = random.randint(-jitter, jitter) if jitter else 0
    px, py = r["left"] + int(x) + jx, r["top"] + int(y) + jy
    pyautogui.moveTo(px, py, duration=random.uniform(0.08, 0.22))
    time.sleep(random.uniform(0.04, 0.12))
    pyautogui.click()


def paste(text):
    pyperclip.copy(text)
    pyautogui.hotkey("command" if sys.platform == "darwin" else "ctrl", "v")


def type_text(text):
    pyautogui.write(text, interval=0.02)


def press(key):
    pyautogui.press(key)


def countdown(n, msg="Switch to the game window"):
    for i in range(int(n), 0, -1):
        print(f"{msg}... {i}")
        time.sleep(1)


def _same_window(a, b):
    ha, hb = getattr(a, "_hWnd", None), getattr(b, "_hWnd", None)
    if ha is not None and hb is not None:
        return ha == hb
    return (a.title or "").strip().lower() == (b.title or "").strip().lower()


def ensure_foreground():
    """True only if the game window is the active window, so we never type into another app."""
    title = CFG.get("window_title", "").strip()
    if not title:
        return True  # cannot verify; bot.py refuses to run like this unless told to
    try:
        import pygetwindow as gw
    except Exception:
        return True
    for _ in range(3):
        try:
            target = _pick_window(title)
            active = gw.getActiveWindow()
            if target is not None and active is not None and _same_window(active, target):
                return True
            if target is not None:
                if getattr(target, "isMinimized", False):
                    target.restore()
                target.activate()
        except Exception:
            pass
        time.sleep(0.5)
    return False


def send_chat(msg):
    """Click the chat's 'Tap to enter text' box (every single time), paste/type msg, press send;
    then put the mouse and clipboard back where they were."""
    if not ensure_foreground():
        return False
    jit = int(CFG.get("click_jitter", 3))
    old_pos = pyautogui.position()
    old_clip = None
    try:
        for i in range(max(1, int(CFG.get("input_clicks", 1)))):
            click(*CFG["input_xy"], jitter=jit)  # focus the input box before typing anything
            if i:
                time.sleep(0.3)
        time.sleep(random.uniform(0.4, 0.6))  # let the game open the text field
        if CFG["paste_mode"] == "paste":
            try:
                old_clip = pyperclip.paste()
            except Exception:
                old_clip = None
            paste(msg)
        else:
            type_text(msg)
        time.sleep(random.uniform(0.25, 0.4))
        if CFG["send_mode"] == "enter":
            press("enter")
        else:
            click(*CFG["send_xy"], jitter=jit)
        time.sleep(0.3)
    finally:
        if old_clip is not None:
            try:
                pyperclip.copy(old_clip)
            except Exception:
                pass
        try:
            pyautogui.moveTo(old_pos.x, old_pos.y)
        except Exception:
            pass
    return True
