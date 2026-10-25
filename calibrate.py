"""Run once: pick the chat area, the 'Tap to enter text' box and the send button with your mouse.

Open the chat tab the bot will work in (World / Alliance / ...) so it looks the way it will while the
bot is running. Coordinates are saved relative to the game window.
"""
import cv2

from common import CFG, countdown, list_titles, load_cfg, save_cfg, screenshot

if not CFG.get("window_title", "").strip():
    print("window_title is empty in config.json -> using the whole primary screen.")
    print("Open windows (set window_title to the game window's title):")
    for t in list_titles():
        print("  ", t)

countdown(CFG.get("countdown", 5), "Switch to the game window, chat open. Capturing in")
img = screenshot()
h, w = img.shape[:2]
print(f"Captured {w}x{h}. Keep the game window at this size from now on.")
cv2.imwrite("screen.png", img)

scale = min(1.0, 900 / h)
small = cv2.resize(img, None, fx=scale, fy=scale)


def pick(title):
    x, y, rw, rh = cv2.selectROI(title, small, showCrosshair=True)
    cv2.destroyAllWindows()
    if rw == 0 or rh == 0:
        raise SystemExit("Selection cancelled.")
    return [int(v / scale) for v in (x, y, rw, rh)]


x, y, rw, rh = pick("1) Drag over the CHAT MESSAGES (just under the tabs down to just above the input bar), ENTER")
chat = [x, y, x + rw, y + rh]

x, y, rw, rh = pick('2) Drag over the "Tap to enter text" box, then press ENTER')
inp = [x + rw // 2, y + rh // 2]

x, y, rw, rh = pick("3) Drag over the green SEND arrow button, then press ENTER")
send = [x + rw // 2, y + rh // 2]

cfg = load_cfg()
cfg["chat_box"] = chat
cfg["input_xy"] = inp
cfg["send_xy"] = send
save_cfg(cfg)
print("Saved to config.json:", chat, inp, send)
