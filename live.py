"""
Live camera scorer for the Rinehart 18-1 clover face (v0).

Approach (robust for a fixed / propped camera):
  1. Frame the clean face. It auto-locks onto the disc after a short countdown
     (or tap BASELINE / press 'b' to do it now).
  2. Shoot. Each new frame is differenced against the baseline to find newly
     appeared objects (arrows). Each hit is scored by its ring, and the total
     is drawn live.

No keyboard needed: tap the on-screen buttons (the tablet touchscreen
registers taps as clicks).
  BASELINE  lock onto the clean face now (also discards the current end)
  SAVE END  record this end to score_history.csv, then reset for the next end
  CAMERA    switch to the next connected camera (e.g. a plugged-in webcam)
  QUIT      exit
Keys b / s / n / q still work too. The active camera index shows top-right;
session ends + running total show below it. History: score_history.csv.

This is a starting point meant to be tuned against the real target -- arrow
impact estimation (currently the blob centroid) and the diff threshold will
need adjustment once we see it running on the tablet.
"""
import csv
import os
import sys
import time
from datetime import datetime
from itertools import combinations

import cv2
import numpy as np

from clover_scorer import (segment_green, find_disc, score_hit, render,
                           RINGS, FACE_DIAMETER_IN)

DIFF_THRESH = 45          # grayscale difference that counts as "changed"
MIN_ARROW_AREA = 60       # px, ignore smaller changed blobs as noise
AUTO_BASELINE_SEC = 3.0   # auto-lock this long after a clean disc is visible
RECONNECT_SEC = 1.5       # how often to retry the camera after it drops out

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'score_history.csv')


def spread_inches(scored, R):
    """Widest gap between any two hits, in inches (0 for <2 hits)."""
    pts = [(x, y) for x, y, _ in scored]
    if len(pts) < 2 or not R:
        return 0.0
    worst = max(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
                for a, b in combinations(pts, 2))
    return worst * FACE_DIAMETER_IN / (2.0 * R)


def save_end(scored, R):
    """Append one shooting end to the history CSV. Returns the row dict."""
    total = sum(s for _, _, s in scored)
    row = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'arrows': len(scored),
        'total': total,
        'scores': ' '.join(str(s) for _, _, s in scored),
        'spread_in': round(spread_inches(scored, R), 2),
    }
    new = not os.path.exists(HISTORY_FILE)
    with open(HISTORY_FILE, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if new:
            w.writeheader()
        w.writerow(row)
    print(f"saved end: {row}")
    return row

FONT = cv2.FONT_HERSHEY_SIMPLEX
_ui = {'buttons': {}, 'action': None}


def _on_mouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        for name, (x1, y1, x2, y2) in param['buttons'].items():
            if x1 <= x <= x2 and y1 <= y <= y2:
                param['action'] = name


BUTTON_ORDER = ['baseline', 'save', 'camera', 'quit']
BUTTON_LABELS = {'baseline': 'BASELINE', 'save': 'SAVE END',
                 'camera': 'CAMERA', 'quit': 'QUIT'}


def button_layout(w, h):
    n = len(BUTTON_ORDER)
    m, bh = 10, 44
    bw = min(150, (w - (n + 1) * m) // n)
    y1 = h - bh - m
    layout = {}
    for i, name in enumerate(BUTTON_ORDER):
        x1 = m + i * (bw + m)
        layout[name] = (x1, y1, x1 + bw, y1 + bh)
    return layout


def draw_buttons(img, buttons):
    for name, (x1, y1, x2, y2) in buttons.items():
        cv2.rectangle(img, (x1, y1), (x2, y2), (50, 50, 50), -1)
        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 255), 1)
        cv2.putText(img, BUTTON_LABELS[name], (x1 + 10, y1 + 30), FONT, 0.5,
                    (255, 255, 255), 2, cv2.LINE_AA)


def find_arrows(baseline, frame, disc_mask):
    """New objects (arrows) inside the disc, as a list of (x, y) impact points."""
    d = cv2.absdiff(cv2.cvtColor(baseline, cv2.COLOR_BGR2GRAY),
                    cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
    _, ch = cv2.threshold(d, DIFF_THRESH, 255, cv2.THRESH_BINARY)
    ch = cv2.bitwise_and(ch, disc_mask)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    ch = cv2.morphologyEx(ch, cv2.MORPH_OPEN, k)
    ch = cv2.morphologyEx(ch, cv2.MORPH_CLOSE, k, iterations=2)
    cnts = cv2.findContours(ch, cv2.RETR_EXTERNAL,
                            cv2.CHAIN_APPROX_SIMPLE)[-2:][0]
    hits = []
    for c in cnts:
        if cv2.contourArea(c) < MIN_ARROW_AREA:
            continue
        M = cv2.moments(c)
        if M['m00'] == 0:
            continue
        hits.append((int(M['m10'] / M['m00']), int(M['m01'] / M['m00'])))
    return hits


def score_frame(frame, baseline, cx, cy, R, disc_mask):
    hits = find_arrows(baseline, frame, disc_mask)
    scored = [(x, y, score_hit(cx, cy, R, x, y)) for (x, y) in hits]
    vis = render(frame, cx, cy, R, scored)
    total = sum(s for _, _, s in scored)
    cv2.putText(vis, f"Arrows: {len(scored)}   Total: {total}",
                (10, 26), FONT, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
    return vis, scored, total


def try_lock(frame):
    """Attempt to find the disc in a frame; return (cx,cy,R,mask) or None."""
    try:
        green = segment_green(frame)
        cx, cy, R, mask = find_disc(green)
        if R < 20:              # too small to be the face
            return None
        return cx, cy, R, mask
    except Exception:
        return None


def _do_baseline(frame):
    lock = try_lock(frame)
    if lock is None:
        print("no clover disc detected yet -- reframe the face")
        return None
    cx, cy, R, mask = lock
    print(f"baselined: center=({cx},{cy}) R={R}px "
          f"scale={FACE_DIAMETER_IN / (2.0 * R):.4f} in/px")
    return (frame.copy(), cx, cy, R, mask)


MAX_CAM_INDEX = 6

# On Linux force the V4L2 backend so OpenCV doesn't fall back to a GStreamer
# pipeline (which can pop up a separate video-sink window). Fall back to the
# default backend on other platforms / if V4L2 isn't available.
_BACKENDS = [getattr(cv2, 'CAP_V4L2', None), getattr(cv2, 'CAP_ANY', 0)]
_BACKENDS = [b for b in _BACKENDS if b is not None]


def camera_indices():
    """Real camera indices from /dev/video*, else a plain 0..MAX scan."""
    try:
        import glob
        import re
        idxs = []
        for path in glob.glob('/dev/video*'):
            m = re.search(r'(\d+)$', path)
            if m:
                idxs.append(int(m.group(1)))
        if idxs:
            return sorted(set(idxs))
    except Exception:
        pass
    return list(range(MAX_CAM_INDEX))


def _try_open(idx):
    for backend in _BACKENDS:
        cap = cv2.VideoCapture(idx, backend)
        if cap.isOpened():
            ok, _ = cap.read()
            if ok:
                return cap
        cap.release()
    return None


def open_camera(preferred):
    """Try the preferred index first, then scan real devices for a working one."""
    order = [preferred] + [i for i in camera_indices() if i != preferred]
    for idx in order:
        cap = _try_open(idx)
        if cap is not None:
            print(f"using camera index {idx}")
            return cap, idx
    return None, None


def next_working_camera(current):
    """First working camera *after* `current` among real devices (wrapping)."""
    idxs = camera_indices()
    if current in idxs:
        start = idxs.index(current) + 1
    else:
        start = 0
    ordered = idxs[start:] + idxs[:start]   # everything after current, wrapping
    for idx in ordered:
        if idx == current:
            continue
        cap = _try_open(idx)
        if cap is not None:
            return cap, idx
    return None, current


def main(cam_index):
    cap, cur_idx = open_camera(cam_index)
    if cap is None:
        print("Could not open any camera (tried indices 0-5). "
              "Is another app using it, or is camera permission blocked?")
        return
    win = 'Rinehart 18-1 Live Scorer'
    cv2.namedWindow(win)
    cv2.setMouseCallback(win, _on_mouse, _ui)

    baseline = None
    cx = cy = R = disc_mask = None
    disc_seen_since = None
    last_wh = (640, 480)      # remembered so we can draw a UI with no camera
    last_reconnect = 0.0
    last_scored = []          # current end's scored hits, for SAVE END
    session_ends = 0
    session_total = 0
    flash = ('', 0.0)         # (message, expiry time) shown briefly after save
    print(__doc__)

    while True:
        ok, frame = (cap.read() if cap is not None else (False, None))

        if not ok:
            # camera dropped out (e.g. USB plugged/unplugged) -- don't quit,
            # keep the window alive and try to reconnect.
            if cap is not None:
                print("camera lost; reconnecting...")
                cap.release()
                cap = None
                baseline = None
                disc_seen_since = None
            now = time.time()
            if now - last_reconnect > RECONNECT_SEC:
                last_reconnect = now
                newcap, newidx = open_camera(cur_idx)
                if newcap is not None:
                    cap, cur_idx = newcap, newidx
                    continue
            w, h = last_wh
            disp = np.zeros((h, w, 3), np.uint8)
            cv2.putText(disp, "Camera disconnected -- reconnecting...",
                        (10, 30), FONT, 0.7, (0, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(disp, "Tap CAMERA to pick another, or QUIT.",
                        (10, 58), FONT, 0.6, (0, 255, 255), 2, cv2.LINE_AA)
            _ui['buttons'] = button_layout(w, h)
        else:
            h, w = frame.shape[:2]
            last_wh = (w, h)
            _ui['buttons'] = button_layout(w, h)

            if baseline is not None:
                disp, last_scored, _ = score_frame(frame, baseline,
                                                   cx, cy, R, disc_mask)
            else:
                disp = frame.copy()
                lock = try_lock(frame)
                if lock is not None:
                    lcx, lcy, lR, _ = lock
                    cv2.circle(disp, (lcx, lcy), lR, (0, 255, 255), 2)
                    if disc_seen_since is None:
                        disc_seen_since = time.time()
                    left = AUTO_BASELINE_SEC - (time.time() - disc_seen_since)
                    if left <= 0:
                        _ui['action'] = 'baseline'
                    else:
                        cv2.putText(disp, f"Auto-locking in {left:.0f}s "
                                    f"(or tap BASELINE)", (10, 26), FONT, 0.7,
                                    (0, 255, 255), 2, cv2.LINE_AA)
                else:
                    disc_seen_since = None
                    cv2.putText(disp, "Point at the clean clover face...",
                                (10, 26), FONT, 0.7, (0, 255, 255), 2,
                                cv2.LINE_AA)

        cv2.putText(disp, f"cam {cur_idx}", (w - 90, 26), FONT, 0.6,
                    (200, 200, 200), 2, cv2.LINE_AA)
        cv2.putText(disp, f"ends {session_ends}  total {session_total}",
                    (w - 240, 52), FONT, 0.6, (200, 200, 200), 2, cv2.LINE_AA)
        if flash[1] > time.time():
            cv2.putText(disp, flash[0], (10, last_wh[1] - 70), FONT, 0.7,
                        (0, 255, 0), 2, cv2.LINE_AA)
        draw_buttons(disp, _ui['buttons'])
        cv2.imshow(win, disp)
        key = cv2.waitKey(1) & 0xff

        action = _ui['action']
        _ui['action'] = None
        if key == ord('b'):
            action = 'baseline'
        elif key == ord('s'):
            action = 'save'
        elif key == ord('n'):
            action = 'camera'
        elif key in (ord('q'), 27):
            action = 'quit'

        if action == 'quit':
            break
        elif action == 'baseline':
            res = _do_baseline(frame)
            if res is not None:
                baseline, cx, cy, R, disc_mask = res
            disc_seen_since = None
        elif action == 'save':
            if last_scored:
                row = save_end(last_scored, R)
                session_ends += 1
                session_total += row['total']
                flash = (f"Saved end #{session_ends}: {row['total']} pts "
                         f"({row['arrows']} arrows)", time.time() + 3)
            else:
                flash = ("No arrows detected -- nothing to save",
                         time.time() + 3)
            baseline = None
            disc_seen_since = None
            last_scored = []
        elif action == 'camera':
            newcap, newidx = next_working_camera(cur_idx)
            if newcap is not None:
                if cap is not None:
                    cap.release()
                cap, cur_idx = newcap, newidx
                baseline = None
                disc_seen_since = None
                print(f"switched to camera {cur_idx}")
            else:
                print("no other working camera found")

    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    main(idx)
